#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import argparse
import os

import pandas as pd
import trimesh


def get_mesh_info(mesh_path):
    # Load the mesh from file
    mesh = trimesh.load(mesh_path, force="mesh")

    # Gather mesh information
    info = {
        "File Name": os.path.basename(mesh_path),
        "File Size (KB)": os.path.getsize(mesh_path) / 1024,
        "Number of Vertices": len(mesh.vertices),
        "Number of Faces": len(mesh.faces),
        "Max cube lenght (m)": mesh.bounding_box_oriented.primitive.extents.max(),
        "Mesh Volume (if solid)": mesh.volume if mesh.is_watertight else "Not a solid",
        "Surface Area": mesh.area,
    }
    return info


def main():
    parser = argparse.ArgumentParser(description="Analyze mesh files and display mesh attributes.")
    parser.add_argument("mesh_files", type=str, nargs="+", help="List of mesh file paths to analyze.")
    args = parser.parse_args()

    # List to store mesh info dictionaries
    mesh_infos = []

    # Process each mesh file
    for mesh_file in args.mesh_files:
        mesh_info = get_mesh_info(mesh_file)
        mesh_infos.append(mesh_info)

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(mesh_infos)

    # Print the DataFrame

    # save to markdown table, format floats to 2 decimal places
    markdown_table = df.to_markdown(floatfmt=".2f", index=False)
    print(markdown_table)


if __name__ == "__main__":
    main()
