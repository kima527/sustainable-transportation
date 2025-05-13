from itertools import product
from math import sqrt
from pathlib import Path
from typing import Callable

from pysolver.instance.models import Vertex, Parameters, ArcID, Arc, Instance, VertexType


def create_arc_matrix(parameters: Parameters, vertices: list[Vertex],
                      distance_fn: Callable[[Vertex, Vertex], float]) -> dict[ArcID, Arc]:
    def _create_arc(u: Vertex, v: Vertex) -> Arc:
        distance = distance_fn(u, v)
        return Arc(distance=distance)

    return {
        (u.vertex_id, v.vertex_id): _create_arc(u, v) for u, v in product(vertices, repeat=2)
    }


def euclidean(u: Vertex, v: Vertex) -> float:
    return sqrt((u.x_coord - v.x_coord) ** 2 + (u.y_coord - v.y_coord) ** 2)


def parse_instance(instance_path: Path) -> Instance:
    vertices: list[Vertex] = []
    with open(instance_path) as instance_stream:
        lines = instance_stream.read().splitlines()
        # DIMENSION: 32
        n = int(lines[3].rsplit(":")[1])
        # CAPACITY: 100
        capacity = int(lines[5].rsplit(":")[1])
        # coordinates start at 7
        # demands at n + 8

        for k in range(0, n):
            (name, x, y) = list(map(int, lines[k + 7].split()))
            demand = int(lines[k + n + 8].split()[1])

            vertex = Vertex(
                vertex_id=k,
                vertex_name=str(k),
                vertex_type=VertexType.Depot if k == 0 else VertexType.Customer,
                x_coord=x,
                y_coord=y,
                demand=demand,
            )

            # vertices[vertex.vertex_id] = vertex
            vertices.append(vertex)

        # parameters = Parameters(capacity=capacity, fleet_size=sum(1 for x in vertices.values() if x.is_customer))
        parameters = Parameters(capacity=capacity, fleet_size=sum(1 for x in vertices if x.is_customer))

        # Create Arcs
        arcs = create_arc_matrix(parameters=parameters, vertices=vertices,
                                 distance_fn=euclidean)

        return Instance(parameters=parameters, vertices=vertices, arcs=arcs)
