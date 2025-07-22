from routingblocks._routingblocks import Route
from routingblocks_bais_as._routingblocks_bais_as import HFVRPEvaluation
from pysolver.instance.models import Instance
import routingblocks as rb


def savings(py_instance: Instance, evaluation: HFVRPEvaluation,
            cpp_instance: rb.Instance) -> rb.Solution:
    solution = rb.Solution(evaluation, cpp_instance, len(py_instance.vertices) - 1)
    routes: [rb.Route] = [r for r in solution.routes]

    capacity_w: list[float] = []  # kg
    capacity_v: list[float] = []  # m³

    c_to_route_id = [-1]
    for c_i in range(1, len(py_instance.vertices)):
        c_to_route_id.append(c_i - 1)
        routes[c_i - 1].insert_vertices_after([(c_i, 0)])
        capacity_w.append(py_instance.vertices[c_i].demand_weight)
        capacity_v.append(py_instance.vertices[c_i].demand_volume)

    savings = list()
    for c_i in range(1, len(py_instance.vertices)):
        for c_j in range(1, len(py_instance.vertices)):
            if c_i == c_j:
                pass
            else:
                s_ij = py_instance.arcs[(c_i, 0)].cost + py_instance.arcs[(0, c_j)].cost - py_instance.arcs[
                    (c_i, c_j)].cost
                s_ij = round(s_ij, 6)
                savings.append((s_ij, c_i, c_j))
    savings.sort(key=lambda x: (-x[0], x[1], x[2]))

    for s_ij, c_i, c_j in savings:
        if s_ij <= 0:
            break

        ri = c_to_route_id[c_i]
        rj = c_to_route_id[c_j]
        if ri == rj:
            continue

        r_i, r_j = routes[ri], routes[rj]
        len_i = len(r_i)
        len_j = len(r_j)

        if (ri != rj and
                len_i > 2 and len_j > 2 and
                r_i[len_i - 2].vertex_id == c_i and  # <- change here
                r_j[1].vertex_id == c_j):
            pass

        # --- prospective merged load ----------------------------------
        new_w = capacity_w[ri] + capacity_w[rj]
        new_v = capacity_v[ri] + capacity_v[rj]

        # choose the cheapest vehicle _after_ merge
        vid = evaluation.choose_vehicle(0.0, new_w, new_v, 0.0)  # matter for capacity test

        if (new_w > evaluation.cap_w[vid] or
                new_v > evaluation.cap_v[vid]):
            continue  # infeasible with *any* vehicle → skip

        # ---- perform merge -------------------------------------------


        r_i.exchange_segments(len(r_i) - 1, len(r_i) - 1,
                              1, len(r_j) - 1, r_j)
        c_to_route_id[r_i[len_i - 2] .vertex_id] = ri

        capacity_w[ri] = new_w
        capacity_v[ri] = new_v
        capacity_w[rj] = capacity_v[rj] = 0

    i = 0
    while i < len(solution):
        # a route with only the two depot nodes is useless → drop it
        if len(solution[i]) <= 2:  # 2 = start-depot + end-depot
            solution.remove_route(solution[i])
        else:
            i += 1

    return solution
