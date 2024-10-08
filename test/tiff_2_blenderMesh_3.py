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

import bpy
import bpy.bmesh as bm
import numpy as np
import rasterio


# Function to create a mesh from height map
def create_mesh_from_height_map(height_map, width, height):
    # Create a new mesh
    # mesh = bpy.data.meshes.new("height_map_mesh")
    # create new mesh with heigh and width
    # bm = bmesh.new()

    # Create vertices
    print("Create vertices")
    verts = np.zeros((width * height), dtype=object)
    k = 0
    for y in range(height):
        for x in range(width):
            k += 1
            verts[k] = height_map[y, x]

    # bm.verts.ensure_lookup_table()

    # Create faces
    print("Create faces")
    faces = np.empty((width - 1) * (height - 1), dtype=object)
    for y in range(height - 1):
        for x in range(width - 1):
            v1 = verts[y * width + x]
            v2 = verts[y * width + (x + 1)]
            v3 = verts[(y + 1) * width + (x + 1)]
            v4 = verts[(y + 1) * width + x]
            bm.faces.new((v1, v2, v3, v4))

    mesh = bpy.data.meshes.new("DEM")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # Create a new object with the mesh
    obj = bpy.data.objects.new("HeightMapObject", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def create_mesh_primitive(elevation_data, mesh_size):
    # Step 2: Create a plane in Blender
    print("Create plane")
    height, width = elevation_data.shape
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=width - 1, y_subdivisions=height - 1, size=mesh_size)

    # Reshape the elevation data to match the vertex coordinates
    print("Flatten array")
    elevation_data_reshaped = elevation_data.flatten()

    # Apply the changes back to the mesh vertices
    for i, vertex in enumerate(bpy.context.active_object.data.vertices):
        vertex.co.z = elevation_data_reshaped[i]


def create_mesh_bmesh(elevation_data, mesh_size, dx, dy):
    # Step 2: Create a plane in Blender
    print("Create plane")
    height, width = elevation_data.shape

    # Reshape the elevation data to match the vertex coordinates
    elevation_data_reshaped = elevation_data.flatten()
    verts = [(i * dx, (i // width) * dx, z) for i, z in enumerate(elevation_data_reshaped)]

    mesh = bpy.data.meshes.new("DEM")
    mesh.from_pydata(verts, [], [])
    mesh.update()

    bpy.ops.object.select_all(action="DESELECT")
    # create an object with that mesh
    obj = bpy.data.objects.new("dem", mesh)
    # Link object to scene
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


# Argument parser setup
parser = argparse.ArgumentParser(description="Import TIFF image and create height map mesh in Blender.")
parser.add_argument("image_path", type=str, help="Path to the TIFF image file")

# Parse arguments
args = parser.parse_args()

print(f"loading {args.image_path}")
# Step 1: Load the GeoTIFF data

with rasterio.open(args.image_path) as dataset:
    elevation_data = dataset.read(1)  # Read the first band
    mesh_size = dataset.shape[0] * dataset.res[0]
    dx = dataset.res[0]
    dy = dataset.res[1]
print("..loaded")


# create_mesh_from_height_map(elevation_data, dataset.shape[1], dataset.shape[0])
create_mesh_bmesh(elevation_data, mesh_size, dx, dy)


bpy.ops.preferences.addon_enable(module="add_mesh_extra_objects")
print(f"Installed Addons: {bpy.context.preferences.addons.keys()}")

# load material from file

# append regolith material
material_name = "Regolith1_MAT"
blend_file = "assets/materials/moon_shaders.blend"
bpy.ops.wm.append(
    filename=material_name,
    filepath=blend_file + "/Material/" + material_name,
    directory=blend_file + "/Material",
)
rock_material = bpy.data.materials.get(material_name)
bpy.context.object.data.materials.append(rock_material)


# Optionally: Smooth shading
bpy.ops.object.shade_smooth()

# save blender file
bpy.ops.wm.save_as_mainfile(filepath="random_rocks.blend")
