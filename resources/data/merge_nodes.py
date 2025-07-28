import os

def parse_nodes(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Skip header and empty lines
    return [line.strip() for line in lines if line.strip() and not line.startswith("Id")]

def merge_and_sort_nodes(file1, file2, output_path):
    header = "Id Lon Lat Demand[kg] Demand[m^3*10^-3] Duration"

    # Read and parse node files
    nodes1 = parse_nodes(file1)
    nodes2 = parse_nodes(file2)

    # Merge nodes
    all_nodes = nodes1 + nodes2

    # Sort using natural alphanumeric order (e.g., C1 < C2 < C10 < D0)
    def sort_key(line):
        id_part = line.split()[0]
        prefix = ''.join(filter(str.isalpha, id_part))
        number = ''.join(filter(str.isdigit, id_part))
        return (prefix, int(number)) if number else (prefix, -1)

    all_nodes.sort(key=sort_key)

    # Write result to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for line in all_nodes:
            f.write(line + "\n")

if __name__ == "__main__":
    # File paths relative to script location
    current_dir = os.path.dirname(__file__)
    file1 = os.path.join(current_dir, "NewYorkManhattan.nodes")
    file2 = os.path.join(current_dir, "NewYorkState.nodes")
    output_file = os.path.join(current_dir, "NewYorkMerged.nodes")

    merge_and_sort_nodes(file1, file2, output_file)
    print(f"✅ Merged and sorted file saved as: {output_file}")
