import folium
import random
from pysolver.instance.models import Instance

def draw_routes_on_map(instance: Instance, R: list[list[int]]):
    # Extract node coordinates
    node_coords = {
        v.vertex_id: (v.x_coord, v.y_coord)  # Note: folium uses (lat, lon) = (y, x)
        for v in instance.vertices
    }

    # Create center point for the map
    center_lat = sum(v.x_coord for v in instance.vertices) / len(instance.vertices)
    center_lon = sum(v.y_coord for v in instance.vertices) / len(instance.vertices)
    m = folium.Map(location=(center_lat, center_lon), zoom_start=10)

    # Add all nodes to the map
    for v in instance.vertices:
        folium.Marker(
            location=(v.x_coord, v.y_coord),
            tooltip=f"ID: {v.vertex_id}",
            icon=folium.Icon(color='green' if v.vertex_id != 0 else 'black')  # depot is black
        ).add_to(m)

    # Generate distinct colors for each route
    def get_color_palette(n):
        colors = [
            "red", "blue", "green", "purple", "orange", "darkred", "lightred",
            "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple", "white",
            "pink", "lightblue", "lightgreen", "gray", "black", "lightgray"
        ]
        if n <= len(colors):
            return colors[:n]
        # If more colors needed, generate random ones
        return colors + ['#%06X' % random.randint(0, 0xFFFFFF) for _ in range(n - len(colors))]

    route_colors = get_color_palette(len(R))

    # Draw routes with different colors
    for r_idx, route in enumerate(filter(lambda r: len(r) > 1, R)):
        path = []
        for vid in route:
            if vid in node_coords:
                path.append(node_coords[vid])
        folium.PolyLine(
            path,
            color=route_colors[r_idx],
            weight=4,
            opacity=0.8,
            tooltip=f"Route {r_idx}"
        ).add_to(m)

    m.save("vis_routes_map.html")
    print("Map saved to 'vis_routes_map.html'")
