from pathlib import Path
import random

import click
import numpy as np

import routingblocks as rb
import routingblocks_bais_as as rb_ext
from collections import namedtuple
import folium

from pysolver.construction.savings import savings
from pysolver.construction.insertion import sequential_best_insertion
from pysolver.construction.random import generate_random_solution
from pysolver.ls import CustomLocalSearch
from pysolver.instance.interface import create_cpp_instance
from pysolver.instance.parsing import parse_instance
from pysolver.utils.plot import draw_routes
from pysolver.utils.plot_map import draw_routes_on_map
from pysolver.metaheuristic.ils import iterative_local_search


from pysolver.metaheuristic import lns

def print_solution_info(name: str, solution: rb.Solution):
    print(f"{name} | obj: {solution.cost} | feasible: {solution.feasible}")

def route_distance(route, py_instance):
    distance = 0
    for i in range(len(route) - 1):
        u = route[i].vertex_id
        v = route[i + 1].vertex_id
        distance += py_instance.arcs[(u, v)].distance  # or .cost if 'distance' doesn't exist
    return distance

def _compactify(sol: rb.Solution) -> None:
    i = 0
    while i < len(sol):
        if len(sol[i]) <= 2:              # depot → depot
            sol.remove_route(sol[i])
        else:
            i += 1

def print_route_summary(py_instance, solution: rb.Solution, evaluation: rb_ext.HFVRPEvaluation, toll):
    _compactify(solution)                          # <<< purge first

    routes = [r for r in solution.routes if len(r) > 2]

    print(routes)
    
    for i, r in enumerate(routes):
        print(f"Route {i + 1}: {[v.vertex_id for v in r]}")
        
    print("=" * 110)
    print(f"ROUTE SUMMARY  |  Total Routes Used: {len(routes)} | Toll: {toll}€/km")
    print("=" * 110)
    print(f"{'Route':<10} {'#Cust.':<10} {'Cost(€)':<10} {'Dist.(km)':<10} {'Dist_in(km)':<10} {'Toll(€)':<10} {'Dur.(min)':<10} "
          f"{'Veh.Type':<10} {'Util.W':<10} {'Util.V':<10}")
    print("-" * 110)

    # ------------------------------------------------------------------
    #  ❑  Accumulators for the grand totals / averages
    # ------------------------------------------------------------------
    total_cust = total_cost = total_dist = total_in = total_toll = total_dur = 0.0
    sum_w_util = sum_v_util = 0.0
    route_count = 0
    # ------------------------------------------------------------------

    for idx, route in enumerate(routes):
        if len(route) <= 2:
            print(f"{idx + 1:<6} {'EMPTY':<8}")
            continue

        try:
            summary = evaluation.summarize_route(route)

            route_id = idx + 1
            num_customers = len(route) - 2
            cost = summary["cost"]
            distance = summary["distance"]
            dist_inside = summary["inside_km"]
            toll_cost = summary["toll_cost"]
            duration = summary["duration"] / 60  # seconds → min
            vehicle_type = summary["vehicle_type"]

            weight_util = (summary["load_weight"] / summary["capacity_weight"]
                           if summary["capacity_weight"] > 0 else 0.0)
            volume_util = (summary["load_volume"] / summary["capacity_volume"]
                           if summary["capacity_volume"] > 0 else 0.0)
            total_cust += num_customers
            total_cost += cost
            total_dist += distance
            total_in += dist_inside
            total_toll += toll_cost
            total_dur += duration
            sum_w_util += weight_util
            sum_v_util += volume_util
            route_count += 1


            if route_count:  # avoid division by 0
                avg_w = sum_w_util / route_count
                avg_v = sum_v_util / route_count
            else:
                avg_w = avg_v = 0.0

            print(f"{route_id:<10} {num_customers:<10} €{cost:<10.2f} {distance:<10.1f} {dist_inside:<10.1f} "
                  f"€{toll_cost:<10.2f} {duration:<10.1f} {vehicle_type:<10} {weight_util:<10.1%} {volume_util:<10.1%}")
        except Exception as e:
            print(f"[ERROR] Failed to summarize Route {idx + 1}: {e}")

    print("=" * 110)
    print(f"{'TOTAL':<10} {int(total_cust):<10} "
          f"€{round(total_cost,2):<10} {total_dist:<10.1f} {total_in:<10.1f} "
          f"€{total_toll:<10.2f} {total_dur:<10.1f} "
          f"{'':<10} {avg_w:<10.1%} {avg_v:<10.1%}")

    resale_value = evaluation.compute_resale_value_for_unused_vehicles()
    print(f"{'RESALE VALUE FOR UNUSED VEHICLES':<10} €{resale_value:.2f}")

    print("=" * 110)

# def print_vt_id_and_routes(evaluation: rb_ext.CVRPEvaluation, solution: rb.Solution):
#     for i, route in enumerate(solution.routes):
#         print(f"vt_{evaluation.compute_best_vehicle_id_of_route(route)}:", route)

@click.command('pysolver')
@click.argument('instance-path', type=click.Path(exists=True, dir_okay=False, file_okay=True), required=True)
@click.option('--output-path', type=click.Path(exists=True, dir_okay=True, file_okay=False), default=Path('.'))
@click.option('--seed', type=int, default=None)



def main(instance_path: Path, output_path: Path, seed: int):
    # set random number generator seed to ensure deterministic behavior for reproducibility
    if seed is None:
        seed = 0
    random.seed(seed)
    np.random.seed(seed)
    cpp_random = rb.Random(seed)

    instance_path = Path(instance_path)

    py_instance, fleets, initial_fleets = parse_instance(instance_path, return_fleets=True)
    cpp_instance = create_cpp_instance(py_instance)

    veh_props = [tuple(row) for row in fleets]
    initial_veh_props = [tuple(row) for row in initial_fleets]
    CityParams = namedtuple("CityParams",
                            ["utility_other", "maintenance_cost",
                             "price_elec", "price_diesel",
                             "hours_per_day", "wage_semi", "wage_heavy", 
                             "toll_per_km_inside", "revenue", "green_upside"])

    p = py_instance.parameters
    base_city = CityParams(
        p.utility_other,
        p.maintenance_cost,
        p.price_elec,
        p.price_diesel,
        p.hours_per_day,
        p.wage_semi,
        p.wage_heavy,
        0.0,  # default toll, will be overwritten in loop 
        p.revenue,
        p.green_upside
    )
    toll = 0.4
    city = base_city._replace(toll_per_km_inside=toll)

    evaluation = rb_ext.HFVRPEvaluation(veh_props, initial_veh_props, p.max_work_time, city._asdict())

    # 0. check routingblocks working properly
    # solution = generate_random_solution(py_instance, evaluation, instance)
    # print(solution, solution.feasible)

    # 1. create solution (savings)
    savings_solution = savings(py_instance, evaluation, cpp_instance)
    print_solution_info("Savings", savings_solution)
    #print_vt_id_and_routes(evaluation, savings_solution)

    # 2. create solution (insertion)
    #insertion_solution = sequential_best_insertion(py_instance, evaluation, cpp_instance)
    #print_solution_info("Insertion", insertion_solution)
    
    # 2.1


    
    # 3. metaheuristic (LNS)
    lns_savings_solution = lns(py_instance, evaluation, cpp_instance, cpp_random, savings_solution, 250)
    print_solution_info("LNS_savings", lns_savings_solution)
    
    # print_vt_id_and_routes(evaluation, lns_insertion_solution)

    #ils_solution = lns_savings_solution

    ils_solution = iterative_local_search(py_instance, evaluation, cpp_instance, cpp_random, lns_savings_solution,  
                                          max_iterations=50, perturbation_strength=10, ls_granularity=20)

    # 4. improve solution (LS)
    #ls_engine = CustomLocalSearch(py_instance, evaluation, cpp_instance, granularity=20)
    #ls_engine.improve(lns_savings_solution)
    
    # 5. Solution
    
    print_solution_info("ILS", ils_solution)

    print_route_summary(py_instance, ils_solution, evaluation, toll)
    # 6. metaheuristic (ALNS)

    # 7. custom operator (ALNS)

    # 8. adapting routingblocks

    # draw something with colors
    draw_routes(py_instance, [[v.vertex_id for v in route] for route in ils_solution])
    draw_routes_on_map(py_instance, [[v.vertex_id for v in route] for route in ils_solution])
    
if __name__ == '__main__':
    main()