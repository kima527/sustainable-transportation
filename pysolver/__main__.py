from pathlib import Path
import random

import click
import numpy as np

import routingblocks as rb
import routingblocks_bais_as as rb_ext
from collections import namedtuple
import folium
import json
from pathlib import Path

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
    _compactify(solution)

    routes = [r for r in solution.routes if len(r) > 2]
    print(routes)

    print("=" * 170)
    print(f"ROUTE SUMMARY  |  Total Routes Used: {len(routes)} | Toll: {toll}€/km")
    print("=" * 170)

    header = (f"{'Route':<8} {'#Cust.':<8} {'Dist.':<8} {'InDist.':<8} {'Dur.':<8} {'Veh.':<6} {'Total€':<10} "
              f"{'Fixed€':<10} {'Acq€':<10} {'Fuel€':<10} {'Maint€':<10} {'Wage€':<10} {'Toll€':<10} {'Green↓€':<10} "
              f"{'Util.W':<10} {'Util.V':<10}")
    print(header)
    print("-" * len(header))

    # Totals
    total_cust = total_dist = total_in = total_dur = 0.0
    total_cost = total_fixed = total_acq = total_fuel = total_maint = 0.0
    total_wage = total_toll = total_green = 0.0
    sum_w_util = sum_v_util = 0.0
    route_count = 0

    vehicle_types_used = []

    for idx, route in enumerate(routes):
        try:
            summary = evaluation.summarize_route(route)

            route_id = idx + 1
            num_customers = len(route) - 2
            distance = summary["distance"]
            dist_inside = summary["inside_km"]
            duration = summary["duration"] / 60
            vehicle_type = summary["vehicle_type"]
            vehicle_types_used.append(vehicle_type)

            cost = summary["cost"]
            fixed_cost = summary.get("fixed_cost", 0.0)
            acq_cost = summary["amortized_acq_cost"]
            fuel_cost = summary["fuel_cost"]
            maint_cost = summary["maint_cost"]
            wage_cost = summary["wage_cost"]
            toll_cost = summary["toll_cost"]
            green_discount = summary["green_upside_cost_discount"]

            weight_util = summary["load_weight"] / summary["capacity_weight"] if summary["capacity_weight"] > 0 else 0.0
            volume_util = summary["load_volume"] / summary["capacity_volume"] if summary["capacity_volume"] > 0 else 0.0

            # Totals
            total_cust += num_customers
            total_dist += distance
            total_in += dist_inside
            total_dur += duration
            total_cost += cost
            total_fixed += fixed_cost
            total_acq += acq_cost
            total_fuel += fuel_cost
            total_maint += maint_cost
            total_wage += wage_cost
            total_toll += toll_cost
            total_green += green_discount
            sum_w_util += weight_util
            sum_v_util += volume_util
            route_count += 1

            print(f"{route_id:<8} {num_customers:<8} {distance:<8.1f} {dist_inside:<8.1f} {duration:<8.1f} "
                  f"{vehicle_type:<6} €{cost:<9.2f} €{fixed_cost:<9.2f} €{acq_cost:<9.2f} €{fuel_cost:<9.2f} "
                  f"€{maint_cost:<9.2f} €{wage_cost:<9.2f} €{toll_cost:<9.2f} €{green_discount:<9.2f} "
                  f"{weight_util:<10.1%} {volume_util:<10.1%}")

        except Exception as e:
            print(f"[ERROR] Route {idx + 1}: {e}")

    print("-" * len(header))
    if route_count:
        avg_w_util = sum_w_util / route_count
        avg_v_util = sum_v_util / route_count
    else:
        avg_w_util = avg_v_util = 0.0

    print(f"{'TOTAL':<8} {int(total_cust):<8} {total_dist:<8.1f} {total_in:<8.1f} {total_dur:<8.1f} {'':<6} "
          f"€{total_cost:<9.2f} €{total_fixed:<9.2f} €{total_acq:<9.2f} €{total_fuel:<9.2f} "
          f"€{total_maint:<9.2f} €{total_wage:<9.2f} €{total_toll:<9.2f} €{total_green:<9.2f} "
          f"{avg_w_util:<10.1%} {avg_v_util:<10.1%}")

    resale_value = evaluation.compute_resale_value_for_unused_vehicles(vehicle_types_used)
    print("=" * 170 + "\n")
    print(f"{'RESALE VALUE FOR UNUSED VEHICLES':<60} €{resale_value:.2f}")


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
    toll = 0
    city = base_city._replace(toll_per_km_inside=toll)

    cfg = load_cfg(Path("pysolver/finetuned_params.json"))
    block = pick_block(instance_path, cfg)

    s_cfg   = block.get("savings", {})
    lns_cfg = block.get("lns", {})
    ils_cfg = block.get("ils", {})

    evaluation = rb_ext.HFVRPEvaluation(veh_props, initial_veh_props, p.max_work_time, city._asdict())

    # 1. Savings Construction
    evaluation.reset_free_vehicle_usage()
    savings_solution = savings(py_instance, evaluation, cpp_instance, 
                               max_customers_per_route=int(s_cfg.get("max_customers_per_route", 16)),
                               min_saving=float(s_cfg.get("min_saving", 0.0)))
    print_solution_info(f"Savings with max_customers_per_route {int(s_cfg.get("max_customers_per_route", 16))} ", savings_solution)

    # 2. LNS
    evaluation.reset_free_vehicle_usage()
    lns_savings_solution = lns(py_instance, evaluation, cpp_instance, cpp_random, savings_solution, 2500,
                               remove_fraction=float(lns_cfg.get("destroy_fraction", 0.2)),
                               destroy_weights=tuple(lns_cfg.get("destroy_weights", [1.0, 0.0, 0.0])))
    print_solution_info(f"LNS with remove_fraction {float(lns_cfg.get("destroy_fraction", 0.2))}", lns_savings_solution)
    
    # 3. ILS
    evaluation.reset_free_vehicle_usage()
    ils_solution = iterative_local_search(py_instance, evaluation, cpp_instance, cpp_random, lns_savings_solution,  
                                          max_iterations=int(ils_cfg.get("max_iterations", 50)),
                                          remove_fraction=float(ils_cfg.get("destroy_fraction", 0.15)))
    print_solution_info(f"ILS with remove_fraction {float(ils_cfg.get("destroy_fraction", 0.15))}", ils_solution)

    # 4. Solution
    evaluation.reset_free_vehicle_usage()
    print_route_summary(py_instance, ils_solution, evaluation, toll)

    # draw something with colors
    draw_routes(py_instance, [[v.vertex_id for v in route] for route in ils_solution])
    draw_routes_on_map(py_instance, [[v.vertex_id for v in route] for route in ils_solution])

def load_cfg(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_block(instance_path: Path, cfg: dict) -> dict:
    stem = instance_path.stem.lower()  # "newyork", "paris", "shanghai"
    return cfg.get("instances", {}).get(stem, {})

if __name__ == '__main__':
    main()