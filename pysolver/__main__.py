from pathlib import Path
import random

import click
import routingblocks as rb
import routingblocks_bais_as as rb_ext

from pysolver.construction.random import generate_random_solution
from pysolver.instance.interface import create_cpp_instance
from pysolver.instance.parsing import parse_instance
from pysolver.utils.plot import draw_routes


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
    output_path = Path(output_path)

    print(f"loading instance from {instance_path}")

    py_instance = parse_instance(instance_path)
    instance = create_cpp_instance(py_instance)

    evaluation = rb_ext.CVRPEvaluation(py_instance.parameters.capacity)

    # 0. check routingblocks working properly
    solution = generate_random_solution(py_instance, evaluation, instance)
    print(solution, solution.feasible)

    # 1. create solution (savings)

    # 2. create solution (insertion)

    # 3. improve solution (LS)

    # 4. custom operator (LS)

    # 5. metaheuristic (LNS)

    # 6. metaheuristic (ALNS)

    # 7. custom operator (ALNS)

    # 8. adapting routingblocks

    # draw something with colors
    draw_routes(py_instance, [[v.vertex_id for v in route] for route in solution])


if __name__ == '__main__':
    main()
