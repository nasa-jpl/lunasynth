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

# PYTHON_ARGCOMPLETE_OK
import argparse
import math
import random

import argcomplete
import enlighten
import lunasynth.blender_helper as bh


def main() -> None:
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("blend_file", type=str, help="The Blender file to render.")
    parser.add_argument("--cases", type=int, default=10, help="The number of cases to render.")
    parser.add_argument("--min-pitch", type=float, default=-80, help="The minimum pitch angle.")
    parser.add_argument("--max-pitch", type=float, default=20, help="The maximum pitch angle.")
    parser.add_argument("--min-z", type=float, default=2, help="The minimum z position.")
    parser.add_argument("--max-z", type=float, default=30, help="The maximum z position.")
    parser.add_argument(
        "--min-sun-elevation",
        type=float,
        default=6,
        help="The minimum sun elevation angle.",
    )
    parser.add_argument(
        "--max-sun-elevation",
        type=float,
        default=30,
        help="The maximum sun elevation angle.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    bh.load_blender_file(args.blend_file)
    camera_x = 0
    camera_y = 0
    params_used = {
        "blend_file": args.blend_file,
        "fixed_params": {
            "camera_x": camera_x,
            "camera_y": camera_y,
        },
        "generation_params": {
            "min_pitch": args.min_pitch,
            "max_pitch": args.max_pitch,
            "min_z": args.min_z,
            "max_z": args.max_z,
            "min_sun_elevation": args.min_sun_elevation,
            "max_sun_elevation": args.max_sun_elevation,
        },
        "cases": args.cases,
        "cases_data": [],
    }
    manager = enlighten.get_manager()
    # status_bar = manager.status_bar(
    #     status_format=f"Processing {args.blend_file}",
    #     color="bold_underline_bright_white_on_lightslategray",
    #     justify=enlighten.Justify.LEFT,
    # )
    pbar = manager.counter(total=args.cases, desc="Rendering ", unit="cases")
    data_bar = manager.status_bar(
        autorefresh=True,
    )

    for i in range(args.cases):
        camera_pitch = random.uniform(args.min_pitch, args.max_pitch)
        camera_azimuth = random.uniform(0, 360)
        camera_z = random.uniform(args.min_z, args.max_z)
        sun_elevation = random.uniform(args.min_sun_elevation, args.max_sun_elevation)
        sun_azimuth = random.uniform(0, 360)
        rgb_filename = args.blend_file.replace(".blend", f"_{i}.png")
        params_used["cases_data"].append(
            {
                "case": i,
                "camera_pitch": camera_pitch,
                "camera_azimuth": camera_azimuth,
                "z": camera_z,
                "sun_elevation": sun_elevation,
                "sun_azimuth": sun_azimuth,
                "rgb_filename": rgb_filename,
            }
        )
        pbar.refresh()
        data_bar.update(
            f" Case {i}: using pitch: {camera_pitch}, azimuth: {camera_azimuth}, z: {camera_z}, "
            f"sun_elevation: {sun_elevation}, sun_azimuth: {sun_azimuth}"
        )
        data_bar.refresh()

        bh.set_camera_pose(
            camera_x,
            camera_y,
            camera_z,
            math.radians(camera_pitch),
            math.radians(camera_azimuth),
        )
        bh.set_sun_orientation(math.radians(sun_elevation), math.radians(sun_azimuth))
        bh.render_blender(
            output_filename=rgb_filename,
        )
        pbar.update()
    pbar.close()
    manager.stop()

    # save the parameters used in json
    import json

    with open(args.blend_file.replace(".blend", "_params.json"), "w") as f:
        json.dump(params_used, f)


if __name__ == "__main__":
    main()
