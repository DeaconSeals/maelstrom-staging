from island import GeneticProgrammingIsland
from population import GeneticProgrammingPopulation
from tqdm.auto import tqdm

import multiprocessing
import concurrent.futures

'''
High-level guiding principles:
	+ Classes are defined hierarchically and rely on wrapper/interface functions to interact down the hierarchy
	+ Fitness evaluation is implemented as an external function and the function itself it passed to the island
	- Fitness evaluations are expected to accept named GeneticProgrammingPopulation objects as input and assign fitness to the individuals
	+ This file is agnostic of the nodes used in evolution
	+ This framework is designed with coevolution in mind, but one could easily use a single-population island with an appropriate fitness function
'''

# General-purpose Maelstrom class that contains and manages multiple islands
class Maelstrom():
	def __init__(self, islands: dict, evaluations=None, migrationEdges=None, cores=None, position=None, **kwargs):
		self.islands = dict()
		self.migrationEdges = migrationEdges
		self.evals = 0
		self.evalLimit = evaluations
		self.log = dict()
		if cores is None:
			cores = min(32, multiprocessing.cpu_count())
		self.cores = cores
		self.position = position
		# self.evalPool = multiprocessing.Pool(cores)

		# Initialize islands
		for key in islands:
			self.islands[key] = GeneticProgrammingIsland(cores = self.cores, **kwargs[islands[key]], **kwargs)
		self.evals = sum([self.islands[key].evals for key in self.islands])
		self.champions = dict()

	# def __del__(self):
	# 	self.evalPool.close()
		
	# Performs a single run of evolution until termination
	def run(self):
		generation = 1
		keys = [key for key in self.islands]
		
		self.evals = sum([self.islands[key].evals for key in self.islands])
		with multiprocessing.Pool(self.cores) as evalPool:
			with tqdm(total=self.evalLimit, unit=' evals', position=self.position) as pbar:
				pbar.set_description(f'Maelstrom Generation {generation}', refresh=False)
				pbar.update(self.evals)
				while self.evals < self.evalLimit:
					evals_old = self.evals
					# print(f"Beginning generation: {generation}\tEvaluations: {self.evals}")

					# migration
					for edge in self.migrationEdges:
						# check migration timing
						if generation % edge['period'] == 0:
							destinationIsland, destinationPopulation = edge['destination']
							sourceIsland, sourcePopulation = edge['source']
							# collect imports
							migrants = self.islands[sourceIsland].select(population=sourcePopulation, n=edge['size'], method=edge['method'])
							# export to destimation population
							if destinationPopulation in self.islands[destinationIsland].imports:
								self.islands[destinationIsland].imports[destinationPopulation].extend(migrants)
							else:
								self.islands[destinationIsland].imports[destinationPopulation] = migrants

					# Evolve one full generation with each island
					with multiprocessing.pool.ThreadPool() as executor:
						executor.starmap(GeneticProgrammingIsland.generation, [(self.islands[key], evalPool) for key in self.islands])
					self.evals = sum([self.islands[key].evals for key in self.islands])
					generation += 1
					pbar.set_description(f'Maelstrom Generation {generation}', refresh=False)
					pbar.update(self.evals-evals_old)

					islandTermination = False
					for _, island in self.islands.items():
						islandTermination = islandTermination or island.termination()
					if islandTermination:
						break
		
		
		# identify champions for each species on each island
		for _, island in self.islands.items():
			for species, champions in island.champions.items():
				if species not in self.champions:
					self.champions[species] = dict()
				self.champions[species].update(champions)


		for key in self.islands:
			self.log[key] = self.islands[key].log
		return self #{key:island.log for key, island in self.islands.items()}

	# # Maelstrom-level selection is only intended for gathering champions for comparison
	# def select(self, n, method = "best", k = 5, merge = False, numInitial = None):
	# 	champions = list()
	# 	islandKeys = [key for key in self.islands]
	# 	for key in islandKeys:
	# 		if numInitial:
	# 			champions.append(self.islands[key].select(numInitial, method, k))
	# 		else:
	# 			champions.append(self.islands[key].select(n, method, k))

	# 	if merge:
	# 		mergedChampions = dict()
	# 		for champion in champions:
	# 			for populationKey in champion:
	# 				if populationKey not in mergedChampions:
	# 					mergedChampions[populationKey] = GeneticProgrammingPopulation(survivalSelection="truncation", popSize=n, numChildren=0, roles=[], outputType='', depthLimit=1)
	# 				mergedChampions[populationKey].population.extend(champion[populationKey])
	# 		return mergedChampions
	# 	else:
	# 		for championIndex in range(len(champions)):
	# 			for populationKey in champions[championIndex]:
	# 				tempPopulation = GeneticProgrammingPopulation(survivalSelection="truncation", popSize=n, numChildren=0, roles=[], outputType='', depthLimit=1)
	# 				tempPopulation.population = champions[championIndex][populationKey]
	# 				champions[championIndex][populationKey] = tempPopulation
	# 		return champions


