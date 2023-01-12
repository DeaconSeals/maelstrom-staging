from PredatorPrey.world import World
from genotype import *
import math
import random

GENERAL = "General"
PREY = "Prey"
PREDATOR = "Predator"
ANGLE = "Angle"
DISTANCE = "Distance"

@GeneticTree.declarePrimitive(PREDATOR, DISTANCE, ())
def distance_to_centerPredator(self, input_nodes, context):
    world: World = context["world"]
    return world.predatorPolar[0]
    # return world.cartesian_to_polar(*world.predator)[0]


@GeneticTree.declarePrimitive(PREY, DISTANCE, ())
def distance_to_centerPrey(self, input_nodes, context):
    world: World = context["world"]
    return world.preyPolar[0]
    # return world.cartesian_to_polar(*world.prey)[0]


@GeneticTree.declarePrimitive(PREDATOR, ANGLE, ())
def angle_to_centerPredator(self, input_nodes, context):
    world: World = context["world"]
    return world.add_angles(world.predatorPolar[1], math.pi)
    # return world.add_angles(world.cartesian_to_polar(*world.predator)[1], math.pi)


@GeneticTree.declarePrimitive(PREY, ANGLE, ())
def angle_to_centerPrey(self, input_nodes, context):
    world: World = context["world"]
    return world.add_angles(world.preyPolar[1], math.pi)
    # return world.add_angles(world.cartesian_to_polar(*world.prey)[1], math.pi)


@GeneticTree.declarePrimitive(PREDATOR, DISTANCE, ())
def distance_to_wallPredator(self, input_nodes, context):
    world: World = context["world"]
    return 1 - world.predatorPolar[0]
    # return 1 - world.cartesian_to_polar(*world.predator)[0]


@GeneticTree.declarePrimitive(PREY, DISTANCE, ())
def distance_to_wallPrey(self, input_nodes, context):
    world: World = context["world"]
    return 1 - world.preyPolar[0]
    # return 1 - world.cartesian_to_polar(*world.prey)[0]


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, ())
def distance_to_opponent(self, input_nodes, context):
    world: World = context["world"]
    return world.agent_distance()


@GeneticTree.declarePrimitive(PREDATOR, ANGLE, ())
def angle_to_prey(self, input_nodes, context):
    world: World = context["world"]
    return math.atan2(world.prey[1] - world.predator[1], world.prey[0] - world.predator[0])


@GeneticTree.declarePrimitive(PREY, ANGLE, ())
def angle_to_predator(self, input_nodes, context):
    world: World = context["world"]
    return math.atan2(world.predator[1] - world.prey[1], world.predator[0] - world.prey[0])


@GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
def predator_last_move(self, input_nodes, context):
    world: World = context["world"]
    return world.last_predator_angle


@GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
def prey_last_move(self, input_nodes, context):
    world: World = context["world"]
    return world.last_prey_angle


# @GeneticTree.declarePrimitive(GENERAL, DISTANCE, ())
# def distance_literal(self, input_nodes, context):
#     return random.random() * 2


# @GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
# def angle_literal(self, input_nodes, context):
#     return random.random() * 2 * math.pi


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE,))
def flip_angle(self, input_nodes, context):
    angle = input_nodes[0].execute(context)
    world: World = context["world"]
    return world.add_angles(angle, math.pi)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, ANGLE), transitive = True)
def add_angles(self, input_nodes, context):
    angle_1 = input_nodes[0].execute(context)
    angle_2 = input_nodes[1].execute(context)
    world: World = context["world"]
    return world.add_angles(angle_1, angle_2)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, ANGLE))
def subtract_angles(self, input_nodes, context):
    angle_1 = input_nodes[0].execute(context)
    angle_2 = input_nodes[1].execute(context)
    world: World = context["world"]
    return world.add_angles(angle_1, -angle_2)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, ANGLE), transitive = True)
def average_angles(self, input_nodes, context):
    angle_1 = input_nodes[0].execute(context)
    angle_2 = input_nodes[1].execute(context)
    world: World = context["world"]
    #return (angle_1 + angle_2) / 2
    return math.atan2((math.sin(angle_1) + math.sin(angle_2)) / 2,
                      (math.cos(angle_1) + math.cos(angle_2)) / 2)


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (ANGLE, DISTANCE), transitive = True)
def multiply_angle(self, input_nodes, context):
    angle = input_nodes[0].execute(context)
    distance = input_nodes[1].execute(context)
    world: World = context["world"]
    return math.fmod(angle * distance, 2*math.pi)


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE), transitive = True)
def add_distances(self, input_nodes, context):
    distance_1 = input_nodes[0].execute(context)
    distance_2 = input_nodes[1].execute(context)
    return distance_1 + distance_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE))
def subtract_distances(self, input_nodes, context):
    distance_1 = input_nodes[0].execute(context)
    distance_2 = input_nodes[1].execute(context)
    return distance_1 - distance_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE), transitive = True)
def multiply_distances(self, input_nodes, context):
    distance_1 = input_nodes[0].execute(context)
    distance_2 = input_nodes[1].execute(context)
    return distance_1 * distance_2


@GeneticTree.declarePrimitive(GENERAL, DISTANCE, (DISTANCE, DISTANCE))
def divide_distances(self, input_nodes, context):
    distance_1 = input_nodes[0].execute(context)
    distance_2 = input_nodes[1].execute(context)
    if distance_2 == 0:
        return 2  # Maximum possible distance
    return distance_1 / distance_2


@GeneticTree.declarePrimitive(GENERAL, ANGLE, (DISTANCE, DISTANCE, ANGLE, ANGLE))
def if_greater_than(self, input_nodes, context):
    distance_1 = input_nodes[0].execute(context)
    distance_2 = input_nodes[1].execute(context)
    angle_1 = input_nodes[2].execute(context)
    angle_2 = input_nodes[3].execute(context)
    if distance_1 > distance_2:
        return angle_1
    else:
        return angle_2

@GeneticTree.declarePrimitive(GENERAL, DISTANCE, ())
def distance_const(self, input_nodes, context):
    if self.value is None:
        self.value = random.random() * 2
    return self.value


@GeneticTree.declarePrimitive(GENERAL, ANGLE, ())
def angle_const(self, input_nodes, context):
    if self.value is None:
        self.value = random.random() * 2 * math.pi
    return self.value

def main():
    print(repr(GeneticTree.primitives))
    prey = GeneticTree((PREY, GENERAL), ANGLE)
    prey.full(5)
    predator = GeneticTree((PREDATOR, GENERAL), ANGLE)
    predator.grow(5)

if __name__ == "__main__":
    main()
