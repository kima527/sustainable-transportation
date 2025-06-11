# make_ny_vrp.py  (put this next to your pyproject or anywhere in the venv)

from pathlib import Path
from pysolver.instance.parsing_csv import (
    parse_instance_from_csv,
    save_instance_as_vrp,
)

nodes   = Path("../../resources/data/NewYorkManhattan.nodes")
routes  = Path("../../resources/data/NewYorkManhattan.routes")

# choose your numbers
cap      = 2800      # per‑truck capacity
fleet_sz = 8       # how many trucks you want noted in the header

inst = parse_instance_from_csv(
    nodes_path=nodes,
    routes_path=routes,
    capacity=cap,
    fleet_size=fleet_sz,
)

print(vars(inst.vertices[0]))
print(f"Number of arcs in instance.arcs: {len(inst.arcs)}")

mapping_output_path = Path("../../resources/instances/test_instances/NewYorkManhattan.id_map.txt")

with open(mapping_output_path, "w") as f:
    for vertex in inst.vertices:
        # VRP index = vertex_id + 1
        index = vertex.vertex_id + 1
        original_id = vertex.vertex_name
        f.write(f"{index} {original_id}\n")

print(f"Wrote {mapping_output_path}")

save_instance_as_vrp(
    instance     = inst,
    output_path  = Path("../../resources/instances/test_instances/NewYorkManhattan.vrp"),
    name         = "NEWYORK_MANHATTAN",
    comment      = "Exported from .nodes/.routes",
)

print("Wrote resources/instances/test_instances/NewYorkManhattan.vrp")
