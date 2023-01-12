import math
import cmath

class World:
    def __init__(self, predator_move_speed=0.05, prey_move_speed=0.1, agent_radius=0.1, time_limit=200):
        self.predator_move_speed = predator_move_speed
        self.prey_move_speed = prey_move_speed
        self.agent_radius = agent_radius
        self.time_limit = time_limit

        self.predator = (0, -0.5)
        self.prey = (0, 0.5)
        self.predatorPolar = self.cartesian_to_polar(*self.predator)
        self.preyPolar = self.cartesian_to_polar(*self.prey)
        self.last_predator_angle = 0
        self.last_prey_angle = 0
        self.past_predator_positions = [self.predator]
        self.past_prey_positions = [self.prey]
        self.time = 0
        self.predator_comfort = 0
        self.prey_comfort = 0
    
    # Take as input the angle at which the predator and prey want to move and adjust their positions based on the speed (magnitude) of the characters
    def move(self, predator_angle, prey_angle):
        self.predator, self.predatorPolar = self.restrict_point(*self.update_point(*self.predator, predator_angle, self.predator_move_speed))
        self.prey, self.preyPolar = self.restrict_point(*self.update_point(*self.prey, prey_angle, self.prey_move_speed))
        self.last_predator_angle = predator_angle
        self.last_prey_angle = prey_angle
        self.past_predator_positions.append(self.predator)
        self.past_prey_positions.append(self.prey)
        self.predator_comfort += self.predatorPolar[0] #self.cartesian_to_polar(*self.predator)[0]
        self.prey_comfort += 1 - self.preyPolar[0] #self.cartesian_to_polar(*self.prey)[0]
        self.time += 1

    def check_termination(self):
        return self.check_collision() or self.time >= self.time_limit

    def check_collision(self):
        return self.agent_distance() < 2 * self.agent_radius

    def agent_distance(self):
        return math.sqrt((self.predator[0] - self.prey[0]) ** 2 + (self.predator[1] - self.prey[1]) ** 2)
        # return math.dist(self.predator, self.prey)
        
    # Calculate the resultant x,y coordinates based on input coordinates, angle of movement, and magnitude of movement
    def update_point(self, x, y, angle, distance):
        x += math.cos(angle) * distance
        y += math.sin(angle) * distance
        return x, y

    def cartesian_to_polar(self, x, y):
        # r = math.sqrt(x**2 + y**2)
        # angle = math.atan2(y, x)
        # return r, angle
        return cmath.polar(complex(x, y))

    def polar_to_cartesian(self, r, angle):
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        return x, y

    # bound the input coordinate to the nearest in-bounds location
    def restrict_point(self, x, y):
        r, angle = self.cartesian_to_polar(x, y)
        r = min(r, 1 - self.agent_radius)
        return self.polar_to_cartesian(r, angle), (r, angle)

    # add two angles in radians and bound that to [0, 2*pi)
    def add_angles(self, angle_1, angle_2):
        return math.fmod(angle_1 + angle_2 + 2*math.pi, 2*math.pi)
