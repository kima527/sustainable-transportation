# make_ny_vrp.py  (put this next to your pyproject or anywhere in the venv)

from pathlib import Path
from pysolver.instance.parsing_csv import (
    parse_instance_from_csv,
    save_instance_as_vrp,
)

nodes   = Path("../../resources/data/NewYorkState.nodes")
routes  = Path("../../resources/data/NewYorkState.routes")

inst = parse_instance_from_csv(
    nodes_path=nodes,
    routes_path=routes
)

print(vars(inst.vertices[0]))
print(f"Number of arcs in instance.arcs: {len(inst.arcs)}")

mapping_output_path = Path("../../resources/instances/test_instances/NewYorkState.id_map.txt")

with open(mapping_output_path, "w") as f:
    for vertex in inst.vertices:
        # VRP index = vertex_id + 1
        index = vertex.vertex_id + 1
        original_id = vertex.vertex_name
        f.write(f"{index} {original_id}\n")

print(f"Wrote {mapping_output_path}")

save_instance_as_vrp(
    instance     = inst,
    output_path  = Path("../../resources/instances/test_instances/NewYorkState.vrp"),
    name         = "NEWYORK_STATE",
    comment      = "Exported from .nodes/.routes",
)

print("Wrote resources/instances/test_instances/NewYorkState.vrp")
