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

#  usage: render_sun_camera.py [-h] [--output OUTPUT] file camera_x camera_y camera_z sun_elevation sun_azimuth
#  you need to install bpy: pip install bpy


def render_sun_camera(
    blender_file,
    output_file=None,
    camera_x=0,
    camera_y=0,
    camera_z=10,
    sun_elevation_degrees=30,
    sun_azimuth_degrees=30,
    save_blender_file=False,
):
    import math

    import bpy

    bpy.ops.wm.open_mainfile(filepath=blender_file)

    # Set camera
    bpy.context.scene.camera.location = (camera_x, camera_y, camera_z)
    bpy.context.scene.camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera.data.type = "ORTHO"

    # remove all lights
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="LIGHT")
    bpy.ops.object.delete()

    # Add sun
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 0))
    sun = bpy.context.object
    sun.data.energy = 10
    sun.data.angle = 0.5 * math.pi / 180
    sun.data.use_shadow = True
    sun.location = (0, 0, 0)
    sun.rotation_euler = (
        math.pi / 2 - math.radians(sun_elevation_degrees),
        0,
        math.radians(sun_azimuth_degrees),
    )
    bpy.context.scene.render.filepath = output_file if output_file else blender_file.replace(".blend", ".png")
    bpy.ops.render.render(write_still=True)

    if save_blender_file:
        bpy.ops.wm.save_as_mainfile(filepath=blender_file.replace(".blend", "_rendered.blend"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render given file with blender")
    parser.add_argument("file", help="file to render")
    parser.add_argument("camera_x", type=float, help="camera x position")
    parser.add_argument("camera_y", type=float, help="camera y position")
    parser.add_argument("camera_z", type=float, help="camera z position")
    parser.add_argument("sun_elevation_degrees", type=float, help="sun elevation in degrees")
    parser.add_argument("sun_azimuth_degrees", type=float, help="sun azimuth in degrees")
    parser.add_argument("--output", help="output file", default=None)
    parser.add_argument(
        "--save-blender-file",
        action="store_true",
        help="Save the Blender file after rendering",
    )
    args = parser.parse_args()
    render_sun_camera(
        args.file,
        camera_x=args.camera_x,
        camera_y=args.camera_y,
        camera_z=args.camera_z,
        sun_elevation_degrees=args.sun_elevation_degrees,
        sun_azimuth_degrees=args.sun_azimuth_degrees,
        output_file=args.output,
        save_blender_file=args.save_blender_file,
    )
