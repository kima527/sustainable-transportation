import folium
import random
from pysolver.instance.models import Instance

def draw_routes_on_map(instance: Instance, R: list[list[int]]):
    # Extract node coordinates
    node_coords = {
        v.vertex_id: (v.y_coord, v.x_coord)  # Note: folium uses (lat, lon) = (y, x)
        for v in instance.vertices
    }

    # Create center point for the map
    center_lat = sum(v.y_coord for v in instance.vertices) / len(instance.vertices)
    center_lon = sum(v.x_coord for v in instance.vertices) / len(instance.vertices)
    m = folium.Map(location=(center_lat, center_lon), zoom_start=10)

    # Add all nodes to the map
    for v in instance.vertices:
        folium.Marker(
            location=(v.y_coord, v.x_coord),
            tooltip=f"ID: {v.vertex_id}",
            icon=folium.Icon(color='green' if v.vertex_id != 0 else 'black')  # depot is black
        ).add_to(m)

    # Generate distinct colors for each route
    def get_color_palette(n):
        colors = [
        "red", "blue", "green", "purple", "orange", "darkred", "#8B0000",
      "#5C4033", "darkblue", "darkgreen", "cadetblue", "#4B0082",
      "#800040", "#00008B", "#006400", "#2F4F4F", "black",
      "#9932CC", "#8B4513", "#483D8B", "#556B2F", "#708090", 
      "#191970", "#A52A2A", "#2E8B57", "#6B8E23", "#800000",
      "#4682B4", "#B22222", "#1C1C1C"
        ]
        if n <= len(colors):
            return colors[:n]
        # If more colors needed, generate random ones
        return colors + ['#%06X' % random.randint(0, 0xFFFFFF) for _ in range(n - len(colors))]

    route_colors = get_color_palette(len(R))

    # Draw routes with different colors
    for r_idx, route in enumerate(filter(lambda r: len(r) > 2, R)):
        path = []
        for vid in route:
            path.append(node_coords[vid])
        if len(path) >= 2:
            folium.PolyLine(
                path,
                color=route_colors[r_idx],
                weight=4,
                opacity=0.8,
                tooltip=f"Route {r_idx}"
            ).add_to(m)
        else:
            pass
            #print(f"[Folium] Skipping route {r_idx} " f"(too few valid points, {len(route)} customers)")


    m.save("vis_routes_map.html")
    print("Map saved to 'vis_routes_map.html'")
