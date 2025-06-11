from itertools import product
from math import sqrt
from pathlib import Path
from typing import Callable
from .parsing_csv import parse_routes_file

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


def parse_instance(instance_path: Path) -> Instance:
    with open(instance_path) as f:
        lines = [line.strip() for line in f if line.strip()]

    # === Header values ===
    dimension = int(next(l for l in lines if l.startswith("DIMENSION")).split(":")[1])
    capacity = int(next(l for l in lines if l.startswith("CAPACITY")).split(":")[1])

    # === Section indices ===
    coord_start = lines.index("NODE_COORD_SECTION") + 1
    demand_start = lines.index("DEMAND_SECTION")
    depot_start = lines.index("DEPOT_SECTION")

    # === Load id_map.txt ===
    id_map_path = instance_path.parent / f"{instance_path.stem}.id_map.txt"
    id_map = load_id_map(id_map_path)

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

        # 🚨 FIX: use id_map to get correct vertex_name
        vertex_name = id_map[int(tokens[0])]

        vertices.append(Vertex(
            vertex_id=vertex_id,
            vertex_name=vertex_name,
            vertex_type=vertex_type,
            x_coord=x,
            y_coord=y,
            demand=0  # Will be filled next
        ))

    # === 2. Parse Demands ===
    demand_lines = lines[demand_start + 1:depot_start]
    for line in demand_lines:
        tokens = line.split()
        vertex_id = int(tokens[0]) - 1
        demand = int(tokens[1])
        vertices[vertex_id].demand = demand

    # === 3. Parameters ===
    parameters = Parameters(capacity=capacity, fleet_size=sum(1 for v in vertices if v.is_customer))

    # === 4. Arcs ===
    ROUTES_DIR = Path("resources/data")
    inferred_routes = ROUTES_DIR / f"{instance_path.stem}.routes"
    arcs = parse_routes_file(inferred_routes, vertices)

    return Instance(parameters=parameters, vertices=vertices, arcs=arcs)

