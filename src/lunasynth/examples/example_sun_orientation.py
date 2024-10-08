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
    parser = argparse.ArgumentParser(description="Render file from different sun angles.")
    parser.add_argument("blend_file", type=str, help="The Blender file to render.")
    args = parser.parse_args()

    bh.load_blender_file(args.blend_file)

    for angle in range(10, 60, 10):
        bh.set_sun_orientation(math.radians(angle), 0)
        bh.render_blender(output_filename=args.blend_file.replace(".blend", f"_{angle}deg_elevation.png"))

    for angle in range(0, 360, 10):
        bh.set_sun_orientation(math.radians(30.0), math.radians(angle))
        bh.render_blender(output_filename=args.blend_file.replace(".blend", f"_{angle}deg_azimuth.png"))


if __name__ == "__main__":
    main()
