import pyhop
import json

def check_enough(state, ID, item, num):
	if getattr(state,item)[ID] >= num: return []
	return False

def produce_enough(state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)

def make_method(name, rule):
	#name: ex.) 'craft wooden axe at bench' or 'punch for wood'
	#rule: says what method produces, requires, consumes, and time
	produces = rule.get('Produces', {})
	requires = rule.get('Requires', {})
	consumes = rule.get('Consumes', {})
	time = rule.get('Time', 0)
	def method(state, ID, item, amount):
		if getattr(state, item)[ID] >= amount:
			return []
		if item not in produces:
			#print("1")
			return False
    # 1. Check if required tools exist
       # if not, planner will need subgoals for them
		subgoals = []
		for tool, needed in requires.items():
			if getattr(state, tool)[ID] < needed:
				subgoals.append(('have_enough', ID, tool, needed))
				#print("2", subgoals)
    # 2. Check if required items exist
       # if not, planner will need subgoals for them
		for res, needed in consumes.items():
			if getattr(state, res)[ID] < needed:
				subgoals.append(('have_enough', ID, res, needed))
				#print("3", subgoals)
    # 3. Check time constraints
		if state.time[ID] < time:
			return False
    # 4. Apply recipe
		subgoals.append(('op_' + name.replace(" ", "_"), ID))
		
		return subgoals
		#state: current inventory, time, tools owned
		#ID: task or goal identifier or resource being planned for

		# your code here
		
	method.__name__ = "produce_" + name.replace(" ", "_")
	return method

def declare_methods(data):
	# some recipes are faster than others for the same product even though they might require extra tools
	# sort the recipes so that faster recipes go first

	# your code here
	# hint: call make_method, then declare the method to pyhop using pyhop.declare_methods('foo', m1, m2, ..., mk)	

	recipes = data["Recipes"]

	#sort by time
	sorted_recipes = sorted(
		recipes.items(),
		key=lambda r: r[1].get("Time", 0)
	)

	methods = []

	for name, rule in sorted_recipes:
		method = make_method(name, rule)
		method.__name__ = "produce_" + name.replace(" ", "_")
		methods.append(method)
	
	pyhop.declare_methods('have_enough', *methods)
				

def make_operator(rule):
	produces = rule.get('Produces', {})
	requires = rule.get('Requires', {})
	consumes = rule.get('Consumes', {})
	time = rule.get('Time', 0)
	
	def operator(state, ID):
		# Check if we have required tools
		for tool, amount in requires.items():
			if getattr(state, tool)[ID] < amount:
				return False
		
		# Check if we have items to consume
		for item, amount in consumes.items():
			if getattr(state, item)[ID] < amount:
				return False
		
		# Check if we have enough time
		if state.time[ID] < time:
			return False
		
		# Apply the recipe: consume items, produce items, use time
		for item, amount in consumes.items():
			current = getattr(state, item)[ID]
			getattr(state, item)[ID] = current - amount
		
		for item, amount in produces.items():
			current = getattr(state, item)[ID]
			getattr(state, item)[ID] = current + amount
		
		state.time[ID] -= time
		
		return state
	
	return operator

def declare_operators(data):
	# your code here
	# hint: call make_operator, then declare the operator to pyhop using pyhop.declare_operators(o1, o2, ..., ok)
	recipes = data["Recipes"]
	
	operators = []
	for name, rule in recipes.items():
		operator = make_operator(rule)
		operator.__name__ = "op_" + name.replace(" ", "_")
		operators.append(operator)
	
	pyhop.declare_operators(*operators)

def add_heuristic(data, ID):
	# prune search branch if heuristic() returns True
	# do not change parameters to heuristic(), but can add more heuristic functions with the same parameters: 
	# e.g. def heuristic2(...); pyhop.add_check(heuristic2)
	def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
		# your code here
		#infinite loop
		#if curr_task in calling_stack:
		#	return True
		if state.time[ID] < 0:
			return True
		
		if calling_stack.count(curr_task) > 2:
			return True
		
		#takes too long
		if depth > 200:
			return True
		#checking time
		

		return False # if True, prune this branch

	pyhop.add_check(heuristic)

def define_ordering(data, ID):
	# if needed, use the function below to return a different ordering for the methods
	# note that this should always return the same methods, in a new order, and should not add/remove any new ones
	def reorder_methods(state, curr_task, tasks, plan, depth, calling_stack, methods):
		#state: what you have
		#curr_task: task currently being decomposed ex.) "wood", "plank", "iron_pickaxe"
		#tasks: tasks still to be planned ^^
		#plan: the history, what have you committed to, what tools youre gonna make, what actions youve already chosen
		#depth: how deep you are in the decomposition tree
		#calling_stack: chain of tasks that led here, can detect: "cycles", "infinite recursion", "im trying to make X bc i need X"
		#methods: list of candidiate methods for this task
		#1.) can this method be applied now?
		checked = []
		for method in methods:
			recipe_name = method.__name__.replace("_", " ")
			rule = data["Recipes"].get(recipe_name, {})

			requires = rule.get("Requires", {})
			consumes = rule.get("Consumes", {})
			time = rule.get("Time", 0)

			missing = 0

			for item, amt in requires.items():
				if state.get(item, 0) < amt:
					missing += 1
			
			for item, amt in consumes.items():
				if state.get(item, 0) < amt:
					missing += 1
			
		checked.append((missing, time, method))
		checked.sort()
		return [m for _, _, m in checked]
	
	pyhop.define_ordering(reorder_methods)

def set_up_state(data, ID):
	state = pyhop.State('state')
	setattr(state, 'time', {ID: data['Problem']['Time']})

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})

	for item, num in data['Problem']['Initial'].items():
		setattr(state, item, {ID: num})

	return state

def set_up_goals(data, ID):
	goals = []
	for item, num in data['Problem']['Goal'].items():
		goals.append(('have_enough', ID, item, num))

	return goals

if __name__ == '__main__':
	import sys
	rules_filename = 'crafting.json'
	if len(sys.argv) > 1:
		rules_filename = sys.argv[1]

	with open(rules_filename) as f:
		data = json.load(f)

	state = set_up_state(data, 'agent')
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')
	define_ordering(data, 'agent')

	pyhop.print_operators()
	pyhop.print_methods()

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	#pyhop.pyhop(state, goals, verbose=1)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
	#pyhop.pyhop(state,[('have_enough', 'agent', 'plank', 1)], verbose = 1)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'wooden_pickaxe', 1)], verbose = 1)
	#pyhop.pyhop(state, [('have_enough', 'agent', 'iron_pickaxe', 1)], verbose = 1)
	pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1), ('have_enough', 'agent', 'rail', 10)], verbose=2)