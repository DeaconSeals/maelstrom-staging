from genotype import GeneticTree
from individual import GeneticProgrammingIndividual

import random
import math
import statistics
from collections import OrderedDict

# General-purpose GP population class that contains and manages individuals
# TODO: transition from parameters dictionary to clearer inputs with default values
class GeneticProgrammingPopulation:
	def __init__(self, popSize, numChildren, roles, outputType, depthLimit, hardLimit = None, depthMin = 1, evaluations = None, parentSelection = "uniform", survivalSelection = "truncation", survivalStrategy = "plus", mutation = 0.05, **kwargs):
		self.population = list()
		# self.parameters = parameters
		self.popSize = popSize
		self.numChildren = numChildren
		self.roles = roles
		self.outputType = outputType
		self.depthLimit = depthLimit
		self.hardLimit = hardLimit if hardLimit is not None else self.depthLimit*2
		self.depthMin = depthMin
		self.evalLimit = evaluations
		self.evals = 0
		self.parentSelection = parentSelection
		self.survivalSelection = survivalSelection
		self.survivalStrategy = survivalStrategy
		self.mutation = mutation
		self.optionalParams = kwargs
		self.hallOfFame = OrderedDict()
		self.CIAO = list()

	def rampedHalfAndHalf(self, leafProb = 0.5):
		full = self.popSize//2
		grow = self.popSize-full
		self.population = [GeneticProgrammingIndividual(GeneticTree(self.roles, self.outputType)) for _ in range(self.popSize)]
		
		for index in range(len(self.population)):
			if index < full:
				self.population[index].genotype.initialize(self.depthLimit, self.hardLimit, full = True)
			else:
				self.population[index].genotype.initialize(self.depthMin + (index%(self.depthLimit+1-self.depthMin)), self.hardLimit, grow = True, leafProb = leafProb)
	
	def selectParents(self, numParents = None):
		if numParents == None:
			numParents = self.numChildren
		
		# Definitions of parent selection algorithms
		# Note: this can probably be cleaned up and segmented in a better way (maybe with the decorator approach used in genotype)
		def uniformRandom(population, n):
			return random.choices(population = population, k = n)
		
		def kTournament(population, n, k):
			candidates = [index for index in range(len(population))]
			winners = []
			for i in range(n):
				participants = random.sample(candidates, k)
				best = max([population[participant].fitness for participant in participants])
				champion = random.choice([participant for participant in participants if best == population[participant].fitness])
				winners.append(champion)
			return [population[parent] for parent in winners]
		
		def fitnessProportionalSelection(population, n):
			fitnesses = [individual.fitness for individual in population]
			offset = min(fitnesses)
			offset = min(0, offset)
			weights = [fitness-offset for fitness in fitnesses]
			if sum(weights) == 0:
				weights = [fitness-offset+0.001 for fitness in fitnesses]
			return random.choices(population = population, weights = weights, k = n)
		
		def stochasticUniversalSampling(population, n):
			fitnesses = [individual.fitness for individual in population]
			offset = min(fitnesses)*1.1 # multiply the min offset by 10% so the least fit individual has a non-zero chance of selection
			if offset == 0:
				offset = -0.01 # mitigates the case where individuals with fitnesss of 0 
			else:
				offset = min(0, offset)
			roulette = [fitness - offset for fitness in fitnesses]
			total = sum(roulette)
			for i in range(1, len(roulette)):
				roulette[i] = roulette[i]+roulette[i-1]
			roulette = [value/total for value in roulette]
			parents = list()
			rouletteArm = random.random()
			arms = [math.fmod(rouletteArm+(i/n), 1.0) for i in range(n)]
			arms.sort()
			popIndex = 0
			for arm in arms:
				if arm <= roulette[popIndex]:
					parents.append(population[popIndex])
				else:
					popIndex += 1
			random.shuffle(parents)
			return parents

		def overselection(population, n, bias = 0.8, partition = 10):
			if partition > len(population) or partition < 0:
				partition = math.round(0.1*len(population))
			elites = math.round(bias*len(population))
			candidates = sorted(population, key=lambda individual: individual.fitness, reverse = True)
			parents = list()
			for i in range(n):
				if i <= elites and partition > 0:
					parents.append(random.choice(candidates[:partition]))
				else:
					parents.append(random.choice(candidates[partition:]))
			random.shuffle(parents)
			return parents
		
		# Actual selection execution
		if self.parentSelection == "kTournament":
			return kTournament(self.population, numParents, self.optionalParams["kParent"])
		elif self.parentSelection == "FPS":
			return fitnessProportionalSelection(self.population, numParents)
		elif self.parentSelection == "SUS":
			return stochasticUniversalSampling(self.population, numParents)
		elif self.parentSelection == "overselection":
			bias = self.optionalParams.get("overselectionBias", 0.8)
			partition = self.optionalParams.get("overselectionPartition", 10)
			return overselection(self.population, numParents, bias, partition)
		elif self.parentSelection != "uniform":
			return uniformRandom(self.population, numParents)
		else:
			raise NameError(f'unrecognized parent selection method: {self.parentSelection}')

	# Generate children through the selection of parents, recombination or mutation of parents to form children, then the migration of children
	# into the primary population depending on survival strategy
	# TODO: generalize this so it relies on operations of the individual class instead of skipping that and working directly with the genotype
	def generateChildren(self, imports = None):
		if imports == None:
			numParents = self.numChildren
		else:
			numParents = max(0, self.numChildren-len(imports))
		parents = self.selectParents(numParents)
		children = [parent.copy() for parent in parents]
		for i in range(len(children)):
			if random.random() <= self.mutation:
				children[i].genotype.subtreeMutation()
			else:
				children[i].genotype.subtreeRecombination(children[(i+1)%len(children)].genotype)
				while children[i].genotype.depth > self.hardLimit:
					children[i] = parents[i].copy()
					children[i].genotype.subtreeRecombination(children[(i+1)%len(children)].genotype)

		if imports != None:
			children.extend([migrant.copy() for migrant in imports])
		
		if self.survivalStrategy == "comma":
			self.population = children
		elif self.survivalStrategy == "plus":
			self.population.extend(children)
		else:
			raise NameError(f'unrecognized survival strategy: {self.survivalStrategy}')
	
	def selectSurvivors(self):
		if self.survivalSelection == "kTournament":
			self.population = self.selectUnique(n = self.popSize, method = "tournament", k = self.optionalParams["ksurvival"])
		elif self.survivalSelection == "FPS":
			self.population = self.selectUnique(n = self.popSize, method = "FPS")
		elif self.survivalSelection == "uniform":
			self.population = self.selectUnique(n = self.popSize, method = "uniform")
		elif self.survivalSelection == "truncation":
			self.population = self.selectUnique(n = self.popSize, method = "truncation")
		else:
			raise NameError(f'unrecognized survival selection method: {self.survivalSelection}')

	# TODO: implement more termination methods
	def checkTermination(self):
		return self.evalLimit is not None and self.evals >= self.evalLimit

	def updateHallOfFame(self):
		bestIndividual = 0
		bestFitness = self.population[bestIndividual].fitness

		for i in range(len(self.population)):
			if self.population[i].fitness > bestFitness:
				bestIndividual = i
		key = self.population[bestIndividual].genotype.string
		self.CIAO.append(key)
		if key in self.hallOfFame:
			self.hallOfFame.move_to_end(key)
			return
		else:
			self.hallOfFame[key] = self.population[bestIndividual].copy()

	# Selection of unique individuals for survival and migration
	# Note: this can probably be cleaned up and segmented in a better way (maybe with the decorator approach used in genotype)
	def selectUnique(self, n, method = "uniform", k = 5):
		# Definition of selection methods
		def uniformRandom(population, n):
			return random.sample(population, n)
		
		def kTournament(population, n, k):
			candidates = {index for index in range(len(population))}
			winners = []
			for i in range(n):
				participants = random.sample(list(candidates), k)
				best = max([population[participant].fitness for participant in participants])
				champion = random.choice([participant for participant in participants if best == population[participant].fitness])
				candidates.remove(champion)
				winners.append(champion)
			return [population[survivor] for survivor in winners]
		
		def fitnessProportionalSelection(population, n):
			offset = min([individual.fitness for individual in population])*1.1 # multiply the min offset by 10% so the least fit individual isn't guaranteed to die
			if offset == 0:
				offset = -0.01 # mitigates some deterministic behaviors of random.choices when all weights are 0 and avoids guaranteed death
			else:
				offset = min(0, offset)
			candidates = {index for index in range(len(population))}
			winners = []
			for i in range(n):
				champion = random.choices(population = list(candidates), weights = [population[individual].fitness-offset for individual in candidates])
				candidates.remove(champion[0])
				winners.append(champion[0])
			return [population[survivor] for survivor in winners]
		
		def truncation(population, n):
			return sorted(population, key=lambda individual: individual.fitness, reverse = True)[:n]
		
		def normalSelection(population, n):
			candidates = {index for index in range(len(population))}
			winners = []
			for i in range(n):
				fitnesses = [population[individual].fitness for individual in candidates]
				avg = statistics.mean(fitnesses)
				dev = statistics.stdev(fitnesses)
				if fitnesses.count(0) == len(fitnesses):
					weights = None
				else:
					weights = [dev/abs(avg-(population[individual].fitness*1.00001)) for individual in candidates]
				champion = random.choices(population = list(candidates), weights = weights)
				candidates.remove(champion[0])
				winners.append(champion[0])
			return [population[survivor] for survivor in winners]

		# Execution of selection method
		if n > len(self.population):
			print("selectUnique: requested too many individuals")
			return

		if method == "tournament":
			return kTournament(self.population, n, k)
		elif method == "FPS":
			return fitnessProportionalSelection(self.population, n)
		elif method == "uniform" or method == "random":
			return uniformRandom(self.population, n)
		elif method == "normal":
			return normalSelection(self.population, n)
		else:
			if method != "truncation" and method != "best":
				print(f"unknown survival selection parameter '{method}' defaulting to truncation")
			return truncation(self.population, n)


