class unorderedWrapper:
	def __init__(self, __unordered_id, func, *args, **kwargs):
		self.func = func
		self.args = args
		self.kwargs = kwargs
		self.unordered_id = __unordered_id

	def execute(self):
		return (self.unordered_id, self.func(*self.args, **self.kwargs))