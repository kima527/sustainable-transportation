from routingblocks._routingblocks import Route

from pysolver.instance.models import Instance
import routingblocks as rb


def savings(py_instance: Instance, evaluation: rb.Evaluation,
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
                # s_ij = c_i0 + c_0j - c_ij
                # s_ij = instance.d[(c_i, 0)] + instance.d[(0, c_j)] - instance.d[(c_i, c_j)]
                s_ij = py_instance.arcs[(c_i, 0)].cost + py_instance.arcs[(0, c_j)].cost - py_instance.arcs[
                    (c_i, c_j)].cost
                savings.append((s_ij, c_i, c_j))
    savings.sort(reverse=True)

    for s_ij, c_i, c_j in savings:
        if s_ij <= 0:
            break

        route_id_of_c_i = c_to_route_id[c_i]
        route_id_of_c_j = c_to_route_id[c_j]

        r_i = routes[route_id_of_c_i]
        r_j = routes[route_id_of_c_j]

        if route_id_of_c_i != route_id_of_c_j and len(r_i) > 2 and len(r_j) > 2 \
                and r_i[len(r_i) - 2].vertex_id == c_i and r_j[1].vertex_id == c_j:
            if (capacity_w[route_id_of_c_i] + capacity_w[route_id_of_c_j] >
                    py_instance.parameters.capacity_weight or
                    capacity_v[route_id_of_c_i] + capacity_v[route_id_of_c_j] >
                    py_instance.parameters.capacity_volume):
                pass
            else:
                # merge
                # r_i [..,4,5]
                # r_j [8,9,..]
                # merge [..,4,5,8,9,..,121]

                r_i.exchange_segments(len(r_i) - 1, len(r_i) - 1, 1, len(r_j) - 1, r_j)
                c_to_route_id[r_i[len(r_i) - 2].vertex_id] = route_id_of_c_i

                capacity_w[route_id_of_c_i] += capacity_w[route_id_of_c_j]
                capacity_v[route_id_of_c_i] += capacity_v[route_id_of_c_j]
                capacity_w[route_id_of_c_j] = capacity_v[route_id_of_c_j] = 0

    i = 0
    while i < len(solution):
        if solution[i].empty:
            solution.remove_route(solution[i])
        else:
            i = i + 1

    return solution


def py_savings(py_instance: Instance, evaluation: rb.Evaluation,
               cpp_instance: rb.Instance) -> rb.Solution:
    """
    Performs the parallel version of the Clark & Wright Savings Heuristic (Clark & Wright, 1964) to construct a
    solution. First, the savings value  is calculated for all pair of customers (s_ij = c_i0 + c_0j - c_ij).
    Then the solution is initialized by creating a route for each customer, going from
    the depot to the customer and immediately back to the depot.
    Starting with the largest savings s_ij, we test whether the route r_i ending with node i and r_j beginning with
    node j can be merged, and if possible, they are indeed merged. Then we continue with the largest savings value
    until no more merges are possible.

    :param py_instance: corresponding instance
    :param evaluation: routingblocks.Evaluation
    :param cpp_instance: routingblocks.Instance
    :return: rb.Solution
    """

    py_routes: list[list[int]] = []
    capacity: list[float] = []
    c_to_route_id = [-1]
    for c_i in range(1, len(py_instance.vertices)):
        c_to_route_id.append(c_i - 1)
        py_routes.append([c_i])
        capacity.append(py_instance.vertices[c_i].demand)

    savings = list()
    for c_i in range(1, len(py_instance.vertices)):
        for c_j in range(1, len(py_instance.vertices)):
            if c_i == c_j:
                pass
            else:
                # s_ij = c_i0 + c_0j - c_ij
                s_ij = py_instance.arcs[(c_i, 0)].distance + py_instance.arcs[(0, c_j)].distance - py_instance.arcs[
                    (c_i, c_j)].distance
                savings.append((s_ij, c_i, c_j))
    savings.sort(reverse=True)

    for s_ij, c_i, c_j in savings:
        if s_ij <= 0:
            break

        route_id_of_c_i = c_to_route_id[c_i]
        route_id_of_c_j = c_to_route_id[c_j]

        if route_id_of_c_i != route_id_of_c_j and len(py_routes[route_id_of_c_i]) > 0 and len(
                py_routes[route_id_of_c_j]) > 0 \
                and py_routes[route_id_of_c_i][-1] == c_i and py_routes[route_id_of_c_j][0] == c_j:
            if capacity[route_id_of_c_i] + capacity[route_id_of_c_j] > py_instance.parameters.capacity:
                pass
            else:
                # merge
                # r_i [..,4,5]
                # r_j [8,9,..]
                # merge [..,4,5,8,9,..]
                r_i: Route = py_routes[route_id_of_c_i]
                r_j: Route = py_routes[route_id_of_c_j]

                r_i.extend(r_j)
                c_to_route_id[r_i[-1]] = route_id_of_c_i

                r_j.clear()

                capacity[route_id_of_c_i] = capacity[route_id_of_c_i] + capacity[route_id_of_c_j]

    simple_solution = list(filter(lambda r: len(r) > 0, py_routes))
    rb_solution = rb.Solution(evaluation, cpp_instance, len(simple_solution))
    routes: [rb.Route] = [r for r in rb_solution.routes]
    for r_id in range(len(routes)):
        routes[r_id].insert_vertices_after([(c_id, 0) for c_id in simple_solution[r_id]])

    return rb_solution
