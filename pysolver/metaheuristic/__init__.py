import random

import routingblocks as rb
from pysolver.instance.models import Instance
from routingblocks.operators.move_selectors import last_move_selector, random_selector_factory
from routingblocks.operators.related_removal import RelatedVertexRemovalMove, build_relatedness_matrix
import math



def lns(py_instance: Instance, evaluation: rb.Evaluation, cpp_instance: rb.Instance,
        cpp_random: rb.Random,
        initial_solution: rb.Solution, max_iterations: int) -> rb.Solution:

    lns = rb.LargeNeighborhood(cpp_random)

    vertices = py_instance.vertices

    def distance_relatedness(u: int, v: int) -> float:
        vert_u = vertices[u]
        vert_v = vertices[v]
        dx = vert_u.x_coord - vert_v.x_coord
        dy = vert_u.y_coord - vert_v.y_coord
        return -math.hypot(dx, dy)

    relatedness_matrix = build_relatedness_matrix(cpp_instance, distance_relatedness)

    destroy_operators = [
        rb.operators.RandomRemovalOperator(cpp_random),
        rb.operators.WorstRemovalOperator(cpp_instance, last_move_selector),
        rb.operators.RelatedRemovalOperator(
            relatedness_matrix,
            random_selector_factory(cpp_random),  # move_selector
            random_selector_factory(cpp_random),  # seed_selector
            random_selector_factory(cpp_random)  # initial_seed_selector
        )
    ]

    destroy_weights = [1, 0, 0]

    for operator in destroy_operators:
        lns.add_destroy_operator(operator)

    repair_operators = [
        rb.operators.BestInsertionOperator(cpp_instance, rb.operators.move_selectors.first_move_selector)
    ]

    for operator in repair_operators:
        lns.add_repair_operator(operator)

    current_solution = initial_solution
    for it in range(max_iterations):
        destroy_op = random.choices(destroy_operators, weights=destroy_weights, k=1)[0]
        new_solution = current_solution.copy()
        num_removed = int(len(py_instance.vertices) * 0.1)
        destroy_op.apply(evaluation, new_solution, num_removed)

        vertex_ids = list(missing_customers(new_solution, len(py_instance.vertices)))
        repair_op = repair_operators[0]
        repair_op.apply(evaluation, new_solution, vertex_ids)

        if new_solution.cost < current_solution.cost:
            print(f"it {it}: new best solution found with {new_solution.cost}")
            current_solution = new_solution
        else:
            pass

        missing = missing_customers(new_solution, len(py_instance.vertices))
        if missing:
            print(f"⚠️  Iteration {it}: Missing customers {missing}")

    return current_solution

def missing_customers(solution: rb.Solution, num_customers: int) -> set[int]:
    visited = set()
    for route in solution:
        for v in route:
            visited.add(v.vertex_id)
    expected = set(range(1, num_customers))  # assuming 0 = depot
    return expected - visited

