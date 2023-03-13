from maelstrom.population import GeneticProgrammingPopulation
from tqdm.auto import tqdm
import multiprocessing


# General-purpose island class that contains and manages multiple populations
# TODO: transition from parameters dictionary to clearer inputs with default values
class GeneticProgrammingIsland:
    # Initializes the island and populations based on input configuration parameters and evaluation function
    def __init__(
        self,
        populations,
        evaluationFunction,
        evaluationkwargs=dict(),
        evalPool=None,
        evaluations=None,
        championsPerGeneration=0,
        cores=None,
        position=None,
        **kwargs,
    ):
        # self.parameters = parameters
        self.populations = dict()
        self.generationCount = 0
        for name, config in populations.items():
            self.populations[name] = GeneticProgrammingPopulation(**kwargs[config])
            self.populations[name].rampedHalfAndHalf()
        self.evaluation = evaluationFunction

        self.evaluationParameters = evaluationkwargs

        self.log = dict()

        if cores is None:
            cores = min(32, multiprocessing.cpu_count())
        self.cores = cores
        self.position = position

        # Fitness evaluations occur here
        with multiprocessing.Pool(self.cores) as evalPool:
            generationData, self.evals = self.evaluation(
                **self.populations, executor=evalPool, **self.evaluationParameters
            )
        for key in generationData:
            self.log[key] = [generationData[key]]

        self.championsPerGeneration = championsPerGeneration

        # identify champions for each species
        self.champions = {key: dict() for key in self.populations}
        for population in self.populations:
            localChampions = self.select(
                population, self.championsPerGeneration, method="best"
            )
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

        generationData, numEvals = self.evaluation(
            **self.populations, executor=evalPool, **self.evaluationParameters
        )
        self.evals += numEvals
        for key in generationData:
            self.log[key].append(generationData[key])

        for population in self.populations:
            self.populations[population].selectSurvivors()
            self.populations[population].updateHallOfFame()

            # identify champions for each species
            localChampions = self.select(
                population, self.championsPerGeneration, method="best"
            )
            for individual in localChampions:
                geneText = individual.genotype.printTree()
                if geneText not in self.champions[population]:
                    self.champions[population][geneText] = individual.genotype.copy()

        return self

    # Termination check
    def termination(self):
        stop = False
        for key in self.populations:
            stop = stop or self.populations[key].checkTermination()
            if stop:
                break
        return stop or (self.evalLimit is not None and self.evals >= self.evalLimit)

    # Selection from populations
    def select(self, population, n, method="uniform", k=5):
        chosen = self.populations[population].selectUnique(n, method, k)
        for index in range(len(chosen)):
            chosen[index] = chosen[index].copy()
        return chosen

    # Perfoms a single run of evolution until termination
    def run(self):
        with multiprocessing.Pool(self.cores) as evalPool:
            with tqdm(
                total=self.evalLimit, unit=" evals", position=self.position
            ) as pbar:
                pbar.set_description(
                    f"COEA Generation {self.generationCount}", refresh=False
                )
                pbar.update(self.evals)
                while not self.termination():
                    evals_old = self.evals
                    # print(f"Beginning generation: {generation}\tEvaluations: {self.evals}")
                    self.generation(evalPool)
                    pbar.set_description(
                        f"COEA Generation {self.generationCount}", refresh=False
                    )
                    pbar.update(self.evals - evals_old)
        return self  # self.log

    def build(self):
        [population.build() for population in self.populations.values()]

    def clean(self):
        [population.clean() for population in self.populations.values()]
