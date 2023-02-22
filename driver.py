from maelstrom import Maelstrom
from island import GeneticProgrammingIsland
from population import GeneticProgrammingPopulation
from primitives import *
from competition import *
from findChampions import localTournaments


import math
import random
import statistics
from pathlib import Path
import gzip
import pickle
import sys
import json
from time import strftime, localtime
from configparser import ConfigParser
import multiprocessing
import concurrent.futures

from snake_eyes.snakeeyes import readConfig
from argparse import ArgumentParser

# from PIL import Image, ImageDraw # (commented out so dependencies are resolved)
import matplotlib.pyplot as plt
import matplotlib as mpl
from tqdm.auto import trange
from tqdm.contrib.concurrent import process_map

# Renders an interaction between agents (commented out so dependencies are resolved)
# def render_world(world, name="world", log_path="logs"):
# 	FULL_SIZE = 800
# 	DOWN_SIZE = 400
# 	AGENT_SIZE = world.agent_radius * FULL_SIZE / 2

# 	def world_to_image(x, y):
# 		x = (x + 1) * FULL_SIZE / 2
# 		y = (y + 1) * FULL_SIZE / 2
# 		return x, y

# 	frames = list()
# 	for frame in range(len(world.past_predator_positions)):
# 		image = Image.new("RGB", (FULL_SIZE, FULL_SIZE), (128, 128, 128))
# 		draw = ImageDraw.Draw(image)
# 		draw.ellipse(((0, 0), (FULL_SIZE - 1, FULL_SIZE - 1)), (255, 255, 255), (0, 0, 0, 0), 5)

# 		predator = world_to_image(*world.past_predator_positions[frame])
# 		draw.ellipse(((predator[0] - AGENT_SIZE, predator[1] - AGENT_SIZE),
# 					  (predator[0] + AGENT_SIZE, predator[1] + AGENT_SIZE)), (255, 0, 0), (0, 0, 0), 2)
# 		prey = world_to_image(*world.past_prey_positions[frame])
# 		draw.ellipse(((prey[0] - AGENT_SIZE, prey[1] - AGENT_SIZE), (prey[0] + AGENT_SIZE, prey[1] + AGENT_SIZE)),
# 					 (0, 255, 0), (0, 0, 0), 2)

# 		for i in range(1, frame + 1):
# 			start = world_to_image(*world.past_predator_positions[i - 1])
# 			end = world_to_image(*world.past_predator_positions[i])
# 			draw.line((start, end), (255, 0, 0), 5, "curve")
# 			start = world_to_image(*world.past_prey_positions[i - 1])
# 			end = world_to_image(*world.past_prey_positions[i])
# 			draw.line((start, end), (0, 255, 0), 5, "curve")

# 		image.thumbnail((DOWN_SIZE, DOWN_SIZE))
# 		frames.append(image)
# 	error = PermissionError("No error?")
# 	for _ in range(10):
# 		try:
# 			frames[0].save(log_path + "/{0}.gif".format(name), save_all=True, append_images=frames[1:], optimize=False,
# 						   duration=40, loop=0)
# 			return
# 		except PermissionError as e:
# 			time.sleep(1)
# 			error = e
# 	raise error


def main():
	argParser = ArgumentParser(description="Maelstrom Predator Prey Experiment Driver",
							epilog="Example: driver.py "
							"--config configs/default.cfg")
	argParser.add_argument('--config', type=str, default='configs/default.cfg', help='Configuration file for experiment parameters')
	args = argParser.parse_args()

	config = readConfig(args.config, globals(), locals())
	# print(config.keys())
	# for section in config:
	# 	print(section, config[section])


	random.seed(42)
	
	# if config['GENERAL'].get('analysis'):
	# 	analyze()
	# 	return
	# if config['GENERAL'].get('default_test'):
	# 	print("Testing baseline controllers")
	# 	_, _, _, _, world = evaluate()
	# 	# render_world(world=world, name = "test", log_path = "logs")
	# 	return

	# create directory for experiment results
	experimentDir = Path(config['GENERAL']['logpath'], config['GENERAL']['experimentName'], strftime('%Y-%m-%d-%H-%M', localtime()))
	experimentDir.mkdir(parents=True, exist_ok = True)

	# copy config file to experiment directory
	with open(args.config) as originalConfig:
		with Path(experimentDir, 'config.cfg').open('w') as copyConfig:
			[copyConfig.write(line) for line in originalConfig]

	experimentLogs = list()
	experimentChampions = list()

	# champions = {"predators": GeneticProgrammingPopulation(**config['predators']), "prey": GeneticProgrammingPopulation(**config['prey'])}
	if config.get('MAELSTROM'):
		maelstrom = True
		evolverClass = config['GENERAL'].get('evolverClass', Maelstrom)
		configKeyword = 'MAELSTROM'
	else:
		maelstrom = False
		evolverClass = config['GENERAL'].get('evolverClass', GeneticProgrammingIsland)
		configKeyword = 'ISLAND'

	if config['GENERAL'].get('parallelizeRuns'):
		parallel_runs = min(config['GENERAL']['runs'], multiprocessing.cpu_count())

		if parallel_runs <= (multiprocessing.cpu_count()*0.25): # allow for maximum of 125% overprovisioning of worker cores
			cores = 1 + (multiprocessing.cpu_count()//parallel_runs)
		else:
			cores = min(1, (multiprocessing.cpu_count()//parallel_runs))

		evolvers = list()
		for run in trange(config['GENERAL']['runs'], unit=' init', position=0):
			evolvers.append(evolverClass(**config[configKeyword], **config, cores = cores, position=run+1))
		runFunc = evolverClass.run
		
		with concurrent.futures.ProcessPoolExecutor(parallel_runs) as runPool:
			# print(runFunc, evolvers)
			evolutionRuns = [run for run in runPool.map(runFunc, evolvers)]
		experimentLogs = [run.log for run in evolutionRuns]
		experimentChampions = list()
		for run in evolutionRuns:
			runChampions = dict()
			for species, population in run.champions.items():
				runChampions[species] = [gene.toDict() for key, gene in population.items()]
			experimentChampions.append(runChampions)
		del evolvers
		del evolutionRuns

	else:
		for run in trange(config['GENERAL']['runs'], unit=' run'):
			evolver = evolverClass(**config[configKeyword], **config)
			evolver.run()
			experimentLogs.append(evolver.log)
			runChampions = dict()
			for species, population in evolver.champions.items():
				runChampions[species] = [gene.toDict() for key, gene in population.items()]
			experimentChampions.append(runChampions)
	
	with gzip.open(Path(experimentDir, 'evolutionLog.json.gz'), mode='wt') as file:
		json.dump(experimentLogs, file, separators=(',', ':'))
	
	competitorsDir = Path(experimentDir, 'competitors')
	competitorsDir.mkdir(parents=True, exist_ok = True)
	for run, competitors in enumerate(experimentChampions):
		with gzip.open(Path(competitorsDir, f'run{run}.json.gz'), mode='wt') as file:
			json.dump(competitors, file, separators=(',', ':'))

	if config['GENERAL'].get('findLocalChampions'):
		print('Beginning champion tournament')
		localTournaments(experimentDir, config['GENERAL']['finalChampions'], more_cores=False)

if __name__ == "__main__":
	multiprocessing.set_start_method('spawn')
	main()
