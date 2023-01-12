from primitives import *
from competition import *
from genotype import *
import json
from tqdm.contrib import tenumerate
from tqdm.auto import trange
import sys
from pathlib import Path
from time import strftime, localtime
import random
import multiprocessing

def summonChampions(championFile):
	with open(championFile) as file:
			experimentCompetitors = json.load(file)
	for run, competitors in enumerate(experimentCompetitors):
		for species, population in competitors.items():
			experimentCompetitors[run][species] = [GeneticTree.fromDict(dictionary) for dictionary in population]
	return experimentCompetitors

def assessChampions(filenames):
	world_kwargs = {"predator_move_speed": 0.075, "prey_move_speed": 0.10, "agent_radius": 0.10, "time_limit":200}
	globalChampionMapping = dict()
	experimentMapping = dict()
	champions = dict()
	# print(filenames)
	for filename in filenames:
		experimentMapping[filename] = list()
		for run, competitors in enumerate(summonChampions(filename)):
			experimentMapping[filename].append(dict())
			for species, population in competitors.items():
				experimentMapping[filename][-1][species] = list()
				if species not in champions:
					champions[species] = list()
				if species not in globalChampionMapping:
					globalChampionMapping[species] = dict()
				for individual in population:
					if individual.string not in globalChampionMapping[species]:
						globalChampionMapping[species][individual.string] = len(champions[species])
						champions[species].append(individual)
					experimentMapping[filename][-1][species].append(globalChampionMapping[species][individual.string])
	results = postHocRoundRobin(**champions, world_kwargs = world_kwargs, parallel_workers = 8, more_cores=True)
	resultsDir = Path('results', strftime('%Y-%m-%d-%H-%M-%S', localtime()))
	resultsDir.mkdir(parents=True, exist_ok = True)
	
	with Path(resultsDir,'rawData.json').open('w') as file:
		json.dump({'mappings': experimentMapping, 'data': results}, file, separators=(',', ':'))

	for species, data in results.items():
		for index, scores in enumerate(data):
			results[species][index] = statistics.mean(scores)

	finalData = dict()
	for filename, experiment in experimentMapping.items():
		finalData[filename] = dict()
		for run, competitors in enumerate(experiment):
			for species, population in competitors.items():
				if species not in finalData[filename]:
					finalData[filename][species] = list()
				finalData[filename][species].append(max([results[species][index] for index in population]))

	with Path(resultsDir, 'finalData.json').open('w') as file:
		json.dump(finalData, file, separators=(',', ':'))

def main():
	if len(sys.argv) < 2:
		print("Please pass a champion file")
	else:
		random.seed(42)
		assessChampions([sys.argv[arg] for arg in range(1,len(sys.argv))])

if __name__ == "__main__":
	multiprocessing.set_start_method('spawn')
	main()
