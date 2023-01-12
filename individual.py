# General-purpose GP individual class - mostly a wrapper for genotype
# TODO: make a little smarter to improve abstraction/generalization capabilities
class GeneticProgrammingIndividual:
	def __init__(self, genotype = None):
		self.fitness = None
		self.genotype = genotype
		self.trials = list()
		self.absoluteFitness = None
		# self.subfitness = list()
	
	def copy(self):
		return GeneticProgrammingIndividual(self.genotype.copy())