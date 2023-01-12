from genotype import GeneticTree
from individual import GeneticProgrammingIndividual
from population import GeneticProgrammingPopulation

import random
import math
import statistics
from collections import OrderedDict

# General-purpose GP population class that contains and manages individuals
# TODO: transition from parameters dictionary to clearer inputs with default values
class CanonicalGeneticProgrammingPopulation (GeneticProgrammingPopulation):
	def __init__(self, popSize, roles, outputType, depthLimit, hardLimit = None, depthMin = 1, evaluations = None, parentSelection = "uniform", mutation = 0.05, reproduction = 0.0, **kwargs):
		self.population = list()
		# self.parameters = parameters
		self.popSize = popSize
		self.roles = roles
		self.outputType = outputType
		self.depthLimit = depthLimit
		self.hardLimit = hardLimit if hardLimit is not None else self.depthLimit*2
		self.depthMin = depthMin
		self.evalLimit = evaluations
		self.evals = 0
		self.parentSelection = parentSelection
		self.mutation = mutation
		self.reproduction = reproduction
		self.optionalParams = kwargs
		self.hallOfFame = OrderedDict()
		self.CIAO = list()

	# Generate children through the selection of parents, recombination or mutation of parents to form children, then the migration of children
	# into the primary population depending on survival strategy
	# TODO: generalize this so it relies on operations of the individual class instead of skipping that and working directly with the genotype
	def generateChildren(self, imports = None):
		
		if imports != None:
			children = [migrant.copy() for migrant in imports]
		else:
			children = list()

		copied = set()

		while len(children) < self.popSize:
			prob = random.random()
			if prob <= self.mutation:
				children.append(self.selectParents(1)[0].copy())
				children[-1].genotype.subtreeMutation()
			elif prob <= self.mutation + self.reproduction:
				parent = self.selectParents(1)[0]
				if parent.genotype.string in copied:
					continue
				copied.add(parent.genotype.string)
				children.append(parent.copy())
			else:
				parents = self.selectParents(2)
				children.append(parents[0].copy())
				children[-1].genotype.subtreeRecombination(parents[1].genotype)

		self.population = children