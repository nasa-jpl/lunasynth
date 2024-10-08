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
from pathlib import Path

import argcomplete
import lunasynth.blender_helper as bh
import lunasynth.dem_tools as dem_tools
import lunasynth.image_tools as image_tools


def main() -> None:
    """Render a Geotiff file."""
    parser = argparse.ArgumentParser(description="Render a Geotiff file.")
    parser.add_argument("mesh_file", type=str, help="The mesh file to import.")
    parser.add_argument(
        "--import-mode",
        type=str,
        default=None,
        help="The import mode for the mesh. Used for tiff files.",
    )
    parser.add_argument(
        "--sun-hour",
        type=float,
        nargs="+",
        default=[0],
        help="Normalized sun hour: -1 is sunrise, 0 is noon, 1 is sunset",
    )
    parser.add_argument(
        "--sun-season",
        type=float,
        nargs="+",
        default=[0],
        help="Normalized sun season: -1 is winter, 0 is spring, 1 is summer",
    )
    parser.add_argument(
        "--save-blender-file",
        action="store_true",
        help="The output filename for the Blender file.",
    )
    parser.add_argument(
        "--overlay",
        action="store_true",
        help="Overlay north location on the rendered image.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="The output filename for the rendered image.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Setup the moon scene the first time this script is run. CAUTION: This will overwrite the current scene in Blender.
    bh.setup_moon_scene()
    bh.load_mesh(mesh_file=args.mesh_file, import_mode=args.import_mode)
    bh.fit_camera_to_mesh("Terrain")
    moon_dem = dem_tools.DEM(args.mesh_file)
    lat, long = moon_dem.get_latlong()
    print(f"latitude {math.degrees(lat):.2f}, sun_hour {args.sun_hour}, sun_season {args.sun_season}")

    case_index = 0
    num_cases = len(args.sun_hour) * len(args.sun_season)
    for sun_hour in args.sun_hour:
        for sun_season in args.sun_season:
            sun_hour = float(sun_hour)
            sun_season = float(sun_season)
            case_index += 1
            print(f"Rendering case {case_index}/{num_cases}: sun_hour {sun_hour}, sun_season {sun_season}")
            elevation, local_azimuth = dem_tools.compute_sun_elevation_azimuth(
                latitude=lat, sun_hour_normalized=sun_hour, sun_season=sun_season
            )
            if local_azimuth is None:
                print("Sun is below horizon, skipping")
                local_azimuth = -math.pi

            azimuth = local_azimuth - long
            print(
                f"elevation {math.degrees(elevation):.2f}, azimuth {math.degrees(azimuth):.2f}, "
                f"local_azimuth {math.degrees(local_azimuth):.2f}, long {math.degrees(long):.2f}"
            )
            bh.set_sun_orientation(elevation, azimuth)

            if args.output is None:
                output_render_filename = args.mesh_file.replace(".tif", "_rendered.png")
                if len(args.sun_hour) > 1 or len(args.sun_season) > 1:
                    output_render_filename = output_render_filename.replace(
                        ".png", f"_sun_hour_{sun_hour}_sun_season_{sun_season}.png"
                    )
            else:
                output_render_filename = args.output

            bh.render_blender(output_filename=output_render_filename)
            print(f"Rendered to {output_render_filename}")

            if args.save_blender_file:
                output_blender_filename = args.mesh_file.replace(".tif", "_rendered.blend")
                bh.save_blender_file(output_filename=output_blender_filename)

            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if args.overlay:
                image_tools.overlay_images(
                    output_render_filename,
                    project_root / "assets/icons8-arrow-100.png",
                    output_render_filename,
                    scale=0.16,
                    rotation=azimuth,
                    margin=0.8,
                )
                image_tools.overlay_images(
                    output_render_filename,
                    project_root / "assets/icons8-north-96.png",
                    output_render_filename,
                    scale=0.12,
                    rotation=-long,
                    margin=0.8,
                )


if __name__ == "__main__":
    main()
