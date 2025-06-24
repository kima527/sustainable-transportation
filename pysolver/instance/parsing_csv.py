import csv
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime, timedelta
from .models import Vertex, Arc, ArcID


import pandas as pd

from .models import Vertex, VertexType, Arc, Instance, Parameters

def _hhmmss_to_seconds(hhmmss: str) -> int:
    h, m, s = map(int, hhmmss.strip().split(":"))
    return h * 3600 + m * 60 + s

def parse_nodes_file(path: Path) -> list[Vertex]:
    vertices = []

    # 🚨 Force Id column to string so 'D0', 'C1', ... are preserved!
    nodes_df = pd.read_csv(
        path,
        sep=r'\s+',
        header=0,
        dtype={"Id": str}
    )

    for i, row in nodes_df.iterrows():
        name = row['Id'].strip()
        lon = float(row['Lon'])
        lat = float(row['Lat'])
        weight = int(row['Demand[kg]'])
        volume = float(row['Demand[m^3*10^-3]'])

        vertex_type = VertexType.Depot if name.startswith("D") else VertexType.Customer

        vertices.append(Vertex(
            vertex_id=i,
            vertex_name=name,
            vertex_type=vertex_type,
            x_coord=lon,
            y_coord=lat,
            demand_weight=weight,
            demand_volume=volume,
            service_time=15.0
        ))

    return vertices

# def parse_duration(s: str) -> timedelta:
#     return datetime.strptime(s.strip(), "%H:%M:%S") - datetime(1900, 1, 1)


def parse_routes_file(path: Path,
                      vertices: list[Vertex]) -> Dict[ArcID, Arc]:
    """Read *.routes* and build the full (i,j)->Arc dictionary."""
    df = pd.read_csv(path, sep=r"\s+", header=0,
                     dtype={"From": str, "To": str})

    # name  -> vertex_id
    name2id = {v.vertex_name.strip(): v.vertex_id for v in vertices}
    arcs: Dict[ArcID, Arc] = {}

    for _, row in df.iterrows():
        from_name = row["From"].strip()
        to_name   = row["To"].strip()

        if from_name not in name2id or to_name not in name2id:
            print(f"⚠️  Skipping arc {from_name}->{to_name} "
                  f"(name not found in .nodes)")
            continue

        i = name2id[from_name]
        j = name2id[to_name]

        # -------- distance (km) -------------------------------
        dist_km = float(row["DistanceTotal[km]"])

        # -------- travel-time (sec) ---------------------------
        dur_raw = row["Duration[s]"]
        if pd.isna(dur_raw):
            dur_sec = 0.0
        elif isinstance(dur_raw, str) and ":" in dur_raw:
            dur_sec = _hhmmss_to_seconds(dur_raw)
        else:
            dur_sec = float(dur_raw)          # already seconds

        arcs[(i, j)] = Arc(distance=dist_km,
                           duration=dur_sec)   #  ← stored!

    # ---------- fill missing (i,i) and ∞-arcs -----------------
    ids = [v.vertex_id for v in vertices]
    for u in ids:
        for v in ids:
            if (u, v) not in arcs:
                arcs[(u, v)] = Arc(
                    distance=0.0 if u == v else float("inf"),
                    duration=0.0 if u == v else float("inf")
                )

    return arcs

def parse_instance_from_csv(nodes_path: Path, routes_path: Path, capacity_weight: float, capacity_volume: float, fleet_size: int) -> Instance:
    if capacity_weight is None or capacity_volume is None or fleet_size is None:
        raise ValueError("Capacity (weight & volume) and fleet_size must be provided")

    vertices = parse_nodes_file(nodes_path)
    arcs = parse_routes_file(routes_path, vertices)

    parameters = Parameters(capacity_weight=capacity_weight, capacity_volume=capacity_volume, fleet_size=fleet_size)


    return Instance(parameters=parameters, vertices=vertices, arcs=arcs)

