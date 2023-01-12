from primitives import *
from competition import *
from genotype import *
import json
from tqdm.auto import tqdm
from tqdm.contrib.concurrent import process_map
import sys
from pathlib import Path
from heapq import nlargest
import multiprocessing

def localTournaments(experimentDir, finalChampions=5, parallel_workers=2, more_cores=False):
	
	if Path(experimentDir, 'competitors').is_dir():
		experimentCompetitors = list()
		for runFile in Path(experimentDir, 'competitors').glob('*.json'):
			with runFile.open() as file:
				experimentCompetitors.append(json.load(file))
	elif Path(experimentDir, 'competitors.json').is_file():
		with Path(experimentDir, 'competitors.json').open() as file:
			experimentCompetitors = json.load(file)
		competitorsDir = Path(experimentDir, 'competitors')
		competitorsDir.mkdir(parents=True, exist_ok = True)
		for run, competitors in enumerate(experimentCompetitors):
			with Path(competitorsDir, f'run{run}.json').open('w') as file:
				json.dump(competitors, file, separators=(',', ':'))
		# print(f'You can safely delete {Path(experimentDir, "competitors.json")}')

	
	totalEvaluations = list()
	for run, competitors in enumerate(experimentCompetitors):
		evaluations = 1
		for species, population in competitors.items():
			experimentCompetitors[run][species] = [GeneticTree.fromDict(dictionary) for dictionary in population]
			evaluations *= len(population)
			# print(f'run {run} {species} {len(population)}')
		totalEvaluations.append(evaluations)

	world_kwargs = {"predator_move_speed": 0.075, "prey_move_speed": 0.10, "agent_radius": 0.10, "time_limit":200}
	results = list()

	with tqdm(total=sum(totalEvaluations), unit=' evals') as pbar:
		for run, competitors in enumerate(experimentCompetitors):
			results.append(postHocRoundRobin(**competitors, world_kwargs = world_kwargs, parallel_workers = parallel_workers, more_cores=more_cores))
			pbar.update(totalEvaluations[run])

	# with Path(experimentDir, 'localTournamentResults.json').open('w') as file:
	# 	json.dump(results, file, separators=(',', ':'))

	champions = list()
	for run, competitors in enumerate(results):
		champions.append(dict())
		for species, population in competitors.items():
			if len(population) <= finalChampions:
				champions[run][species] = [individual.toDict() for individual in experimentCompetitors[run][species]]
			else:
				data = [(index, statistics.mean(scores)) for index, scores in enumerate(population)]
				data = nlargest(finalChampions, data, key=lambda individual: individual[1])
				champions[run][species] = [experimentCompetitors[run][species][index].toDict() for index, _ in data]

	with Path(experimentDir, 'champions.json').open('w') as file:
		json.dump(champions, file, separators=(',', ':'))

	return champions

def main():
	if len(sys.argv) < 2:
		print("Please pass an experiment directory")
	else:
		for experimentDir in tqdm(sys.argv[1:], unit=' experiment'):
			localTournaments(experimentDir, parallel_workers = 8, more_cores = True)
		# process_map(localTournaments, [sys.argv[arg] for arg in range(1,len(sys.argv))], max_workers=max(1, multiprocessing.cpu_count()//32), unit=' experiment')
		# for arg in trange(1,len(sys.argv), unit=' experiment'):
		# 	localTournaments(sys.argv[arg])

if __name__ == "__main__":
	multiprocessing.set_start_method('spawn')
	main()
