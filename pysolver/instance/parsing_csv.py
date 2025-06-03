import csv
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime, timedelta

from .models import Vertex, VertexType, Arc, Instance, Parameters


def parse_nodes_file(path: Path) -> list[Vertex]:
    vertices = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f, delimiter=' ')
        for i, row in enumerate(reader):
            name = row['Id'].strip()
            lon = float(row['Lon'])
            lat = float(row['Lat'])
            demand = int(row['Demand[kg]'])

            vertex_type = VertexType.Depot if name.startswith("D") else VertexType.Customer

            vertices.append(Vertex(
                vertex_id=i,
                vertex_name=name,
                vertex_type=vertex_type,
                x_coord=lon,
                y_coord=lat,
                demand=demand
            ))

    return vertices

# def parse_duration(s: str) -> timedelta:
#     return datetime.strptime(s.strip(), "%H:%M:%S") - datetime(1900, 1, 1)


def parse_routes_file(path: Path, vertices: list[Vertex]) -> Dict[Tuple[int, int], Arc]:
    arcs = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f, delimiter=' ')
        for row in reader:
            from_name = row['From'].strip()
            to_name = row['To'].strip()

            # Convert "D0" -> 0, "C1" -> 1, "C12" -> 12, etc.
            def name_to_id(name: str) -> int:
                if name.startswith("D") or name.startswith("C"):
                    return int(name[1:])
                else:
                    raise ValueError(f"Unknown vertex name format: {name}")

            from_id = name_to_id(from_name)
            to_id = name_to_id(to_name)
            distance = float(row['DistanceTotal[km]'])

            arcs[(from_id, to_id)] = Arc(distance=distance)

    # Ensure all self-loops exist with 0-cost if missing
    for v in vertices:
        key = (v.vertex_id, v.vertex_id)
        if key not in arcs:
            arcs[key] = Arc(distance=0.0)

    return arcs


def parse_instance_from_csv(nodes_path: Path, routes_path: Path, capacity: float, fleet_size: int) -> Instance:
    vertices = parse_nodes_file(nodes_path)
    arcs = parse_routes_file(routes_path, vertices)

    # hard-coded parameters for now
    parameters = Parameters(capacity=2800, fleet_size=19)

    return Instance(parameters=parameters, vertices=vertices, arcs=arcs)


def save_instance_as_vrp(instance, output_path: Path = "resources/instances/test_instances/newyork_manhattan.vrp", name: str = "PARIS", comment: str = ""):
    with open(output_path, "w") as f:
        f.write(f"NAME : {name}\n")
        f.write("TYPE : CVRP\n")
        f.write(f"COMMENT : {comment}\n")
        f.write(f"DIMENSION : {len(instance.vertices)}\n")
        f.write("EDGE_WEIGHT_TYPE : EUC_2D\n")
        f.write(f"CAPACITY : {int(instance.parameters.capacity)}\n\n")

        # Node coordinates section
        f.write("NODE_COORD_SECTION\n")
        for v in instance.vertices:
            f.write(f"{v.vertex_id + 1} {v.x_coord:.6f} {v.y_coord:.6f}\n")

        # Demands section
        f.write("\nDEMAND_SECTION\n")
        for v in instance.vertices:
            f.write(f"{v.vertex_id + 1} {int(v.demand)}\n")

        # Depot section
        f.write("\nDEPOT_SECTION\n")
        f.write(f"{instance.depot.vertex_id + 1}\n")
        f.write("-1\n")
        f.write("EOF\n")
