from canonicalPopulation import CanonicalGeneticProgrammingPopulation
from island import GeneticProgrammingIsland
from tqdm.auto import tqdm
import multiprocessing

# General-purpose island class that contains and manages multiple populations
# TODO: transition from parameters dictionary to clearer inputs with default values
class CanonicalGeneticProgrammingIsland(GeneticProgrammingIsland):
	
	# Initializes the island and populations based on input configuration parameters and evaluation function
	def __init__(self, populations, evaluationFunction, evaluationkwargs = dict(), evalPool = None, evaluations=None, championsPerGeneration=0, cores=None, position=None, **kwargs):
		# self.parameters = parameters
		self.populations = dict()
		self.generationCount = 0
		for name, config in populations.items():
			self.populations[name] = CanonicalGeneticProgrammingPopulation(**kwargs[config])
			self.populations[name].rampedHalfAndHalf()
		self.evaluation = evaluationFunction
		
		self.evaluationParameters = evaluationkwargs
		
		self.log = dict()
		# if evalPool is None:
		# 	if cores is None:
		# 		cores = min(32, multiprocessing.cpu_count())
		# 	self.evalPool = multiprocessing.Pool(cores)
		# else:
		# 	self.evalPool = evalPool

		if cores is None:
			cores = min(32, multiprocessing.cpu_count())
		self.cores = cores
		self.position = position

		# Fitness evaluations occur here
		with multiprocessing.Pool(self.cores) as evalPool:
			generationData, self.evals = self.evaluation(**self.populations, executor = evalPool, **self.evaluationParameters)
		for key in generationData:
			self.log[key] = [generationData[key]]
		
		self.championsPerGeneration = championsPerGeneration
		
		# identify champions for each species
		self.champions = {key:dict() for key in self.populations}
		for population in self.populations:
			localChampions = self.select(population, self.championsPerGeneration, method = "best")
			for individual in localChampions:
				geneText = individual.genotype.printTree()
				if geneText not in self.champions[population]:
					self.champions[population][geneText] = individual.genotype.copy()
		
		self.imports = dict()
		self.evalLimit = evaluations

	# Performs a single generation of evolution
	def generation(self, evalPool=None):
		self.generationCount += 1
		for population in self.populations:
			if population in self.imports:
				self.populations[population].generateChildren(self.imports[population])
			else:
				self.populations[population].generateChildren()
		self.imports.clear()

		generationData, numEvals = self.evaluation(**self.populations, executor=evalPool, **self.evaluationParameters)
		self.evals += numEvals
		for key in generationData:
			self.log[key].append(generationData[key])

		for population in self.populations:
			self.populations[population].updateHallOfFame()

			# identify champions for each species
			localChampions = self.select(population, self.championsPerGeneration, method = "best")
			for individual in localChampions:
				geneText = individual.genotype.printTree()
				if geneText not in self.champions[population]:
					self.champions[population][geneText] = individual.genotype.copy()

		return self