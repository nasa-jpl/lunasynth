#!/usr/bin/env python
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
import math

import lunasynth.blender_helper as bh


def main():
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("blend_file", type=str, help="The Blender file to render.")
    args = parser.parse_args()

    bh.load_blender_file(args.blend_file)

    for angle in range(-80, 20, 10):
        bh.set_camera_pose(20, -20, 20, math.radians(angle), math.radians(40))
        bh.render_blender(output_filename=args.blend_file.replace(".blend", f"_pitch_{angle}.png"))

    for pos in range(2, 30, 4):
        bh.set_camera_pose(20, -20, pos, math.radians(-40), math.radians(40))
        bh.render_blender(output_filename=args.blend_file.replace(".blend", f"_z_{pos}.png"))


if __name__ == "__main__":
    main()
