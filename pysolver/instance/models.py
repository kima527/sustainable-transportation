from dataclasses import dataclass
from typing import Iterable, Tuple, Dict
from enum import Enum
from itertools import product
from datetime import timedelta


from pydantic import root_validator, field_validator, model_validator

# VertexID = str
ArcID = Tuple[int, int]


class VertexType(Enum):
    Depot = 'd'
    Customer = 'c'


@dataclass
class Vertex:
    vertex_id: int
    vertex_name: str
    vertex_type: VertexType
    x_coord: float
    y_coord: float
    demand_weight: int
    demand_volume: float
    service_time: float

    @property
    def demand(self) -> int:  # ← legacy alias
        return self.demand_weight

    @property
    def is_customer(self) -> bool:
        return self.vertex_type == VertexType.Customer

    @property
    def is_station(self) -> bool:
        return False

    @property
    def is_depot(self) -> bool:
        return self.vertex_type == VertexType.Depot

    @model_validator(mode='after')
    def check_depot_station_demand(cls, values: dict) -> Dict:
        if values['vertex_type'] in [VertexType.Depot]:
            if values['demand'] != 0.0:
                raise ValueError(
                    "stations or depots cannot have a non-zero demand")
        return values

    @field_validator('demand')
    def check_nonzero_members(cls, value):
        if value < 0:
            raise ValueError(
                '_vertex demand must be at least 0')
        return value


@dataclass
class Arc:
    distance: float
    duration: float

    @field_validator('*')
    def check_nonzero_members(cls, value):
        if value < 0:
            raise ValueError('negative arcs are not allowed')
        return value

    @property
    def cost(self) -> float:
        return self.distance


@dataclass
class Parameters:
    capacity_weight: float
    capacity_volume: float
    fleet_size: int
    max_work_time: float  # seconds
    utility_other: float  # €/d
    maintenance_cost: float  # €/d
    price_elec: float  # €/kWh
    price_diesel: float  # €/l
    hours_per_day: float  # h/d
    wage_semi: float  # €/d
    wage_heavy: float


    @field_validator('*')
    def check_nonzero_members(cls, value):
        if value <= 0.:
            raise ValueError('parameter values must be greater than 0')
        return value


@dataclass
class Instance:
    parameters: Parameters
    vertices: list[Vertex]
    arcs: dict[ArcID, Arc]

    @field_validator('vertices')
    def check_single_depot(cls, vertices: list[Vertex]):
        if sum(1 for x in vertices if x.is_depot) != 1:
            raise ValueError('expected exactly one depot')
        return vertices

    @field_validator('vertices')
    def check_at_least_one_customer(cls, vertices: list[Vertex]):
        if sum(1 for x in vertices if x.is_customer) == 0:
            raise ValueError('expected at least one customer')
        return vertices

    @field_validator('vertices')
    def check_vertex_ids_match(cls, vertices: list[Vertex]):
        for v_id, v in vertices:
            if v_id != v.vertex_id:
                raise ValueError(f'Vertex {v} has id {v.vertex_id} but expected {v_id}')
        return vertices

    @model_validator(mode='after')
    def check_arc_matrix_complete(cls, members):
        arcs = members['arcs']
        vertices = members['vertices']
        for u, v in product(vertices.values(), repeat=2):
            if (u.vertex_id, v.vertex_id) not in arcs:
                raise ValueError("arc ({(u.vertex_id, v.vertex_id)}) is missing")
        if len(arcs) != len(vertices) ** 2:
            raise ValueError('too many arcs: got {len(arcs)} but expected {len(vertices)**2}')

        return members

    @property
    def depot(self) -> Vertex:
        return self.vertices[0]

    @property
    def stations(self) -> Iterable[Vertex]:
        return []

    @property
    def customers(self) -> Iterable[Vertex]:
        return (i for i in self.vertices if i.is_customer)
