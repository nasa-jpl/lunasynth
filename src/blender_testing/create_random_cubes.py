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

# create 20 random cubes
for i in range(20):
    bpy.ops.mesh.primitive_cube_add(
        location=(
            random.uniform(-10, 10),
            random.uniform(-10, 10),
            random.uniform(-10, 10),
        )
    )
    bpy.ops.transform.resize(value=(random.uniform(0.1, 1), random.uniform(0.1, 1), random.uniform(0.1, 1)))

# position the camera to see all the cubes
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.view3d.camera_to_view_selected()


# save the file
bpy.ops.wm.save_as_mainfile(filepath="random_cubes.blend")
