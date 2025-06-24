from pathlib import Path
import random

import click
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

def print_route_summary(evaluation: rb.Evaluation, solution: rb.Solution, py_instance):
    print(f"Vehicles / routes used: {len(solution)}")
    for r_id, route in enumerate(solution.routes, start=1):
        n_customers = len(route) - 2
        dist = route_distance(route, py_instance)
        print(f"  Route {r_id:<2}:  customers = {n_customers:<3}   distance = {dist:>8.2f}")


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
        seed = random.randint(0, 10000)
    random.seed(seed)
    cpp_random = rb.Random(seed)

    instance_path = Path(instance_path)

    py_instance, fleets = parse_instance(instance_path, return_fleets=True)
    cpp_instance = create_cpp_instance(py_instance)

    veh_props = [(acq, cap_w, cap_v, rng) for (acq, cap_w, cap_v, rng) in fleets]
    CityParams = namedtuple("CityParams",
                            ["utility_other", "maintenance_cost",
                             "price_elec", "price_diesel",
                             "hours_per_day", "wage_semi", "wage_heavy"])

    p = py_instance.parameters
    city = CityParams(
        p.utility_other,
        p.maintenance_cost,
        p.price_elec,
        p.price_diesel,
        p.hours_per_day,
        p.wage_semi,
        p.wage_heavy,
    )
    evaluation = rb_ext.HFVRPEvaluation(veh_props, p.max_work_time, city)

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

    # 3. metaheuristic (LNS)
    lns_savings_solution = lns(py_instance, evaluation, cpp_instance, cpp_random, savings_solution, 10000)
    print_solution_info("LNS_savings", lns_savings_solution)
    # print_vt_id_and_routes(evaluation, lns_insertion_solution)

    # 4. improve solution (LS)
    ls_engine = CustomLocalSearch(py_instance, evaluation, cpp_instance,granularity=20)
    ls_engine.improve(lns_savings_solution)
    print_solution_info("LocalSearch", lns_savings_solution)

    #print_route_summary(evaluation, lns_savings_solution, py_instance)
    # 6. metaheuristic (ALNS)

    # 7. custom operator (ALNS)

    # 8. adapting routingblocks

    # draw something with colors
    draw_routes(py_instance, [[v.vertex_id for v in route] for route in lns_savings_solution])
    draw_routes_on_map(py_instance, [[v.vertex_id for v in route] for route in lns_savings_solution])


if __name__ == '__main__':
    main()
