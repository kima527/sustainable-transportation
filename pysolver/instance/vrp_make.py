# vrp_make.py ── create .vrp + id_map.txt for all cities in city_configs.json
#
#   python vrp_make.py
#
#   outputs to:
#       resources/instances/test_instances/<city>.vrp
#       resources/instances/test_instances/<city>.id_map.txt

from pathlib import Path
import json

from pysolver.instance.parsing_csv import (
    parse_instance_from_csv
)

# --------------------------------------------------------------------------
# locate folders
PROJ_ROOT    = Path(__file__).resolve().parents[2]          # project root
DATA_DIR     = PROJ_ROOT / "resources" / "data"
INST_OUT_DIR = PROJ_ROOT / "resources" / "instances" / "test_instances"
CFG_FILE     = DATA_DIR / "city_configs.json"

INST_OUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
def build_vrp(city: str, spec: dict):
    """Create <city>.vrp and <city>.id_map.txt from config spec."""
    nodes_path  = DATA_DIR / spec["nodes_path"]
    routes_path = DATA_DIR / spec["routes_path"]

    # ---- capacity & fleet size (legacy weight capacity for header) ----------
    cap_weight = spec["fleets"][0]["Payload [kg]"]
    cap_volume = spec["fleets"][0]["Loading area volume [m3]"]
    fleet_size = sum(f["Carrier count"] for f in spec["fleets"])

    inst = parse_instance_from_csv(
        nodes_path=nodes_path,
        routes_path=routes_path,
        capacity_weight=cap_weight,
        capacity_volume=cap_volume,
        fleet_size=fleet_size,
    )

    city_slug = city.lower()

    # ----------- id_map.txt  -----------------------------------------------
    id_map_path = INST_OUT_DIR / f"{city_slug}.id_map.txt"
    with id_map_path.open("w") as mp:
        for v in inst.vertices:
            mp.write(f"{v.vertex_id + 1} {v.vertex_name}\n")

    # ----------- .vrp file --------------------------------------------------
    vrp_path = INST_OUT_DIR / f"{city_slug}.vrp"
    with vrp_path.open("w") as f:

        # classic header
        f.write(f"NAME : {city.upper()}\n")
        f.write("TYPE : HFVRP\n")
        f.write("COMMENT : generated from city_configs.json\n")
        f.write(f"DIMENSION : {len(inst.vertices)}\n")
        f.write("EDGE_WEIGHT_TYPE : EXPLICIT\n")
        f.write(f"CAPACITY_WEIGHT : {cap_weight}\n\n")

        # ---- fleet block ---------------------------------------------------
        f.write("FLEET_SECTION\n")
        for idx, fl in enumerate(spec["fleets"], 1):
            f.write(
                f"{idx} "
                f"{fl['Carrier type']} "
                f"{fl['Carrier count']} "
                f"{fl['Payload [kg]']} "
                f"{fl['Loading area volume [m3]']} "
                f"{fl.get('max_range', 999999)} "
                f"{fl['Aquisition cost [€]']}\n"
            )
        f.write("END_FLEET_SECTION\n\n")

        # ---- city-level info ----------------------------------------------
        f.write("CITY_INFO_SECTION\n")
        for k, v in spec.items():
            if k in ("nodes_path", "routes_path", "fleets"):
                continue
            f.write(f"{k} : {v}\n")
        f.write("END_CITY_INFO_SECTION\n\n")

        # ---- coordinates ---------------------------------------------------
        f.write("NODE_COORD_SECTION\n")
        for v in inst.vertices:
            f.write(f"{v.vertex_id + 1} {v.x_coord:.6f} {v.y_coord:.6f}\n")

        # ---- demands (weight) ---------------------------------------------
        f.write("\nDEMAND_SECTION\n")
        for v in inst.vertices:
            f.write(f"{v.vertex_id + 1} {v.demand}\n")

        # ---- depot ---------------------------------------------------------
        f.write("\nDEPOT_SECTION\n")
        f.write(f"{inst.depot.vertex_id + 1}\n-1\n")
        f.write("EOF\n")

    print(f"✅ {city}:  {vrp_path.name}, {id_map_path.name} written")

# --------------------------------------------------------------------------
def main():
    with CFG_FILE.open() as f:
        configs = json.load(f)

    for city, spec in configs.items():
        try:
            build_vrp(city, spec)
        except Exception as e:
            print(f"⚠️ {city}: {e}")

if __name__ == "__main__":
    main()
