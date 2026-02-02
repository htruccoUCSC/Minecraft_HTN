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
	def method(state, ID):
		
    # 1. If this recipe does not help achieve ID, fail
		if ID not in produces:
			return False
    # 2. Check if required tools exist
       # if not, planner will need subgoals for them
		subgoals = []
		for tool, amount in requires.items():
			if state.get(tool, 0) < amount:
				subgoals.append(("get", tool))
    # 3. Check if required items exist
       # if not, planner will need subgoals for them
		for item, amount in consumes.items():
			if state.get(item, 0) < amount:
				subgoals.append(("get", item))
    # 4. Check time constraints
		if state.time < time:
			return False
    # 5. Apply recipe
		subgoals.append(("apply", name))
		return subgoals
		#state: current inventory, time, tools owned
		#ID: task or goal identifier or resource being planned for

		# your code here
		
	method.__name__ = name.replace(" ", "_")
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

	methods_by_product = {}
	for name, rule in sorted_recipes:
		method = make_method(name, rule)

		for product in rule.get("Produces", {}):
			methods_by_product.setdefault(product, []).append(method)

	for product, methods in methods_by_product.items():
		pyhop.declare_methods(product, *methods)
				

def make_operator(rule):
	def operator(state, ID):
		# your code here
		pass
	return operator

def declare_operators(data):
	# your code here
	# hint: call make_operator, then declare the operator to pyhop using pyhop.declare_operators(o1, o2, ..., ok)
	pass

def add_heuristic(data, ID):
	# prune search branch if heuristic() returns True
	# do not change parameters to heuristic(), but can add more heuristic functions with the same parameters: 
	# e.g. def heuristic2(...); pyhop.add_check(heuristic2)
	def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
		# your code here
		return False # if True, prune this branch

	pyhop.add_check(heuristic)

def define_ordering(data, ID):
	# if needed, use the function below to return a different ordering for the methods
	# note that this should always return the same methods, in a new order, and should not add/remove any new ones
	def reorder_methods(state, curr_task, tasks, plan, depth, calling_stack, methods):
		return methods
	
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

	# pyhop.print_operators()
	# pyhop.print_methods()
	for recipe_name, recipe_data in data["Recipes"].items():
		print(recipe_name)
		print(recipe_data)

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=1)
	# pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
