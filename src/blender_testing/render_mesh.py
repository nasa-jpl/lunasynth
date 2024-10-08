#!/usr/bin/env python3
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

#  usage: render_mesh.py mesh_file elevation_in_degrees [-h] [--output OUTPUT] [--save-blender-file]
#  you need to install bpy, pip install bpy, or using your favorite virtual environment manager


def render_mesh(
    mesh_file,
    output_file=None,
    sun_elevation=0.2,
    save_blender_file=False,
) -> None:
    import math
    from pathlib import Path

    import bpy

    # check if the file is a mesh
    if not Path(mesh_file).is_file():
        msg = f"File {mesh_file} not found"
        raise ValueError(msg)

    if mesh_file.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=mesh_file)
    elif mesh_file.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=mesh_file)
    else:
        msg = "Unsupported file format"
        raise ValueError(msg)

    bpy.context.view_layer.objects.active = bpy.context.object
    active_mesh = bpy.context.active_object
    bpy.ops.object.shade_smooth()

    # add new material to mesh. set albedo to 0.14
    mat = bpy.data.materials.new(name="DEM_MAT")
    mat.diffuse_color = (0.14, 0.14, 0.14, 1)
    active_mesh.data.materials.append(mat)

    bpy.context.scene.camera.data.type = "ORTHO"
    bpy.context.scene.camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024
    bpy.context.scene.camera.data.clip_end = 100000
    bpy.ops.view3d.camera_to_view_selected()

    # set cycles
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.device = "GPU"
    bpy.context.scene.cycles.samples = 2048

    # Add sun
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="LIGHT")
    bpy.ops.object.delete()
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 0))
    sun = bpy.context.object
    sun.data.energy = 10
    sun.data.angle = 0.5 * math.pi / 180
    sun.data.use_shadow = True
    sun.location = (0, 0, 0)
    sun.rotation_euler = (
        math.pi / 2 - math.radians(sun_elevation),
        0,
        0,
    )
    # use the same file name as the mesh file, but with .png extension
    bpy.context.scene.render.filepath = output_file if output_file else str(Path(mesh_file).with_suffix(".png"))
    bpy.ops.render.render(write_still=True)

    if save_blender_file:
        for a in bpy.context.screen.areas:
            if a.type == "VIEW_3D":
                for s in a.spaces:
                    if s.type == "VIEW_3D":
                        s.clip_end = 10000
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(mesh_file).with_suffix(".blend")))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render given file with blender")
    parser.add_argument("file", help="file to render")
    parser.add_argument("sun_elevation", type=float, help="sun elevation in degrees")
    parser.add_argument("--output", help="output file", default=None)
    parser.add_argument(
        "--save-blender-file",
        action="store_true",
        help="Save the Blender file after rendering",
    )
    args = parser.parse_args()
    render_mesh(
        args.file,
        sun_elevation=args.sun_elevation,
        output_file=args.output,
        save_blender_file=args.save_blender_file,
    )
