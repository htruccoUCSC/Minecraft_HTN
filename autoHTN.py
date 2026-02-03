import pyhop
import json

def check_enough(state, ID, item, num):
	if getattr(state,item)[ID] >= num: 
		return []
	return False

def produce_enough(state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
	# check if we've already made this tool to avoid redundant work
	# much simpler than handling this in the heuristic functions
	if ("made_" + item) in state.__dict__:
		if (getattr(state, "made_"+ item)[ID] is True):
			return False
		else:
			setattr(state, "made_"+ item, {ID: True})

	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)

def make_method(name, rule):
	requires = rule.get('Requires', {})
	consumes = rule.get('Consumes', {})
	def method(state, ID):
		subgoals = []
		if consumes:
			# prioritize ingots to be produced last
			# this fixes a surprising amount of ordering issues
			if 'ingot' in consumes:
				for item, quantity in consumes.items():
						subgoals.append(('have_enough', ID, item, quantity))
			else:	
				for item, quantity in consumes.items():
						subgoals.insert(0, ('have_enough', ID, item, quantity))

		if requires:
			for tool, quantity in requires.items():
				subgoals.append(('have_enough', ID, tool, quantity))
		
		subgoals.append(("op_" + name.replace(" ", "_"), ID))
		return subgoals
	
	method.__name__ = name.replace(" ", "_")
	return method

def declare_methods(data):
	# Group methods by the item they produce
	methods_by_product = {}

	for recipe_name, recipe in data["Recipes"].items():
		produces = recipe['Produces']
		requires = recipe.get('Requires', {})
		consumes = recipe.get('Consumes', {})
		time = recipe['Time']

		# Create the method for this recipe
		method = make_method(recipe_name, {
			'Produces': produces,
			'Requires': requires,
			'Consumes': consumes,
			'Time': time
		})

		# Determine the task name based on what the recipe produces
		product_name = next(iter(produces))
		task_name = f'produce_{product_name}'

		# Add method to the appropriate group
		if task_name not in methods_by_product:
			methods_by_product[task_name] = []
		methods_by_product[task_name].append({'method': method, 'time': time})

	# Sort methods by time (faster methods first) and register with pyhop
	for task_name, method_entries in methods_by_product.items():
		method_entries.sort(key=lambda entry: entry['time'])
		method_functions = [entry['method'] for entry in method_entries]
		pyhop.declare_methods(task_name, *method_functions)
				

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
	recipes = data["Recipes"]

	operators = []
	for name, rule in recipes.items():
		operator = make_operator(rule)
		operator.__name__ = "op_" + name.replace(" ", "_")
		operators.append(operator)
	
	pyhop.declare_operators(*operators)


def add_heuristic(data, ID):
	"""
	Add heuristic functions to prune inefficient search branches.
	Each heuristic returns True to prune the branch, False to continue.
	"""
	
	# Extract goal items for easy lookup
	goal_items = set(data['Problem']['Goal'].keys())
	goal_quantities = data['Problem']['Goal']
	
	# Calculate wood requirements based on goals
	# Wood is needed directly, or indirectly through planks (4 planks per wood) and sticks (8 sticks per wood)
	wood_needed_for_goals = 0
	if "wood" in goal_quantities:
		wood_needed_for_goals += goal_quantities["wood"]
	if "plank" in goal_quantities:
		wood_needed_for_goals += goal_quantities["plank"] / 4
	if "stick" in goal_quantities:
		wood_needed_for_goals += goal_quantities["stick"] / 8

	# --- Helper functions ---
	
	def is_producing_item(task, item_name):
		"""Check if task is trying to produce the specified item."""
		if task[0] == 'produce' and len(task) >= 3:
			return task[2] == item_name
		return task[0] == f'produce_{item_name}'

	def is_producing_any_of(task, item_names):
		"""Check if task is trying to produce any of the specified items."""
		return any(is_producing_item(task, item) for item in item_names)

	# --- Heuristic: Prune unnecessary iron_axe production ---
	
	def prune_unnecessary_iron_axe(state, curr_task, tasks, plan, depth, calling_stack):
		"""
		Don't craft iron_axe unless it's explicitly required as a goal.
		It's identical to the stone_axe but takes more time to make
		"""
		if is_producing_item(curr_task, 'iron_axe'):
			if 'iron_axe' not in goal_items:
				return True
		return False

	# --- Heuristic: Prune unnecessary wood-chopping axes ---
	
	def prune_unnecessary_wood_axes(state, curr_task, tasks, plan, depth, calling_stack):
		"""
		Don't craft wooden_axe or stone_axe if we can gather enough wood by punching
		within the available time, and these axes aren't explicitly required as goals.
		"""
		if is_producing_any_of(curr_task, ['wooden_axe', 'stone_axe']):
			# Skip if axes are explicitly required
			if 'wooden_axe' in goal_items or 'stone_axe' in goal_items:
				return False
			
			# Calculate if we have enough time to punch for remaining wood
			wood_still_needed = wood_needed_for_goals - state.wood[ID]
			time_to_punch = wood_still_needed * 4
			
			if time_to_punch <= state.time[ID]:
				return True
		
		return False

	# --- Heuristic: Prune redundant pickaxe upgrades ---
	
	def prune_redundant_pickaxe_production(state, curr_task, tasks, plan, depth, calling_stack):
		"""
		Don't start producing iron_pickaxe if we're already planning to get a stone_pickaxe.
		This prevents wasted effort on intermediate tools when a better one is coming.
		"""
		if curr_task == ('produce', ID, 'iron_pickaxe'):
			if ('have_enough', ID, 'stone_pickaxe', 1) in tasks:
				return True
		return False

	# Register all heuristics with pyhop
	pyhop.add_check(prune_unnecessary_iron_axe)
	pyhop.add_check(prune_unnecessary_wood_axes)
	pyhop.add_check(prune_redundant_pickaxe_production)

def set_up_state(data, ID):
	state = pyhop.State('state')
	setattr(state, 'time', {ID: data['Problem']['Time']})

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})
		# flags that track what tools we have made
		setattr(state, "made_" + item, {ID: False})

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

	pyhop.print_operators()
	pyhop.print_methods()

	pyhop.pyhop(state, goals, verbose=1)