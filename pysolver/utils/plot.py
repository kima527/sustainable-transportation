# requires matplotlib package (https://matplotlib.org)
# Note: PyPy might have problems with this lib
import matplotlib.pyplot as plt

from pysolver.instance.models import Instance


# draw nodes and routes
# requires list of routes R = [[0,..,0],..], i.e., list of list of visits
def draw_routes(instance: Instance, R: list[list[int]]):
    # set color scheme
    # https://matplotlib.org/3.2.1/gallery/color/colormap_reference.html
    colors = plt.cm.get_cmap('tab10', len(R))

    fig, ax = plt.subplots()

    for r_idx, r in enumerate([i for i in filter(lambda r: len(r) > 2, R)]):
        path = list()
        for i in range(len(r)):
            # for i in range(1, len(r)-1):
            path.append((instance.vertices[r[i]].x_coord, instance.vertices[r[i]].y_coord))

        # plot control points and connecting lines
        x, y = zip(*path)
        line, = ax.plot(x, y, 'o-', color=colors(r_idx))

    ax.plot(instance.vertices[0].x_coord, instance.vertices[0].y_coord, 'ks')

    # ax.grid()
    ax.axis('equal')

    # hide axis labels
    plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    plt.tick_params(axis='y', which='both', right=False, left=False, labelleft=False)

    # hide bounding box
    # for pos in ['right', 'top', 'bottom', 'left']:
    #     plt.gca().spines[pos].set_visible(False)

    plt.show()
