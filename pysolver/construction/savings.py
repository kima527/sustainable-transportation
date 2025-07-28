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

    MAX_ATTEMPTS = 30000
    attempt_count = 0
    successful_merges = 0

    for s_ij, c_i, c_j in savings:
        if s_ij <= 0:
            break

        attempt_count += 1
        if attempt_count > MAX_ATTEMPTS:
            print("[INFO] Too many merge attempts. Stopping early.")
            break

        #if attempt_count % 500 == 0:
            #print(f"[INFO] Merge attempt {attempt_count} | Successes: {successful_merges}")

        ri = c_to_route_id[c_i]
        rj = c_to_route_id[c_j]
        if ri == rj:
            continue

        # Skip if either route has already been merged (marked None)
        if routes[ri] is None or routes[rj] is None:
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

        # Build a new route manually
        new_route = rb.Route(evaluation, cpp_instance)

        for i in range(1, len(r_i) - 1):
            new_route.insert_vertices_after([(r_i[i].vertex_id, 0)])
        for j in range(1, len(r_j) - 1):
            new_route.insert_vertices_after([(r_j[j].vertex_id, 0)])

        #print(f" → Trying to merge customers {c_i} and {c_j}")
        #print("New route node vertex_ids:", [n.vertex_id for n in new_route])
        #print("Full route nodes with indices:")
        #for idx, node in enumerate(new_route):
            #print(f"  [{idx}] vertex_id={node.vertex_id}")

        MAX_CUSTOMERS_PER_ROUTE = 8  # adjust based on city/dataset

        # Count customers (excluding depots at both ends)
        customer_count = len(new_route) - 2
        if customer_count > MAX_CUSTOMERS_PER_ROUTE:
            #print(
                #f"[INFO] Merge skipped: route would have {customer_count} customers (limit = {MAX_CUSTOMERS_PER_ROUTE})")
            continue

        # Estimate total distance from arc costs
        try:
            arc_1 = py_instance.arcs[(0, c_i)].cost
            arc_2 = py_instance.arcs[(c_i, c_j)].cost
            arc_3 = py_instance.arcs[(c_j, 0)].cost
            total_dist = arc_1 + arc_2 + arc_3
            #print(f" → Arc costs: depot→{c_i}={arc_1}, {c_i}→{c_j}={arc_2}, {c_j}→depot={arc_3}")
        except Exception as e:
            print(f"[ERROR] Missing arc cost for ({c_i}, {c_j}): {e}")
            continue

        # Estimate work time: travel + service (approximation)
        average_speed_kph = 50
        service_time_min = 5

        average_speed_mps = average_speed_kph * 1000 / 3600
        travel_time_sec = (total_dist * 1000) / average_speed_mps
        work_time = travel_time_sec + 2 * service_time_min * 60

        #print(f" → Estimated distance: {total_dist:.2f} km, work time: {work_time:.0f} sec")

        # Choose vehicle and check feasibility
        try:
            vid = evaluation.choose_vehicle(total_dist, total_dist, new_w, new_v, work_time)
            #print(f" → Vehicle {vid} can serve this route.")
        except Exception as e:
            print(f"[ERROR] Vehicle selection failed: {e}")
            continue

        if (new_w > evaluation.cap_w[vid]
                or new_v > evaluation.cap_v[vid]
                or work_time > evaluation.hours_per_day * 3600):
            #print("[INFO] Merge infeasible due to vehicle limits.")
            #print(f" → cap_w[{vid}]={evaluation.cap_w[vid]}, demand={new_w}")
            #print(f" → cap_v[{vid}]={evaluation.cap_v[vid]}, demand={new_v}")
            #print(f" → work_time={work_time:.0f} sec, limit={evaluation.hours_per_day * 3600:.0f} sec")
            continue

        # Merge accepted — replace r_i with new route, mark r_j for removal
        routes[ri] = new_route
        routes[rj] = None
        capacity_w[ri] = new_w
        capacity_v[ri] = new_v
        capacity_w[rj] = 0
        capacity_v[rj] = 0
        c_to_route_id[c_i] = ri
        c_to_route_id[c_j] = ri

        successful_merges += 1

        # After merge loop, clean up solution
    routes = [r for r in routes if r is not None]
    solution = rb.Solution(evaluation, cpp_instance, len(py_instance.vertices) - 1)
    for route in routes:
        solution.add_route(route)

    return solution
