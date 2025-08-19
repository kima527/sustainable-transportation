from routingblocks._routingblocks import Route
from routingblocks_bais_as._routingblocks_bais_as import HFVRPEvaluation
from pysolver.instance.models import Instance
import routingblocks as rb

def savings(py_instance: Instance,
            evaluation: HFVRPEvaluation,
            cpp_instance: rb.Instance,
            max_customers_per_route: int = 8,
            min_saving: float = 0.0) -> rb.Solution:

    # --- Build independent 1-customer routes (NOT from solution.routes) ---
    routes: list[rb.Route] = []
    capacity_w: list[float] = []
    capacity_v: list[float] = []
    c_to_route_id = [-1]  # 0th unused to match vertex ids

    for c_i in range(1, len(py_instance.vertices)):
        r = rb.Route(evaluation, cpp_instance)   # standalone route (has depots)
        # assert len(r) == 2 and r[0].vertex_id == 0 and r[-1].vertex_id == 0
        r.insert_vertices_after([(c_i, 0)])
        routes.append(r)
        c_to_route_id.append(len(routes) - 1)
        capacity_w.append(py_instance.vertices[c_i].demand_weight)
        capacity_v.append(py_instance.vertices[c_i].demand_volume)

    # --- Compute savings (with a tiny threshold) ---
    savings = []
    for c_i in range(1, len(py_instance.vertices)):
        for c_j in range(1, len(py_instance.vertices)):
            if c_i == c_j:
                continue
            s_ij = (py_instance.arcs[(c_i, 0)].cost
                    + py_instance.arcs[(0, c_j)].cost
                    - py_instance.arcs[(c_i, c_j)].cost)
            if s_ij <= min_saving:
                continue
            savings.append((round(s_ij, 6), c_i, c_j))
    savings.sort(key=lambda x: (-x[0], x[1], x[2]))

    MAX_ATTEMPTS = 30000
    attempt_count = 0

    # --- Greedy merges on our standalone routes ---
    for s_ij, c_i, c_j in savings:
        if s_ij <= 0:
            break
        attempt_count += 1
        if attempt_count > MAX_ATTEMPTS:
            break

        ri = c_to_route_id[c_i]
        rj = c_to_route_id[c_j]
        if ri == rj:
            continue
        if ri < 0 or rj < 0:
            continue
        if routes[ri] is None or routes[rj] is None:
            continue

        r_i, r_j = routes[ri], routes[rj]
        len_i = len(r_i)
        len_j = len(r_j)

        # Only tail(i) -> head(j)
        if not (len_i > 2 and len_j > 2 and
                r_i[len_i - 2].vertex_id == c_i and
                r_j[1].vertex_id == c_j):
            continue

        # Prospective merged load
        new_w = capacity_w[ri] + capacity_w[rj]
        new_v = capacity_v[ri] + capacity_v[rj]

        # Structural limit before constructing anything
        customer_count_after = (len_i - 2) + (len_j - 2)
        if customer_count_after > max_customers_per_route:
            continue

        # Distance/time estimate
        try:
            arc_1 = py_instance.arcs[(0, c_i)].cost
            arc_2 = py_instance.arcs[(c_i, c_j)].cost
            arc_3 = py_instance.arcs[(c_j, 0)].cost
            total_dist = arc_1 + arc_2 + arc_3
        except Exception:
            continue

        average_speed_kph = 50.0
        service_time_min = 5.0
        average_speed_mps = average_speed_kph * 1000 / 3600
        travel_time_sec = (total_dist * 1000) / average_speed_mps
        work_time = travel_time_sec + 2 * service_time_min * 60

        # Vehicle feasibility
        try:
            vid = evaluation.choose_vehicle(total_dist, total_dist, new_w, new_v, work_time)
        except Exception:
            continue

        if (new_w > evaluation.cap_w[vid]
                or new_v > evaluation.cap_v[vid]
                or work_time > evaluation.hours_per_day * 3600):
            continue

        # --------- SAFE MERGE: build a fresh merged route (no duplicates) ---------
        merged = rb.Route(evaluation, cpp_instance)
        # assert len(merged) == 2 and merged[0].vertex_id == 0 and merged[-1].vertex_id == 0

        # r_i middle customers
        for i_pos in range(1, len_i - 1):
            merged.insert_vertices_after([(r_i[i_pos].vertex_id, 0)])
        # r_j middle customers
        for j_pos in range(1, len_j - 1):
            merged.insert_vertices_after([(r_j[j_pos].vertex_id, 0)])

        # Replace r_i with merged; retire r_j
        routes[ri] = merged
        routes[rj] = None

        # Update loads
        capacity_w[ri] = new_w
        capacity_v[ri] = new_v
        capacity_w[rj] = 0.0
        capacity_v[rj] = 0.0

        # Remap all customers that were in r_j to ri
        for j_pos in range(1, len_j - 1):
            c_to_route_id[r_j[j_pos].vertex_id] = ri
        # --------------------------------------------------------------------------

    # --- Assemble final solution from remaining routes ---
    final_routes = [r for r in routes if r is not None]
    solution = rb.Solution(evaluation, cpp_instance, len(py_instance.vertices) - 1)
    for route in final_routes:
        solution.add_route(route)
    return solution
