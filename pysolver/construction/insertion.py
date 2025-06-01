from pysolver.instance.models import Instance
import routingblocks as rb


def sequential_best_insertion(py_instance: Instance, evaluation: rb.Evaluation,
                              cpp_instance: rb.Instance) -> rb.Solution:
    solution = rb.Solution(evaluation, cpp_instance, len(py_instance.vertices) - 1)
    best_insertion_operator = rb.operators.BestInsertionOperator(cpp_instance,
                                                                 rb.operators.move_selectors.first_move_selector)

    vertex_ids = [v.vertex_id for v in py_instance.vertices[1:]]

    best_insertion_operator.apply(evaluation, solution, vertex_ids)

    i = 0
    while i < len(solution):
        if solution[i].empty:
            solution.remove_route(solution[i])
        else:
            i += 1

    return solution
