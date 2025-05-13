import random
import routingblocks as rb

from pysolver.instance.models import Instance


def generate_random_solution(py_instance: Instance, evaluation: rb.Evaluation,
                             cpp_instance: rb.Instance) -> rb.Solution:
    customers = [x for x in py_instance.customers]
    random.shuffle(customers)

    routes = []
    # route = [0]
    route = []
    capacity = 0

    for c in customers:
        if capacity + c.demand > py_instance.parameters.capacity:
            routes.append(route)
            route = []
            capacity = 0

        route.append(c.vertex_id)
        capacity = capacity + c.demand

    routes.append(route)

    return rb.Solution(evaluation, cpp_instance,
                       [rb.create_route(evaluation, cpp_instance, route) for route in routes])
