# TODO: make a little smarter to improve abstraction/generalization capabilities
class GeneticProgrammingIndividual:
    """
    General-purpose GP individual class - mostly a wrapper for genotype
    """

    def __init__(self, genotype=None):
        """
        Args:
            genotype: genotype of the individual
        """
        self.fitness = None
        self.genotype = genotype
        self.trials = []
        self.absolute_fitness = None
        # self.subfitness = list()

    def copy(self):
        """
        Returns:
            copy of the individual
        """
        return GeneticProgrammingIndividual(self.genotype.copy())

    def build(self):
        """
        Builds the individual
        """
        self.genotype.build()

    def clean(self):
        """
        Cleans the individual
        """
        self.genotype.clean()
