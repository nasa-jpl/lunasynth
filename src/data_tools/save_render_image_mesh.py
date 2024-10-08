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

import trimesh

"""Use Trimesh to render a mesh to a PNG image with smooth shading.

Usage:
    python save_render_image_mesh.py mesh_file1.obj mesh_file2.stl ...

Output:
    A PNG image file for each input mesh file, saved in the same directory as the input file.
"""


def render_and_save(mesh_path):
    # Load the mesh from file
    mesh = trimesh.load(mesh_path)

    # If the mesh doesn't have vertex normals, calculate them for smooth shading
    if not mesh.vertex_normals.shape[0]:
        mesh.vertex_normals = mesh.vertex_normals

    # Set up a scene
    scene = trimesh.Scene(mesh)

    # Render the scene to a numpy array with smooth shading
    try:
        # The resolution can be adjusted as needed
        png = scene.save_image(resolution=[1920, 1080], visible=False, smooth=True)
    except Exception as e:
        print(f"An error occurred during rendering of {mesh_path}: {e}")
        return

    if png is not None:
        # Construct the output filename
        output_filename = os.path.splitext(mesh_path)[0] + ".png"
        # Save the numpy array (image) to a PNG file
        with open(output_filename, "wb") as f:
            f.write(png)
        print(f"Render saved to '{output_filename}'")
    else:
        print(f"Failed to render the image for {mesh_path}.")


def main():
    parser = argparse.ArgumentParser(description="Render meshes to PNG images with smooth shading.")
    parser.add_argument("mesh_files", type=str, nargs="+", help="List of mesh file paths to render.")
    args = parser.parse_args()

    for mesh_file in args.mesh_files:
        render_and_save(mesh_file)


if __name__ == "__main__":
    main()
