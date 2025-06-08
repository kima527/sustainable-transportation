# make_ny_vrp.py  (put this next to your pyproject or anywhere in the venv)

from pathlib import Path
from pysolver.instance.parsing_csv import (
    parse_instance_from_csv,
    save_instance_as_vrp,
)

nodes   = Path("resources/data/NewYork.merged.nodes")
routes  = Path("resources/data/newyork.routes")

# choose your numbers
cap      = 2800      # per‑truck capacity
fleet_sz = 8       # how many trucks you want noted in the header

inst = parse_instance_from_csv(
    nodes_path=nodes,
    routes_path=routes,
    capacity=cap,
    fleet_size=fleet_sz,
)

save_instance_as_vrp(
    instance     = inst,
    output_path  = Path("resources/instances/newyork.vrp"),
    name         = "NEWYORK_STATE",
    comment      = "Exported from .nodes/.routes",
)

print("Wrote resources/instances/newyork.vrp")
