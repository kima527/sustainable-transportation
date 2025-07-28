# vrp_make.py ── create .vrp + id_map.txt for all cities in city_configs.json
#
#   python vrp_make.py
#
#   outputs to:
#       resources/instances/test_instances/<city>.vrp
#       resources/instances/test_instances/<city>.id_map.txt
from gettext import Catalog
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
CATALOG_FILE  = DATA_DIR / "fleet_catalog.json"

INST_OUT_DIR.mkdir(parents=True, exist_ok=True)
CATALOG = json.loads(CATALOG_FILE.read_text())

# --------------------------------------------------------------------------
def build_vrp(city: str, spec: dict):
    """Create <city>.vrp and <city>.id_map.txt from config spec."""
    nodes_path  = DATA_DIR / spec["nodes_path"]
    routes_path = DATA_DIR / spec["routes_path"]

    mix: dict[str, int] = spec["fleets"]  # type id  →  count

    fleet_rows = []
    for typ, cnt in mix.items():
        cat = CATALOG[typ]
        fleet_rows.append(dict(
            typ=typ,
            cnt=cnt,
            vol=cat["volume_m3"],
            pay_w=cat["payload_kg"],
            acq_c=cat["acq_cost"],
            con_kWh=cat["cons_kWh_km"],
            con_l=cat["cons_l_km"],
            m_rng=cat["max_range_km"],
            main_c=cat["maint_c_km"],
        ))

    initial_mix: dict[str, int] = spec["initial_fleet"]  # type id  →  count

    initial_fleet_rows = []
    for typ, cnt in initial_mix.items():
        cat = CATALOG[typ]
        initial_fleet_rows.append(dict(
            typ=typ,
            cnt=cnt,
            vol=cat["volume_m3"],
            pay_w=cat["payload_kg"],
            acq_c=cat["acq_cost"],
            con_kWh=cat["cons_kWh_km"],
            con_l=cat["cons_l_km"],
            m_rng=cat["max_range_km"],
            main_c=cat["maint_c_km"],
        ))

    # ---- capacity & fleet size (legacy weight capacity for header) ----------
    cap_weight = fleet_rows[0]["pay_w"]
    cap_volume = fleet_rows[0]["vol"]
    fleet_size = sum(row["cnt"] for row in fleet_rows)
    initial_fleet_size = sum(row["cnt"] for row in initial_fleet_rows)
    max_work_time=3600 * float(spec["Average working hours per day"])
    utility_other=float(spec["Other utility cost"])
    maintenance_cost=fleet_rows[0]["main_c"]
    price_elec=float(spec["Electricity price"])
    price_diesel=float(spec["Diesel price"])
    hours_per_day=float(spec["Average working hours per day"])
    wage_semi=float(spec["Average hourly costs of semi-truck driver"])
    wage_heavy=float(spec["Average hourly costs of heavy-truck driver"])
    revenue=float(spec["Revenue"])
    green_upside=float(spec["green_upside"])

    inst = parse_instance_from_csv(
        nodes_path=nodes_path,
        routes_path=routes_path,
        capacity_weight=cap_weight,
        capacity_volume=cap_volume,
        fleet_size=fleet_size,
        initial_fleet_size=initial_fleet_size,
        max_work_time=max_work_time,
        utility_other=utility_other,
        maintenance_cost=maintenance_cost,
        price_elec=price_elec,
        price_diesel=price_diesel,
        hours_per_day=hours_per_day,
        wage_semi=wage_semi,
        wage_heavy=wage_heavy,
        revenue=revenue,
        green_upside=green_upside
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
        f.write(f"DIMENSION : {len(inst.vertices)}\n\n")

        # ---- fleet block ---------------------------------------------------
        f.write("FLEET_SECTION\n")
        for idx, row in enumerate(fleet_rows, 1):
            f.write(f"{idx} {row['typ']} {row['cnt']} "
                    f"{row['vol']} {row['pay_w']} "
                    f"{row['acq_c']} {row['con_kWh']} "
                    f"{row['con_l']} {row['m_rng']} "
                    f"{row['main_c']} \n")
        f.write("END_FLEET_SECTION\n\n")

        # ---- initial fleet block ---------------------------------------------------
        f.write("INITIAL_FLEET_SECTION\n")
        for idx, row in enumerate(initial_fleet_rows, 1):
            f.write(f"{idx} {row['typ']} {row['cnt']} "
                    f"{row['vol']} {row['pay_w']} "
                    f"{row['acq_c']} {row['con_kWh']} "
                    f"{row['con_l']} {row['m_rng']} "
                    f"{row['main_c']} \n")
        f.write("END_INITIAL_FLEET_SECTION\n\n")

        # ---- city-level info ----------------------------------------------
        f.write("CITY_INFO_SECTION\n")
        for k, v in spec.items():
            if k in ("nodes_path", "routes_path", "fleets", "initial_fleet"):
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
        f.write("END_DEMAND_SECTION\n\n")

        # ---- volumes -------------------------------------------------------
        f.write("\nVOLUME_SECTION\n")
        for v in inst.vertices:
            # convert m³ to milliliters (×1000) for compatibility
            milliliters = int(round(v.demand_volume * 1000))
            f.write(f"{v.vertex_id + 1} {milliliters}\n")
        f.write("END_VOLUME_SECTION\n\n")

        # ---- depot ---------------------------------------------------------
        f.write("\nDEPOT_SECTION\n")
        f.write(f"{inst.depot.vertex_id + 1}\n-1\n")
        f.write("EOF\n\n")

        # ---- service time ---------------------------------------------------------
        f.write("SERVICE_TIME_SECTION\n")
        for v in inst.vertices:  # depot first, then customers
            f.write(f"{v.vertex_id + 1} {v.service_time}\n")
        f.write("END_SERVICE_TIME_SECTION\n\n")

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
