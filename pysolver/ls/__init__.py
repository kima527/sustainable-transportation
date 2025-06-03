import routingblocks as rb
from pysolver.instance.models import Instance


class CustomLocalSearch:
    _local_search: rb.LocalSearch
    _reduced_arc_set: rb.ArcSet
    _operators: list[rb.LocalSearchOperator]

    def __init__(self, py_instance: Instance, evaluation: rb.Evaluation, cpp_instance: rb.Instance,
                 granularity: int = 20):
        self._local_search = rb.LocalSearch(cpp_instance, evaluation, None, rb.BestImprovementPivotingRule())

        arc_set = rb.ArcSet(len(py_instance.vertices))
        for i in range(1, len(py_instance.vertices)):
            sorted_arcs = sorted(
                ((j, py_instance.arcs[py_instance.vertices[i].vertex_id, py_instance.vertices[j].vertex_id]) for j in
                 range(1, len(py_instance.vertices))), key=lambda arc: arc[1].cost)
            for j, _ in sorted_arcs[granularity:]:
                arc_set.forbid_arc(i, j)

        self._reduced_arc_set = arc_set

        self._operators = [
            rb.operators.SwapOperator_0_1(cpp_instance, self._reduced_arc_set),
            rb.operators.SwapOperator_0_2(cpp_instance, self._reduced_arc_set),
            rb.operators.SwapOperator_1_1(cpp_instance, self._reduced_arc_set),
            rb.operators.InterRouteTwoOptOperator(cpp_instance, self._reduced_arc_set),
        ]

    def improve(self, solution: rb.Solution) -> rb.Solution:
        self._local_search.optimize(solution, self._operators)
        return solution
