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
import bpy

# Parameters
N = 300  # Number of vertices along width
M = 300  # Number of vertices along length
width = 10  # Width of the plane
length = 10  # Length of the plane
file_path = "../moon_data/pgda78/Haworth_final_adj_5mpp_surf.tif"

# activate addon add_mesh_extra_objects


# Create the plane
bpy.ops.mesh.primitive_grid_add(x_subdivisions=N, y_subdivisions=M, size=1)
plane = bpy.context.object
plane.scale = (width / 2.0, length / 2.0, 1.0)

# Create a new texture
texture = bpy.data.textures.new(name="DisplacementTexture", type="IMAGE")

# Load the TIFF image
image = bpy.data.images.load(file_path)
texture.image = image

# Create a displacement modifier
displace_modifier = plane.modifiers.new(name="Displace", type="DISPLACE")
displace_modifier.texture = texture

# Set the displacement strength
displace_modifier.strength = 1.0  # Adjust the strength as needed


# Optionally, smooth the shading
bpy.ops.object.shade_smooth()
# save the file
bpy.ops.wm.save_as_mainfile(filepath="tiff_2_blenderMesh.blend")
