import routingblocks as rb

def iterative_local_search(
    py_instance,
    evaluation,
    cpp_instance,
    rng,
    initial_solution: rb.Solution,
    max_iterations: int = 100,
    perturbation_strength: int = 15,
    ls_granularity: int = 20,
):
    
    from pysolver.ls import CustomLocalSearch
    from routingblocks.operators import WorstRemovalOperator, BestInsertionOperator, random_selector_factory, first_move_selector

    best_solution = initial_solution.copy()
    
    
    ls = CustomLocalSearch(py_instance, evaluation, cpp_instance, granularity=ls_granularity)
    best_solution = ls.improve(best_solution)

    for i in range(max_iterations):
        # Local copy
        candidate = best_solution.copy()

        # Destroying
        destroy = WorstRemovalOperator(cpp_instance, random_selector_factory(rng))
        removed = destroy.apply(evaluation, candidate, perturbation_strength)

        # Repairing
        repair = BestInsertionOperator(cpp_instance, first_move_selector)
        repair.apply(evaluation, candidate, removed)

        # LS
        candidate = ls.improve(candidate)

        # Accept only better solutions
        if candidate.cost < best_solution.cost:
            best_solution = candidate
            #print(f"Iteration {i}: Improved → obj = {best_solution.cost:.2f}")
        #else:
            #print("error")

    
    return best_solution