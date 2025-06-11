# Copyright (c) 2023 Patrick S. Klein (@libklein)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import annotations
from .models import Vertex, Instance, Arc
from .parsing import parse_instance
from pathlib import Path
from typing import Callable, Any

import routingblocks as rb
import routingblocks_bais_as as rb_ext

def create_cpp_vertex(vertex: Vertex, vertex_id: int, data_factory: Callable[[Vertex], Any]) -> rb_ext.Vertex:
    return rb_ext.create_cvrp_vertex(vertex.vertex_id, vertex.vertex_name, False, vertex_id == 0, data_factory(vertex))


def create_cpp_arc(arc: Arc, data_factory: Callable[[Arc], Any]) -> rb_ext.Arc:
    return rb_ext.create_cvrp_arc(data_factory(arc))


def cvrp_vertex_data_factory(vertex: Vertex) -> rb_ext.CVRPVertexData:
    return rb_ext.CVRPVertexData(vertex.demand)


def cvrp_arc_data_factory(arc: Arc) -> rb_ext.CVRPArcData:
    return rb_ext.CVRPArcData(arc.distance)

def create_cpp_instance(instance: Instance) -> rb_ext.Instance:
    vertex_data_factory = cvrp_vertex_data_factory
    arc_data_factory = cvrp_arc_data_factory

    # Convert vertices
    sorted_vertices = [instance.depot, *sorted(instance.customers, key=lambda v: v.vertex_id), *[]]

    # 🚨 Correct — do NOT reload id_map.txt here!
    # Build name_to_vertex_id from instance.vertices
    name_to_vertex_id = {v.vertex_name: v.vertex_id for v in instance.vertices}

    cpp_vertices = [create_cpp_vertex(v, i, data_factory=vertex_data_factory) for i, v in enumerate(sorted_vertices)]

    for v in sorted_vertices:
        print(f"vertex_name = {v.vertex_name}, vertex_id = {v.vertex_id}")

    cpp_arcs = [
        [create_cpp_arc(instance.arcs[name_to_vertex_id[i.vertex_name], name_to_vertex_id[j.vertex_name]],
                        data_factory=arc_data_factory)
         for j in sorted_vertices] for i in sorted_vertices]

    return rb.Instance(cpp_vertices, cpp_arcs, instance.parameters.fleet_size)

