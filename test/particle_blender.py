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

import datetime as dt
import random
import time

import bpy
import humanize
import matplotlib.pyplot as plt
import numpy as np


def dth(d, minimum_unit="microseconds"):
    return humanize.precisedelta(dt.timedelta(seconds=d), minimum_unit=minimum_unit)


# clear the scene
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.object.delete()

obj_filepath = "assets/rocks/earth_scanned/rock7.ply"
bpy.ops.wm.ply_import(filepath=obj_filepath)
rock_obj = bpy.context.selected_objects[-1]


# Clear existing particles
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
bpy.ops.object.delete()

# Create a sphere to use as the particle
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0))
sphere = bpy.context.object

# Create an emitter plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
emitter = bpy.context.object
emitter.name = "Emitter"

# Add a particle system to the plane
bpy.ops.object.particle_system_add()
psys = emitter.particle_systems.active
pset = psys.settings

# Configure the particle system
n_objects = 1000
pset.count = n_objects
pset.use_scale_instance = True
pset.frame_start = 1
pset.frame_end = 1
pset.lifetime = 50
pset.emit_from = "FACE"
pset.physics_type = "NO"
pset.render_type = "OBJECT"
pset.instance_object = sphere
pset.particle_size = 0.2
# pset.size_random = 0.5

emitter = bpy.data.objects["Emitter"]
degp = bpy.context.evaluated_depsgraph_get()
particle_systems = emitter.evaluated_get(degp).particle_systems
psys = particle_systems[0]

# psys = emitter.particle_systems[0]
# bpy.context.view_layer.update()
# load obj for rock type 16
time_copy = []
print(f" {len(psys.particles)} particles")

bpy.context.view_layer.update()
start = time.time()
# bpy.ops.particle.particle_edit_toggle()
size_list = [random.uniform(0.1, 3.0) for i in range(len(psys.particles))]
psys.particles.foreach_set("size", size_list)
psys.settings.display_size = 1.0
bpy.context.view_layer.update()
# psys.particles.foreach_set("size", size_list)

recovered_size_list = np.empty(len(psys.particles))
psys.particles.foreach_get("size", recovered_size_list)

print(f"Size list: {size_list}, Recovered size list: {recovered_size_list}")
time_copy = time.time() - start
print(
    f"Total time to copy {n_objects} objects: {dth(time_copy)}, "
    f"average time to copy an object: {dth(time_copy/n_objects)}"
)
bpy.context.view_layer.update()


def particleSetter(scene, degp):
    emitter = bpy.data.objects["Emitter"]
    degp = bpy.context.evaluated_depsgraph_get()
    particle_systems = emitter.evaluated_get(degp).particle_systems
    psys = particle_systems[0]

    size_list = [random.uniform(0.3, 3.0) for i in range(len(psys.particles))]

    psys.particles.foreach_set("size", size_list)


# bpy.app.handlers.frame_change_post.clear()
# bpy.app.handlers.frame_change_post.append(particleSetter)

# for p in psys.particles:
# Get the emitter object
# Loop through all particles and modify their size
# copied_obj = p.instance_object
# bpy.context.collection.objects.link(copied_obj)
# move to random location
# copied_obj.location = (
#     random.uniform(-10, 10),
#     random.uniform(-10, 10),
#     random.uniform(-10, 10),
# )
# scale randomly
# p.size = random.uniform(0.1, 20)
# # copied_obj.scale = (
# #     random.uniform(0.1, 1),
# #     random.uniform(0.1, 1),
# #     random.uniform(0.1, 1),
# # )

# # random rotation
# # copied_obj.rotation_euler = (
# #     random.uniform(0, 3.14),
# #     random.uniform(0, 3.14),
# #     random.uniform(0, 3.14),
# # )
# end = time.time()
# time_copy.append(end - start)

# print(f"Total time to copy {n_objects} objects: {dth(sum(time_copy))},
# average time to copy an object: {dth(np.mean(time_copy))}")

# plot the time taken to copy the objects

fig, ax = plt.subplots()
ax.plot(time_copy)
plt.xlabel("Object index")
plt.ylabel("Time to copy object")
plt.title("Time to copy objects")
# plt.show()

# emitter = bpy.data.objects['Emitter']
# degp = bpy.context.evaluated_depsgraph_get()
# particle_systems = emitter.evaluated_get(degp).particle_systems

# position the camera to see all the cubes
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.select_by_type(type="MESH")
# bpy.ops.view3d.camera_to_view_selected()


bpy.context.scene.render.filepath = "random_rocks_particle.png"
# bpy.context.view_layer.update()
bpy.ops.render.render(write_still=True)

# save the file
# bpy.ops.wm.save_as_mainfile(filepath="copy_objects_copy_particle.blend")
