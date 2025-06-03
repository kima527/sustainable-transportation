from pathlib import Path
from .parsing_csv import parse_instance_from_csv, save_instance_as_vrp
from .interface import create_cpp_instance

# Define paths to your test files
nodes_path = Path("resources/data/NewYorkManhattan.nodes")
routes_path = Path("resources/data/NewYork.routes")

# Define instance parameters
capacity = 883
fleet_size = 12

# Parse instance from your files
py_instance = parse_instance_from_csv(
    nodes_path=nodes_path,
    routes_path=routes_path,
    capacity=capacity,
    fleet_size=fleet_size
)

# Print parsed vertices and arcs
print(f"Depot: {py_instance.depot}")
print(f"{len(list(py_instance.customers))} customers loaded")

for (i, j), arc in list(py_instance.arcs.items())[:5]:
    print(f"Arc from {i} to {j}: cost={arc.cost:.2f}s, distance={arc.distance:.2f}km")

# Convert to C++ instance using routingblocks
cpp_instance = create_cpp_instance(py_instance)
print(f"Successfully created C++ instance with {cpp_instance.number_of_vertices} vertices.")

save_instance_as_vrp(
    instance=py_instance,
    output_path=Path("resources/instances/test_instances/newyork_manhattan.vrp"),
    name="NEW YORK MANHATTAN",
    comment="Exported from .nodes/.routes"
)