from PredatorPrey.world import World
from maelstrom.genotype import *
import math
import random

GENERAL = "General"
PREY = "Prey"
PREDATOR = "Predator"
ANGLE = "Angle"
DISTANCE = "Distance"


@GeneticTree.declarePrimitive(PREDATOR, DISTANCE, ())
def distance_to_centerPredator(context):
    world: World = context["world"]
    return world.predatorPolar[0]
    # return world.cartesian_to_polar(*world.predator)[0]


@GeneticTree.declarePrimitive(PREY, DISTANCE, ())
def distance_to_centerPrey(context):
    world: World = context["world"]
    return world.preyPolar[0]
    # return world.cartesian_to_polar(*world.prey)[0]


@GeneticTree.declarePrimitive(PREDATOR, ANGLE, ())
def angle_to_centerPredator(context):
    world: World = context["world"]
    return world.add_angles(world.predatorPolar[1], math.pi)
    # return world.add_angles(world.cartesian_to_polar(*world.predator)[1], math.pi)


@GeneticTree.declarePrimitive(PREY, ANGLE, ())
def angle_to_centerPrey(context):
    world: World = context["world"]
    return world.add_angles(world.preyPolar[1], math.pi)
    # return world.add_angles(world.cartesian_to_polar(*world.prey)[1], math.pi)


@GeneticTree.declarePrimitive(PREDATOR, DISTANCE, ())
def distance_to_wallPredator(context):
    world: World = context["world"]
    return 1 - world.predatorPolar[0]
    # return 1 - world.cartesian_to_polar(*world.predator)[0]


@GeneticTree.declarePrimitive(PREY, DISTANCE, ())
def distance_to_wallPrey(context):
    world: World = context["world"]
    return 1 - world.preyPolar[0]
    # return 1 - world.cartesian_to_polar(*world.prey)[0]


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, ())
def distance_to_opponent(context):
    world: World = context["world"]
    return world.agent_distance()


@GeneticTree.declarePrimitive(PREDATOR, ANGLE, ())
def angle_to_prey(context):
    world: World = context["world"]
    return math.atan2(
        world.prey[1] - world.predator[1], world.prey[0] - world.predator[0]
    )


@GeneticTree.declarePrimitive(PREY, ANGLE, ())
def angle_to_predator(context):
    world: World = context["world"]
    return math.atan2(
        world.predator[1] - world.prey[1], world.predator[0] - world.prey[0]
    )


@GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
def predator_last_move(context):
    world: World = context["world"]
    return world.last_predator_angle


@GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
def prey_last_move(context):
    world: World = context["world"]
    return world.last_prey_angle


# @GeneticTree.declarePrimitive(GENERAL, DISTANCE, ())
# def distance_literal(self, input_nodes, context):
#     return random.random() * 2


# @GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
# def angle_literal(self, input_nodes, context):
#     return random.random() * 2 * math.pi


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE,))
def flip_angle(angle):
    return World.add_angles(angle, math.pi)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, ANGLE), transitive=True)
def add_angles(angle_1, angle_2):
    return World.add_angles(angle_1, angle_2)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, ANGLE))
def subtract_angles(angle_1, angle_2):
    return World.add_angles(angle_1, -angle_2)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, ANGLE), transitive=True)
def average_angles(angle_1, angle_2):
    return math.atan2(
        (math.sin(angle_1) + math.sin(angle_2)) / 2,
        (math.cos(angle_1) + math.cos(angle_2)) / 2,
    )


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, DISTANCE), transitive=True)
def multiply_angle(angle, distance):
    return math.fmod(angle * distance, 2 * math.pi)


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE), transitive=True)
def add_distances(distance_1, distance_2):
    return distance_1 + distance_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE))
def subtract_distances(distance_1, distance_2):
    return distance_1 - distance_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE), transitive=True)
def multiply_distances(distance_1, distance_2):
    return distance_1 * distance_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE))
def divide_distances(distance_1, distance_2):
    if distance_2 == 0:
        return 2  # Maximum possible distance
    return distance_1 / distance_2


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (DISTANCE, DISTANCE, ANGLE, ANGLE))
def if_greater_than(distance_1, distance_2, angle_1, angle_2):
    if distance_1 > distance_2:
        return angle_1
    else:
        return angle_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (), 2, literal_init=True)
def distance_const(maximum):
    return random.random() * maximum


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (), 2 * math.pi, literal_init=True)
def angle_const(maximum):
    return random.random() * maximum


def main():
    print(repr(GeneticTree.primitives))
    prey = GeneticTree((PREY, GENERAL), ANGLE)
    prey.full(5)
    predator = GeneticTree((PREDATOR, GENERAL), ANGLE)
    predator.grow(5)


if __name__ == "__main__":
    main()
