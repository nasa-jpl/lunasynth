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
# create a blender file with 20 random cubes

import random

import bpy

# clear the scene
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.object.delete()

# list installed addons
installed_addons = bpy.context.preferences.addons.keys()

print(f"Installed Addons: {installed_addons}")

# activate addon add_mesh_extra_objects
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

rocks = []
for i in range(100):
    # defaults:
    #   preset_values='0',
    #   num_of_rocks=1,
    #   scale_X=(1, 1),
    #   skew_X=0,
    #   scale_Y=(1, 1),
    #   skew_Y=0,
    #   scale_Z=(1, 1),
    #   skew_Z=0,
    #   use_scale_dis=False,
    #   scale_fac=(1, 1, 1),
    #   deform=5,
    #   rough=2.5,
    #   detail=3,
    #   display_detail=2,
    #   smooth_fac=0,
    #   smooth_it=0,
    #   use_generate=True,
    #   use_random_seed=True,
    #   user_seed=1
    rocks.append(bpy.ops.mesh.add_mesh_rock(use_random_seed=False, user_seed=i, display_detail=1))
    bpy.ops.transform.translate(value=(random.uniform(-3, 3), random.uniform(-3, 3), 0.0))

    # assign rock material to the rock
    bpy.context.object.data.materials.append(rock_material)


# position the camera to see all the cubes
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.view3d.camera_to_view_selected()

# save the file
bpy.ops.wm.save_as_mainfile(filepath="random_rocks.blend")
