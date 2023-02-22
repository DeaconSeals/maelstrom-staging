from PredatorPrey.world import World
from genotype import GeneticTree
from primitives import *
from population import GeneticProgrammingPopulation
from unorderedWrapper import unorderedWrapper

import math
import random
import statistics
import multiprocessing
import sys
import concurrent.futures
from tqdm.contrib.concurrent import process_map
from tqdm.auto import tqdm
import itertools
import numpy as np

def get_size(obj, seen=None):
	"""Recursively finds size of objects"""
	size = sys.getsizeof(obj)
	if seen is None:
		seen = set()
	obj_id = id(obj)
	if obj_id in seen:
		return 0
	# Important mark as seen *before* entering recursion to gracefully handle
	# self-referential objects
	seen.add(obj_id)
	if isinstance(obj, dict):
		size += sum([get_size(v, seen) for v in obj.values()])
		size += sum([get_size(k, seen) for k in obj.keys()])
	elif hasattr(obj, '__dict__'):
		size += get_size(obj.__dict__, seen)
	elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
		size += sum([get_size(i, seen) for i in obj])
	return size

def get_eng_size(obj):
	size = get_size(obj)
	if size >= 1E9:
		return f'{round(size/1E12, 1)} GB'
	elif size >= 1E6:
		return f'{round(size/1E6, 1)} MB'
	elif size >= 1E3:
		return f'{round(size/1E3, 1)} KB'
	else:
		return f'{size}'

# Evaluate a competition between predator and prey. If either are not supplied, a random controller is created.
def evaluate(predator = None, prey = None, world_kwargs=None):
	if world_kwargs is None:
		world_kwargs = dict()
	world = World(**world_kwargs)
	termination = False
	if predator == None:
		predator = GeneticTree((PREDATOR, GENERAL), ANGLE)
		predator.root.func = angle_to_prey
		predator.initialize()
	if prey == None:
		prey = GeneticTree((PREY, GENERAL), ANGLE)
		
		prey.root.func = multiply_angle
		prey.root.children = [Node(ANGLE), Node(DISTANCE)]
		prey.root.children[0].func = predator_last_move
		prey.root.children[1].func = add_distances
		prey.root.children[1].children = [Node(DISTANCE), Node(DISTANCE)]
		prey.root.children[1].children[0].func = distance_to_opponent
		prey.root.children[1].children[1].func = distance_to_opponent
		prey.initialize()

	while not termination:
		if predator == None:
			predator_angle = random.random()*2*math.pi
		else:
			predator_angle = predator.execute({"world": world})
		if prey == None:
			prey_angle = random.random()*2*math.pi
		else:
			prey_angle = prey.execute({"world": world})
		world.move(predator_angle, prey_angle)
		termination = world.check_termination()
	time = world.time
	remaining_time = world.time_limit - world.time
	predator_comfort = world.predator_comfort + remaining_time
	prey_comfort = world.prey_comfort
	return remaining_time, time, predator_comfort, prey_comfort#, world


# Generate data for the current population
def gatherData(predators, prey, evals = None) -> dict:
	# global smallestPrey, absBestPrey
	log = dict()
	predFitness = [i.fitness for i in predators.population]
	log["avgPred"] = statistics.mean(predFitness)
	log["bestPred"] = max(predFitness)

	# absolute fitness evaluation for predator
	# for individual in predators.population:
	# 	if individual.absoluteFitness is None:
	# 		individual.absoluteFitness = evaluate(predator = individual.genotype)[0]

	# absPred = [i.absoluteFitness for i in predators.population]
	# log["avgAbsPred"] = statistics.mean(absPred)
	# log["bestAbsPred"] = max(absPred)
	
	preyFitness = [i.fitness for i in prey.population]
	log["avgPrey"] = statistics.mean(preyFitness)
	log["bestPrey"] = max(preyFitness)

	# # absolute fitness evaluation for prey
	# for individual in prey.population:
	# 	if individual.absoluteFitness is None:
	# 		individual.absoluteFitness = evaluate(prey = individual.genotype)[1]

	# absPrey = [i.absoluteFitness for i in prey.population]
	# log["avgAbsPrey"] = statistics.mean(absPrey)
	# log["bestAbsPrey"] = max(absPrey)
	if evals is not None:
		log['evals'] = evals
	else:
		log["evals"] = predators.evals

	return log


# Accepts matches between agents and evaluates them in parallel
def evaluateMatches(predators: list, prey: list, matches: list, executor = None, world_kwargs = None, max_sequence = 1000000):
	if executor is None:
		close = True
		executor = multiprocessing.Pool(min(32, multiprocessing.cpu_count()))
	else:
		close = False
		
	cores = executor.__dict__['_processes']

	results = [None for _ in range(len(matches))]
	tasks = [unorderedWrapper(match_id, evaluate, predators[match[0]].genotype, prey[match[1]].genotype, world_kwargs) for match_id, match in enumerate(matches)]
	chunks_per_processor = 10
	chunksize = max(1, min(max_sequence, len(tasks))//(cores*chunks_per_processor))
	while chunksize > cores*100: # heuristically bound max chunksize
		if chunksize == 1:
			break
		chunks_per_processor += 1
		chunksize = max(1, min(max_sequence, len(tasks))//(cores*chunks_per_processor))

	# evaluate competitions in segments of max_sequence length to manage memory
	start = 0
	end = 0
	for i in range(len(tasks)//max_sequence):
		end += max_sequence
		for task in executor.imap_unordered(unorderedWrapper.execute, tasks[start:end], chunksize=chunksize):
			# pbar.update(1)
			match_id, result = task
			results[match_id] = result
		start = end
	else:
		if tasks[start:]: # catch cases where there are no remaining tasks
			for task in executor.imap_unordered(unorderedWrapper.execute, tasks[start:], chunksize=chunksize):
				# pbar.update(1)
				match_id, result = task
				results[match_id] = result
	assert None not in results, "An evaluation was missed during competition"

	if close:
		executor.close()

	return results


# evaluate individuals against random distinct opponents
def sampleEvaluations(predators: GeneticProgrammingPopulation, prey: GeneticProgrammingPopulation, samples = 5, hallOfFameSize = 0, executor = None, world_kwargs = None) -> dict:
	# clear previous trials
	[indPredator.trials.clear() for indPredator in predators.population]
	[indPrey.trials.clear() for indPrey in prey.population]

	preyCounter = [0 for _ in prey.population]

	matches = list()
	evals = 0
	# print(f'predator size: {get_eng_size(predators)}\tprey size: {get_eng_size(prey)}')
	
	# Matchmaking
	for predator in range(len(predators.population)):
		opponents = set()
		for i in range(samples):
			minimum = min(preyCounter)
			opponent = random.choice([i for i in range(len(preyCounter)) if preyCounter[i] == minimum and i not in opponents])
			opponents.add(opponent)
			matches.append((predator, opponent))
			preyCounter[opponent] += 1
		
	results = evaluateMatches(predators.population, prey.population, matches, executor, world_kwargs)
	for i in range(len(matches)):
		predators.population[matches[i][0]].trials.append(results[i][0])
		prey.population[matches[i][1]].trials.append(results[i][1])

	predators.evals += len(matches)
	prey.evals += len(matches)
	evals = len(matches)

	if hallOfFameSize > 0:
		# evaluate predators against hall of fame
		matches.clear()
		for predatorIndex in range(len(predators.population)):
			counter = 0
			for preyKey in reversed(prey.hallOfFame):
				matches.append((predatorIndex, preyKey))
				counter += 1
				if counter >= hallOfFameSize:
					break
		results = evaluateMatches(predators.population, prey.hallOfFame, matches, executor, world_kwargs)
		for i in range(len(matches)):
			predators.population[matches[i][0]].trials.append(results[i][0])
		predators.evals += len(matches)
		evals += len(matches)
		# print(f'Predator games against HoF: {len(results)}  HoF size: {len(prey.hallOfFame)}')

		# evaluate prey against hall of fame
		matches.clear()
		counter = 0
		for predatorKey in reversed(predators.hallOfFame):
			for preyIndex in range(len(prey.population)):
				matches.append((predatorKey, preyIndex))
			counter += 1
			if counter >= hallOfFameSize:
				break
		results = evaluateMatches(predators.hallOfFame, prey.population, matches, executor, world_kwargs)
		for i in range(len(matches)):
			prey.population[matches[i][1]].trials.append(results[i][1])
		prey.evals += len(matches)
		evals += len(matches)
		# print(f'Prey games against HoF: {len(results)}  HoF size: {len(predators.hallOfFame)}')
		
	
	for indPredator in predators.population:
		indPredator.fitness = statistics.mean(indPredator.trials)
	# print(f"predator:\t{[indPredator.fitness for indPredator in predators.population]}")

	for indPrey in prey.population:
		indPrey.fitness = statistics.mean(indPrey.trials)
	# print(f"prey:\t\t{[indPrey.fitness for indPrey in prey.population]}")


	return gatherData(predators, prey), evals


# Perform a complete round-robin evaluation for analysis reason
def completeEvaluations(predators: GeneticProgrammingPopulation, prey: GeneticProgrammingPopulation, hallOfFameSize = 0, executor = None, world_kwargs = None, clear = True):
	if clear:
		[indPredator.trials.clear() for indPredator in predators.population]
		[indPrey.trials.clear() for indPrey in prey.population]
	
	evals = 0
	matches = list()
	for predatorIndex in range(len(predators.population)):
		for preyIndex in range(len(prey.population)):
			matches.append((predatorIndex, preyIndex))

	results = evaluateMatches(predators.population, prey.population, matches, executor, world_kwargs)
	for i in range(len(matches)):
		predators.population[matches[i][0]].trials.append(results[i][0])
		prey.population[matches[i][1]].trials.append(results[i][1])

	predators.evals += len(matches)
	prey.evals += len(matches)
	evals = len(matches)

	if hallOfFameSize == -1:
		hallOfFameSize = min(len(predators.hallOfFame), len(prey.hallOfFame))
	if hallOfFameSize > 0:
		# evaluate predators against hall of fame
		matches.clear()
		for predatorIndex in range(len(predators.population)):
			counter = 0
			for preyKey in reversed(prey.hallOfFame):
				matches.append((predatorIndex, preyKey))
				counter += 1
				if counter >= hallOfFameSize:
					break
		results = evaluateMatches(predators.population, prey.hallOfFame, matches, executor, world_kwargs)
		for i in range(len(matches)):
			predators.population[matches[i][0]].trials.append(results[i][0])
		predators.evals += len(matches)
		evals += len(matches)
		# print(f'Predator games against HoF: {len(results)}  HoF size: {len(prey.hallOfFame)}')

		# evaluate prey against hall of fame
		matches.clear()
		counter = 0
		for predatorKey in reversed(predators.hallOfFame):
			for preyIndex in range(len(prey.population)):
				matches.append((predatorKey, preyIndex))
			counter += 1
			if counter >= hallOfFameSize:
				break
		results = evaluateMatches(predators.hallOfFame, prey.population, matches, executor, world_kwargs)
		for i in range(len(matches)):
			prey.population[matches[i][1]].trials.append(results[i][1])
		prey.evals += len(matches)
		evals += len(matches)
		# print(f'Prey games against HoF: {len(results)}  HoF size: {len(predators.hallOfFame)}')

	for indPredator in predators.population:
		indPredator.fitness = statistics.mean(indPredator.trials)
	# print(f"predator:\t{[indPredator.fitness for indPredator in predators.population]}")

	for indPrey in prey.population:
		indPrey.fitness = statistics.mean(indPrey.trials)
	# print(f"prey:\t\t{[indPrey.fitness for indPrey in prey.population]}")

	return gatherData(predators, prey), evals


# Play the two best agents (unofficially deprecated)
def exhibition(predators: GeneticProgrammingPopulation, prey: GeneticProgrammingPopulation):
	bestPredator = max([predator.fitness for predator in predators.population])
	bestPredator = random.choice([predator for predator in predators.population if predator.fitness == bestPredator])
	bestPrey = max([preyIndividual.fitness for preyIndividual in prey.population])
	bestPrey = random.choice([preyIndividual for preyIndividual in prey.population if preyIndividual.fitness == bestPrey])
	return evaluate(bestPredator.genotype, bestPrey.genotype)

# def evaluateWrapper(inputs):
# 	predator, prey, world_kwargs = inputs
# 	results = evaluate(predator, prey, world_kwargs)
# 	return results[0], results[1]

def evaluateGenes(predators: list, prey: list, matches: list, cores = None, world_kwargs = None, max_sequence=2000000, executor=None, progress=False):
	if cores is None:
		cores = min(32, multiprocessing.cpu_count())

	if executor is None:
		close = True
		executor = multiprocessing.Pool(cores)
	else:
		close = False
		cores = executor.__dict__['_processes']

	results = [None for _ in range(len(matches))]
	tasks = [unorderedWrapper(match_id, evaluate, predators[match[0]], prey[match[1]], world_kwargs) for match_id, match in enumerate(matches)]
	chunks_per_processor = 10
	chunksize = max(1, min(max_sequence, len(tasks))//(cores*chunks_per_processor))
	while chunksize > cores*100: # heuristically bound max chunksize
		if chunksize == 1:
			break
		chunks_per_processor += 1
		chunksize = max(1, min(max_sequence, len(tasks))//(cores*chunks_per_processor))
	# maxtasksperchild = chunksize*2
	if progress:
		pbar = tqdm(total=len(tasks), unit=' evals')# with tqdm(total = len(tasks), unit=' evals') as pbar:
	# with multiprocessing.Pool(cores) as executor:
	# evaluate competitions in segments of max_sequence length to manage memory
	start = 0
	end = 0
	for i in range(len(tasks)//max_sequence):
		end += max_sequence
		for task in executor.imap_unordered(unorderedWrapper.execute, tasks[start:end], chunksize=chunksize):
			if progress: pbar.update(1)
			match_id, result = task
			results[match_id] = result
		start = end
	else:
		if tasks[start:]: # catch cases where there are no remaining tasks
			for task in executor.imap_unordered(unorderedWrapper.execute, tasks[start:], chunksize=chunksize):
				if progress: pbar.update(1)
				match_id, result = task
				results[match_id] = result
	assert None not in results, "An evaluation was missed during competition"

	if close:
		executor.close()
	if progress:
		pbar.close()

	return results

def postHocRoundRobin(predators: list, prey: list, world_kwargs = None, parallel_workers = 2, more_cores = True, max_sequence = 1000000, bonus_cores = 1):
	num_predators = len(predators)
	num_prey = len(prey)
	num_evals = num_predators * num_prey
	matches = ((pred_idx, prey_idx) for pred_idx in range(num_predators) for prey_idx in range(num_prey))

	if more_cores:
		cores = multiprocessing.cpu_count()
	else:
		cores = min(32, multiprocessing.cpu_count())
	
	segments = parallel_workers
	while math.ceil(num_evals/segments) > max_sequence:
		segments += parallel_workers
	sequence_length = max(1, math.ceil(num_evals/segments))
	worker_cores = bonus_cores+(cores//parallel_workers)
	start = 0
	end = 0
	num_jobs = math.ceil(num_evals/sequence_length)

	with tqdm(total = num_evals, unit=' evals') as pbar:
		# scores = list()
		with concurrent.futures.ProcessPoolExecutor(parallel_workers) as executor:
			jobs = [executor.submit(evaluateGenes, predators, prey, [match for match in itertools.islice(matches, sequence_length)], world_kwargs = world_kwargs, cores = worker_cores) for _ in range(min(parallel_workers*2, num_jobs))]
			results = {'predators': np.zeros((num_predators, num_prey)), 'prey': np.zeros((num_prey, num_predators))}
			matchIndex = 0
			for job in range(num_jobs):
				score = jobs[job%len(jobs)].result()
				for result in score:
					predatorIndex, preyIndex = matchIndex//num_prey, matchIndex%num_prey
					results['predators'][predatorIndex][preyIndex] = result[0]
					results['prey'][preyIndex][predatorIndex] = result[1]
					matchIndex += 1
				pbar.update(len(score))
				if job + len(jobs) < num_jobs:
					jobs[job%len(jobs)] = executor.submit(evaluateGenes, predators, prey, [match for match in itertools.islice(matches, sequence_length)], world_kwargs = world_kwargs, cores = worker_cores)
	del jobs, score
	# try:
	# 	del jobs
	# except:
	# 	pass
	# try:
	# 	del score
	# except:
	# 	pass
	for key in results:
		results[key]= results[key].tolist()
	return results
