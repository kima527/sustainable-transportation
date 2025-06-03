import routingblocks as rb
from pysolver.instance.models import Instance


def lns(py_instance: Instance, evaluation: rb.Evaluation, cpp_instance: rb.Instance,
        cpp_random: rb.Random,
        initial_solution: rb.Solution, max_iterations: int) -> rb.Solution:

    lns = rb.LargeNeighborhood(cpp_random)

    destroy_operators = [
        rb.operators.RandomRemovalOperator(cpp_random)
    ]

    for operator in destroy_operators:
        lns.add_destroy_operator(operator)

    repair_operators = [
        rb.operators.BestInsertionOperator(cpp_instance, rb.operators.move_selectors.first_move_selector)
    ]

    for operator in repair_operators:
        lns.add_repair_operator(operator)

    current_solution = initial_solution
    for it in range(max_iterations):
        new_solution = current_solution.copy()
        lns.generate(evaluation, new_solution, int(len(py_instance.vertices) * 0.25))

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

