import pandas as pd

# Load nodes files and extract valid node IDs
manhattan_nodes = pd.read_csv("../../resources/data/NewYorkManhattan.nodes", delim_whitespace=True, header=0)
state_nodes = pd.read_csv("../../resources/data/NewYorkState.nodes", delim_whitespace=True, header=0)

manhattan_ids = set(manhattan_nodes['Id'])
state_ids = set(state_nodes['Id'])

# Load big routes file
routes = pd.read_csv("../../resources/data/newyork.routes", delim_whitespace=True, header=0)

# Filter routes for Manhattan
manhattan_routes = routes[routes['From'].isin(manhattan_ids) & routes['To'].isin(manhattan_ids)]
# Filter routes for State
state_routes = routes[routes['From'].isin(state_ids) & routes['To'].isin(state_ids)]

# Save the split routes to resources/data
manhattan_routes.to_csv("../../resources/data/NewYorkManhattan.routes", sep=' ', index=False)
state_routes.to_csv("../../resources/data/NewYorkState.routes", sep=' ', index=False)

print("Splitting completed. Files saved in /resources/data.")
