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
import time

import bpy
import matplotlib.pyplot as plt

# clear the scene
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.object.delete()

obj_filepath = "assets/rocks/earth_scanned/rock7.ply"
bpy.ops.wm.ply_import(filepath=obj_filepath)
rock_obj = bpy.context.selected_objects[-1]

# load obj for rock type 16
time_copy = []
for i in range(2000):
    start = time.time()
    bpy.ops.object.duplicate(linked=True)
    # move to random location
    bpy.context.object.location = (
        random.uniform(-10, 10),
        random.uniform(-10, 10),
        random.uniform(-10, 10),
    )
    # scale randomly
    bpy.context.object.scale = (
        random.uniform(0.1, 1),
        random.uniform(0.1, 1),
        random.uniform(0.1, 1),
    )

    # random rotation
    bpy.context.object.rotation_euler = (
        random.uniform(0, 3.14),
        random.uniform(0, 3.14),
        random.uniform(0, 3.14),
    )
    end = time.time()
    time_copy.append(end - start)

# plot the time taken to copy the objects

fig, ax = plt.subplots()
ax.plot(time_copy)
ax.set_xlabel("Object index")
ax.set_ylabel("Time to copy object")
ax.set_title("Time to copy objects")
plt.show()

# position the camera to see all the cubes
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.view3d.camera_to_view_selected()


bpy.context.scene.render.filepath = "random_cubes.png"
# bpy.ops.render.render(write_still=True)

# save the file
bpy.ops.wm.save_as_mainfile(filepath="copy_objects.blend")
