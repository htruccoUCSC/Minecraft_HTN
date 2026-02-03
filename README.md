# Minecraft HTN Planner

This program contains a basic Hierarchal Task Network for minecraft crafting recipes.  

The task network employs the following heuristics and rules to ensure the ability to complete tasks:

- all tools have a boolean value that tracks if they have been made already
- ingots are ordered to be produced last
- methods are sorted by shortest time
- iron axes are strictly forbidden unless the goal specifies them (they are useless)
- avoid making axes for minimal amounts of wood
- avoid making unnecessary pickaxes

## Sonny worked on

- work for manualHTN.py
- declare_operators in autoHTN
- make_operators in autoHTN
- helper functions in autoHTN
- general debugging

## Ava worked on

- make_methods in autoHTN
- declare_methods in autoHTN
- add_heuristics in autoHTN
