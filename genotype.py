import math
import random
import itertools

'''General-purpose strong-type GP tree class'''
class GeneticTree:
	primitives = dict()
	transitives = dict()
	literal_initializers = dict()
	DEBUG = False
	local = dict()
	
	'''
	Defines a decorator that can be used to conviently define primitives. Primitives have the notion of RPG-style
	"roles" that can be used to assign classes of capabilities to trees of different species. Primitives also have
	output type and expected input type of children stored as well. This decorator captures the function of the
	primitive and all associated metadata in the primitives dictionary of the GeneticTree class for	programatic
	use by GeneticTree and Node objects at runtime.

	This approach represents a modified approach to a decorator-based primitive scheme implemented by Sean Harris.
	The primary modification made here is the addition of the roles mechanism to avoid needing to create multiple
	files of primitives with large amounts of duplicate content. This implementation also requires the treatment
	of GP literal nodes in a general manner instead of implementing a separate decorator for literals as was done
	in Sean's implementation.
	'''
	@classmethod
	def declarePrimitive(cls, roles, output_type, input_types, *args, transitive = False, literal_init = False, **kwargs):
		if isinstance(roles, str):
			roles = roles, # turns the string into a single-element tuple
		def addPrimitive(func):
			for role in roles:
				if role not in cls.primitives:
					cls.primitives[role] = set()
					cls.transitives[role] = set()
					cls.literal_initializers[role] = dict()
					cls.local[role] = dict()
				cls.primitives[role].add((func, output_type, input_types))
				cls.local[role][func.__name__] = func
				if transitive and len(set(input_types)) == 1:
					cls.transitives[role].add((func, output_type, input_types))
				if literal_init:
					key = (func.__name__, output_type, input_types)
					cls.literal_initializers[role][key] = (args, kwargs)
				if cls.DEBUG: print(f"importing primitive '{func.__name__}' of type {output_type} for role '{role}'", func)
			return func
		return addPrimitive

	'''
	Initializes a tree object with a set of primitives appropriate for the roles assigned to the object and a
	root node of the desired output type.
	'''
	def __init__(self, roles, output_type):
		self.primitiveSet = set()
		self.init_dict = dict()
		self.local = dict()
		if isinstance(roles, str):
			roles = roles, # turns the string into a single-element tuple
		self.roles = roles
		for role in self.roles:
			if role not in self.__class__.primitives:
				print(f"encountered unknown role: {role}")
			else:
				self.primitiveSet |= self.__class__.primitives[role]
				self.init_dict.update(self.__class__.literal_initializers[role])
				self.local.update(self.__class__.local[role])
		assert len(self.primitiveSet) > 0, "No valid roles used in tree declaration"
		self.root = Node(output_type)
		self.branchingFactor = branchingFactor = max([len(primitive[2]) for primitive in self.primitiveSet])
		self.nodeTags = None
		self.depthLimit = 0
		self.hardLimit = 0
		self.depth = 0
		self.size = 0
		self.func = None

	# Performs tree initialization in the GP sense to the calling tree object
	def initialize(self, depth = 1, hardLimit = 0, grow = False, leafProb = 0.5, full = False, **kwargs):
		if grow:
			self.grow(depth, leafProb)
		elif full:
			self.full(depth)
		self.depthLimit = depth
		if hardLimit < depth:
			self.hardLimit = depth*2
		else:
			self.hardLimit = hardLimit
		self.root.initialize(self.init_dict)
		self.nodeTags = self.root.getTags(self.branchingFactor)
		self.depth = math.ceil(math.log(max(list(self.nodeTags.keys())), self.branchingFactor))
		self.size = len(self.nodeTags)
		self.string = self.printTree()
		# self.build()

	def build(self):
		local = dict()
		for role in self.roles:
			if role not in self.__class__.primitives:
				print(f"encountered unknown role: {role}")
			else:
				local.update(self.__class__.local[role])
		self.func = eval(''.join(['lambda context: ', self.string]), local)

	# Full initialization method
	def full(self, depth = 1):
		self.root.full(self.primitiveSet, depth-1)

	# Grow initialization method
	def grow(self, depth = 1, leafProb = 0.5):
		self.root.grow(self.primitiveSet, depth-1, leafProb, reachDepth = True)

	# Execute/evaluate the calling tree
	def execute(self, context):
		if self.func is None:
			self.build()
		return self.func(context)

	# Return a copy of the calling tree
	def copy(self):
		clone = self.__class__(self.roles, self.root.type)
		clone.root = self.root.copy()
		clone.initialize(self.depthLimit, self.hardLimit)
		return clone

	# Random subtree mutation - intended to be called by a copy of a parent
	def subtreeMutation(self):
		for i in range(10):
			target = random.choice(list(self.nodeTags.keys()))
			mutantDepthLimit = self.hardLimit - math.ceil(math.log(target, self.branchingFactor))
			if mutantDepthLimit <= 0:
				depth = 0
			else:
				depth = random.randrange(0, mutantDepthLimit)
			
			if self.root.findTag(target, self.branchingFactor).mutate(self.primitiveSet, depth):
				break # break on successful mutation

		else: # else of for loop calls grow on a random node if all other mutation attempts fail
			target = random.choice(list(self.nodeTags.keys()))
			mutantDepthLimit = self.hardLimit - math.ceil(math.log(target, self.branchingFactor))
			if mutantDepthLimit <= 0:
				depth = 0
			else:
				depth = random.randrange(0, mutantDepthLimit)
			self.root.findTag(target, self.branchingFactor).grow(self.primitiveSet, depth)
		self.initialize(self.depthLimit, self.hardLimit)

	# Random subtree recombination - intended to be called by a copy of a parent
	def subtreeRecombination(self, mate):
		typeOptions = set(self.nodeTags.values()) & set(mate.nodeTags.values())
		if len(typeOptions) == 0:
			print("No matching types for crossover!")
		localTag = random.choice([key for key in self.nodeTags if self.nodeTags[key] in typeOptions])
		mateTag = random.choice([key for key in mate.nodeTags if mate.nodeTags[key] == self.nodeTags[localTag]])
		self.root.assignAtTag(localTag, mate.root.findTag(mateTag, mate.branchingFactor).copy(), self.branchingFactor)
		self.initialize(self.depthLimit, self.hardLimit)

	# Returns a string representation of the expression encoded by the GP tree
	def printTree(self):
		return self.root.printTree()

	def toDict(self):
		return {'roles': self.roles, 'output_type': self.root.type, 'depthLimit': self.depthLimit, 'hardLimit': self.hardLimit, 'root': self.root.toDict()}

	@classmethod
	def fromDict(cls, _dict):
		genotype = cls(_dict['roles'], _dict['output_type'])
		genotype.root.fromDict(genotype.primitiveSet, _dict['root'])
		genotype.initialize(_dict['depthLimit'], _dict['hardLimit'])
		return genotype


'''General-purpose strong-typed GP node class'''
class Node:
	def __init__(self, output_type):
		self.type = output_type
		self.func = None # stores an executable function object
		self.children = list()
		self.value = None

	def initialize(self, init_dict):
		key = (self.func.__name__, self.type, tuple([child.type for child in self.children]))
		if self.value == None and key in init_dict:
			args, kwargs = init_dict[key]
			self.value = self.func(*args, **kwargs)
		for child in self.children:
			child.initialize(init_dict)

	# Accepts the list of available primitives and filters into leaf and internal primitives of acceptable type
	def filterTypePrimitives(self, primitives):
		options = [primitive for primitive in primitives if self.type == primitive[1]]
		if not options:
			print(f"type {self.type} not found in primitives")
			exit()
		leaves = [leaf for leaf in options if leaf[2] == ()]
		internals = [internal for internal in options if internal[2] != ()]
		return leaves, internals

	# Full initialization method for subtree generation
	def full(self, primitives, limit = 0):
		self.value = None
		if self.children: self.children.clear()
		leaves, internals = self.filterTypePrimitives(primitives)

		if limit > 0 and internals:
			self.func, _, input_types = random.choice(internals)
			self.children = [Node(childType) for childType in input_types]
		else:
			self.func, _, _ = random.choice(leaves)

		for i in range(len(self.children)):
			self.children[i].full(primitives, limit-1)

	# Grow initialization method for subtree generation
	def grow(self, primitives, limit = 0, leafProb = 0.5, reachDepth = False):
		self.value = None
		if self.children: self.children.clear()
		leaves, internals = self.filterTypePrimitives(primitives)

		if limit > 0 and internals and (reachDepth or random.random() > leafProb):
			self.func, _, input_types = random.choice(internals)
			self.children = [Node(childType) for childType in input_types]
		else:
			self.func, _, _ = random.choice(leaves)

		if reachDepth and self.children:
			branch = random.choice(range(len(self.children)))
		else:
			branch = -1
		for i in range(len(self.children)):
			if i != branch:
				self.children[i].grow(primitives, limit-1)
			else:
				self.children[i].grow(primitives, limit-1, reachDepth = True)

	def mutate(self, primitives, limit = 0):
		if self.func == None:
			self.grow(primitives, limit)
			return True
		else:
			name = self.func.__name__
			primitive = None
			leaves, internals = self.filterTypePrimitives(primitives)
			if self.children == []:
				options = leaves
			else:
				options = internals

			for option in options:
					if option[0].__name__ == name:
						primitive = option
						break

			if primitive is None:
				return False

			if self.value is None:
				options.remove(primitive)
			options = [option for option in options if option[2] == primitive[2]]
			if len(options) == 0:
				return False

			self.value = None
			self.func, _, _ = random.choice(options)
			return True



	# Execute/evaluate the subtree of the calling node as root
	# def execute(self, context):
	# 	return self.func(self, self.children, context)

	# Return a copy of the subtree of the calling node
	def copy(self):
		clone = Node(self.type)
		clone.func = self.func
		clone.value = self.value
		clone.children = [child.copy() for child in self.children]
		return clone

	# Generate dictionary of unique node ID tags and node types
	def getTags(self, branching, index = 1):
		tags = dict()
		tags[index] = self.type
		for childIndex in range(len(self.children)):
			tags.update(self.children[childIndex].getTags(branching, (index*branching)+childIndex))
		return tags

	# Get the node with the input ID tag
	def findTag(self, target, branching, index = 1):
		if target == index:
			return self
		elif index > target:
			return None

		for childIndex in range(len(self.children)):
			tag = (index*branching)+childIndex
			if tag > target:
				break
			elif tag == target:
				return self.children[childIndex]
			childResult =  self.children[childIndex].findTag(target, branching, tag)
			if childResult is not None:
				return childResult
		if index <= 1:
			print(f"invalid/missing target: {target}") # TODO: make into a proper robust error
		return None

	# Modify node at the input ID tag
	def assignAtTag(self, target, payloadNode, branching, index = 1):
		if target == index:
			self.type = payloadNode.type
			self.func = payloadNode.func
			self.value = payloadNode.value
			self.children = payloadNode.children[:]
			return True
		else:
			for childIndex in range(len(self.children)):
				tag = (index*branching)+childIndex
				if tag > target:
					return False
				elif tag == target:
					self.children[childIndex] = payloadNode
					return True
				elif self.children[childIndex].assignAtTag(target, payloadNode, branching, tag):
					return True
		if index <= 1 and target != index:
			print(f"invalid/missing target: {target}") # TODO: make into a proper robust error
		return False

	# Returns a string representation of the subtree of the calling node for debugging purposes
	def printTree(self):
		if self.value is not None:
			name = f'{self.value}'
		else:
			name = self.func.__name__
		if self.value is not None and not self.children:
			return name
		elif not self.children:
			return f'{name}(context)'
		else:
			child_strings = list()
			num_children = len(self.children)
			for i in range(num_children):
				child_strings.append(self.children[i].printTree())
				if i < num_children-1:
					child_strings.append(',')
			return f'{name}({"".join(child_strings)})'

	def toDict(self):
		return {'func': self.func.__name__, 'type': self.type, 'value': self.value, 'children': [child.toDict() for child in self.children]}

	def fromDict(self, primitives, _dict):
		self.value = _dict['value']
		self.type = _dict['type']
		leaves, internals = self.filterTypePrimitives(primitives)
		if _dict['children'] == []:
			options = leaves
			children = tuple()
		else:
			options = internals
			children = tuple([child['type'] for child in _dict['children']])

		for option in options:
				if option[0].__name__ == _dict['func'] and children == option[2]:
					self.func = option[0]
					break
		else:
			assert False, f'Function {_dict["func"]} of type {_dict["type"]} with children {children} could not be found in options\n{options}'
		self.children.clear()
		for child in _dict['children']:
			self.children.append(Node(child['type']))
			self.children[-1].fromDict(primitives, child)
		# self.children = [Node(child['type']).fromDict(primitives, child) for child in _dict['children']]




# Testbench for debugging - only called if you were to run this file directly
def main():
	GENERAL = "General"
	PREY = "Prey"
	PREDATOR = "Predator"
	ANGLE = "Angle"
	DISTANCE = "Distance"
	@GeneticTree.declarePrimitive((GENERAL, PREY), ANGLE, ())
	def dummy():
		print("Dummy")

	@GeneticTree.declarePrimitive((GENERAL, PREY), ANGLE, (ANGLE, ANGLE))
	def thicc():
		print("thicc")
	# @GeneticTree.declarePrimitive((GENERAL, PREY), (ANGLE,), (ANGLE, ANGLE, ANGLE, ANGLE))
	# def thiccc():
		# print("thiccc")
	print(repr(GeneticTree.primitives))
	fullTree = GeneticTree(PREY, ANGLE)
	fullTree.initialize(4, full = True)
	print("full nodes: " + repr(fullTree.nodeTags))
	print(f"levels: {fullTree.depth}")
	growTree = GeneticTree(GENERAL, ANGLE)
	growTree.initialize(5, grow = True)
	print("grow nodes: " + repr(growTree.nodeTags))
	growTree.subtreeMutation()
	print("mutated grow nodes: " + repr(growTree.nodeTags))
	growTree.subtreeRecombination(fullTree)
	print("recombination grow nodes: " + repr(growTree.nodeTags))

if __name__ == "__main__":
	main()
