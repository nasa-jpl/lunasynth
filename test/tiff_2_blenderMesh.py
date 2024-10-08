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

import bmesh
import bpy
import numpy as np
from PIL import Image


# Function to create a mesh from height map
def create_mesh_from_height_map(height_map, width, height):
    # Create a new mesh
    mesh = bpy.data.meshes.new("height_map_mesh")
    # create new mesh with heigh and width
    bm = bmesh.new()

    # Create vertices
    for y in range(height):
        for x in range(width):
            z = height_map[y, x] / 255.0  # Scale the height value
            bm.verts.new((x, y, z))

    bm.verts.ensure_lookup_table()

    # Create faces
    for y in range(height - 1):
        for x in range(width - 1):
            v1 = bm.verts[y * width + x]
            v2 = bm.verts[y * width + (x + 1)]
            v3 = bm.verts[(y + 1) * width + (x + 1)]
            v4 = bm.verts[(y + 1) * width + x]
            bm.faces.new((v1, v2, v3, v4))

    bm.to_mesh(mesh)
    bm.free()

    # Create a new object with the mesh
    obj = bpy.data.objects.new("HeightMapObject", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


# Argument parser setup
parser = argparse.ArgumentParser(description="Import TIFF image and create height map mesh in Blender.")
parser.add_argument("image_path", type=str, help="Path to the TIFF image file")

# Parse arguments
args = parser.parse_args()

# Load the image using PIL
image_path = args.image_path
image = Image.open(image_path)
height_map = np.array(image.convert("L"))  # Convert to grayscale

# Get the image dimensions
height, width = height_map.shape

# Create the mesh from the height map
create_mesh_from_height_map(height_map, width, height)

# Set up the viewport to see the result
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")

# Optionally, scale the mesh to fit the scene better
bpy.context.object.scale = (0.1, 0.1, 10)

#  save the file
bpy.ops.wm.save_as_mainfile(filepath="height_map.blend")

print("Height map mesh created successfully.")
