import re
from itertools import product
from math import sqrt
from pathlib import Path
from typing import Callable
from .parsing_csv import parse_routes_file, parse_nodes_file

from .models import Vertex, Parameters, ArcID, Arc, Instance, VertexType


def create_arc_matrix(parameters: Parameters, vertices: list[Vertex],
                      distance_fn: Callable[[Vertex, Vertex], float]) -> dict[ArcID, Arc]:
    def _create_arc(u: Vertex, v: Vertex) -> Arc:
        distance = distance_fn(u, v)
        return Arc(distance=distance)

    return {
        (u.vertex_id, v.vertex_id): _create_arc(u, v) for u, v in product(vertices, repeat=2)
    }


# def euclidean(u: Vertex, v: Vertex) -> float:
#     return sqrt((u.x_coord - v.x_coord) ** 2 + (u.y_coord - v.y_coord) ** 2)

def load_id_map(id_map_path: Path) -> dict[int, str]:
    with open(id_map_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    result = {}
    for line in lines:
        tokens = line.split()
        result[int(tokens[0])] = tokens[1]
    return result


def parse_instance(instance_path: Path, *, return_fleets: bool = False) -> Instance:
    with open(instance_path) as f:
        lines = [line.strip() for line in f if line.strip()]

        # ---------- CITY_INFO_SECTION (optional) --------------------
        try:
            ci_s = lines.index("CITY_INFO_SECTION") + 1
            ci_e = lines.index("END_CITY_INFO_SECTION")
            city = _parse_city_info(lines[ci_s:ci_e])
        except ValueError:
            city = {}  # file has no city block

        # ---------- FLEET_SECTION (required) ------------------------
        try:
            fs_start = lines.index("FLEET_SECTION") + 1
            fs_end = lines.index("END_FLEET_SECTION")
        except ValueError:
            raise ValueError(f"{instance_path.name} is missing a FLEET_SECTION")

    fleets: list[tuple[str, float, float, float, float,
    float, float, float]] = []

    for ln in lines[fs_start:fs_end]:
        # idx typ cnt vol pay_w acq_k€ cons_kWh cons_l max_rng maint_c
        (_, typ, cnt, vol, pay_w, acq, kwh, ltr, rng, maint) = ln.split()
        typ = typ.strip()
        cnt = int(cnt)

        for _ in range(cnt):
            fleets.append((typ,  float(vol), float(pay_w), float(acq),
                            float(kwh), float(ltr), float(rng),
                        float(maint)))

    fleet_sz = sum(int(ln.split()[2]) for ln in lines[fs_start:fs_end])


    # ---------- INITIAL_FLEET_SECTION (optional) ------------------------
    try:
        fs_start = lines.index("INITIAL_FLEET_SECTION") + 1
        fs_end = lines.index("END_INITIAL_FLEET_SECTION")
    except ValueError:
        raise ValueError(f"{instance_path.name} is missing a INITIAL_FLEET_SECTION")

    initial_fleets: list[tuple[str, float, float, float, float,
    float, float, float]] = []

    for ln in lines[fs_start:fs_end]:
        # idx typ cnt vol pay_w acq_k€ cons_kWh cons_l max_rng maint_c
        (_, typ, cnt, vol, pay_w, acq, kwh, ltr, rng, maint) = ln.split()
        typ = typ.strip()
        cnt = int(cnt)

        for _ in range(cnt):
            initial_fleets.append((typ,  float(vol), float(pay_w), float(acq),
                        float(kwh), float(ltr), float(rng),
                       float(maint)))

    # use the **first** vehicle type as legacy capacity defaults
    cap_w = fleets[0][1]
    cap_v = fleets[0][2]
    initial_fleet_sz = sum(int(ln.split()[2]) for ln in lines[fs_start:fs_end])

    # === Section indices ===
    coord_start = lines.index("NODE_COORD_SECTION") + 1
    demand_start = lines.index("DEMAND_SECTION")
    depmand_end = lines.index("END_DEMAND_SECTION")


    # === Load id_map.txt ===
    id_map_path = instance_path.parent / f"{instance_path.stem}.id_map.txt"
    if id_map_path.exists():
        id_map = load_id_map(id_map_path)
    else:
        id_map = {}

    # === 1. Parse Coordinates ===
    coord_lines = lines[coord_start:demand_start]
    vertices = []
    for line in coord_lines:
        tokens = line.split()
        if len(tokens) < 3:
            raise ValueError(f"Expected 3 columns (id, x, y), got: {line}")
        vertex_id = int(tokens[0]) - 1  # convert 1-based to 0-based
        x = float(tokens[1])
        y = float(tokens[2])
        vertex_type = VertexType.Depot if vertex_id == 0 else VertexType.Customer

        vertex_name = id_map.get(int(tokens[0]), tokens[0]).strip()


        vertices.append(Vertex(
            vertex_id=vertex_id,
            vertex_name=vertex_name,
            vertex_type=vertex_type,
            x_coord=x,
            y_coord=y,
            demand_weight=0,  # to be filled below
            demand_volume=0.0,
            service_time=15*60 #second
        ))

    # === 2. Parse Demands ===
    for ln in lines[demand_start + 1: depmand_end]:
        tokens = ln.strip().split()
        if len(tokens) < 2:
            continue
        idx, w = tokens[:2]
        vid = int(idx) - 1
        vertices[vid].demand_weight = int(w)

    # === 2b. Parse Volume (if exists)
    try:
        volume_start = lines.index("VOLUME_SECTION") + 1
        volume_end = lines.index("END_VOLUME_SECTION")
        for ln in lines[volume_start:volume_end]:
            tokens = ln.strip().split()
            if len(tokens) < 2:
                continue
            idx, vol = tokens[:2]
            vid = int(idx) - 1
            # assuming volume is in dm³ → convert to m³
            vertices[vid].demand_volume = float(vol) / 1000.0
    except ValueError:
        # fallback estimate if volume is missing
        for v in vertices:
            v.demand_volume = v.demand_weight / 1000.0

    avg_work_h = city.get("hours_per_day", 8.0)
    max_work_sec = 3600.0 * avg_work_h

    if "SERVICE_TIME_SECTION" in lines:
        st_s = lines.index("SERVICE_TIME_SECTION") + 1
        st_e = lines.index("END_SERVICE_TIME_SECTION")
        for ln in lines[st_s:st_e]:
            vid, sec = ln.split()
            vertices[int(vid) - 1].service_time = float(sec)
    else:
        for v in vertices[1:]:
            v.service_time = 900

    # === 3. Parameters ===
    parameters = Parameters(
        capacity_weight=cap_w,
        capacity_volume=cap_v,
        fleet_size=fleet_sz,
        initial_fleet_size=initial_fleet_sz,
        max_work_time=max_work_sec,
        **city
    )

    # === 4. Arcs ===
    ROUTES_DIR = Path("resources/data")
    inferred_routes = ROUTES_DIR / f"{instance_path.stem}.routes"
    arcs = parse_routes_file(inferred_routes, vertices)

    inst = Instance(parameters=parameters, vertices=vertices, arcs=arcs)

    if return_fleets:  # ← only when the caller asks for it
        return inst, fleets, initial_fleets  # (Instance, list[tuple[acq, cap_w, cap_v, rng]], list[tuple[acq, cap_w, cap_v, rng]])
    return inst


def _to_float(x, default):
    return float(str(x).replace(",", ".")) if x is not None else float(default)

def _floats(line: str) -> list[float]:
    return list(map(float, line.split()))

# ───────────────────────────────────────────────── CITY INFO ─────
def _parse_city_info(raw_lines: list[str]) -> dict[str, float]:
    """
    Turns the seven lines inside CITY_INFO_SECTION into a flat dict
    that can be unpacked with ** into Parameters().
    """
    key_map = {
        "other utility cost":        "utility_other",
        "maintenance costs":         "maintenance_cost",
        "electricity price":         "price_elec",
        "diesel price":              "price_diesel",
        "average working hours":     "hours_per_day",
        "semi-truck driver":         "wage_semi",
        "heavy-truck driver":        "wage_heavy",
        "revenue":                   "revenue",
        "green upside":              "green_upside",
    }

    out: dict[str, float] = {}
    for ln in raw_lines:
        if ":" not in ln:
            continue
        left, right = ln.split(":", 1)
        left_lc = left.lower()
        # keep only digits, dot, minus, comma
        num = float(re.sub(r"[^\d\.\-]+", "", right).replace(",", ".") or "0")
        for needle, target in key_map.items():
            if needle in left_lc:
                out[target] = num
                break

    # guarantee that every expected key exists
    for target in key_map.values():
        out.setdefault(target, 0.0)

    return out
