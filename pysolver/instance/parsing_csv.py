import csv
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime, timedelta
from .models import Vertex, Arc, ArcID


import pandas as pd

from .models import Vertex, VertexType, Arc, Instance, Parameters


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
            demand_volume=volume
        ))

    return vertices

# def parse_duration(s: str) -> timedelta:
#     return datetime.strptime(s.strip(), "%H:%M:%S") - datetime(1900, 1, 1)


def parse_routes_file(path: Path, vertices: list[Vertex]) -> dict[ArcID, Arc]:
    import pandas as pd

    # Read .routes file with flexible whitespace separator
    df = pd.read_csv(path, sep=r'\s+', header=0, dtype={"From": str, "To": str})

    # Build name → vertex_id map
    name_to_vertex_id = {v.vertex_name.strip(): v.vertex_id for v in vertices}

    arcs = {}

    for _, row in df.iterrows():
        from_name = row['From'].strip()
        to_name = row['To'].strip()

        if from_name not in name_to_vertex_id:
            print(f"WARNING: Skipping arc ({from_name} → {to_name}) — From not found in .nodes")
            continue

        if to_name not in name_to_vertex_id:
            print(f"WARNING: Skipping arc ({from_name} → {to_name}) — To not found in .nodes")
            continue

        from_id = name_to_vertex_id[from_name]
        to_id = name_to_vertex_id[to_name]

        distance = float(row['DistanceTotal[km]'])

        arcs[(from_id, to_id)] = Arc(distance=distance)

    # Add self-loops with 0.0 distance if missing
    all_ids = [v.vertex_id for v in vertices]

    for i in all_ids:
        if (i, i) not in arcs:
            arcs[(i, i)] = Arc(distance=0.0)

    # 🚨 Add INF arcs for all missing (i,j)
    for i in all_ids:
        for j in all_ids:
            if (i, j) not in arcs:
                arcs[(i, j)] = Arc(distance=float('inf'))

    return arcs


def parse_instance_from_csv(nodes_path: Path, routes_path: Path, capacity_weight: float, capacity_volume: float, fleet_size: int) -> Instance:
    if capacity_weight is None or capacity_volume is None or fleet_size is None:
        raise ValueError("Capacity (weight & volume) and fleet_size must be provided")

    vertices = parse_nodes_file(nodes_path)
    arcs = parse_routes_file(routes_path, vertices)

    parameters = Parameters(capacity_weight=capacity_weight, capacity_volume=capacity_volume, fleet_size=fleet_size)
    return Instance(parameters=parameters, vertices=vertices, arcs=arcs)

