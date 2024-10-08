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
import os

import argcomplete
import lunasynth.blender_helper as blender_helper
import lunasynth.terrain_enhancement as terrain_enhancement


def main():
    parser = argparse.ArgumentParser(description="Load rocks from a CSV file.")
    parser.add_argument("--blend-file", type=str, default=None, help="Path to a .blend file.")
    parser.add_argument("--mesh-file", type=str, default=None, help="Path to a mesh file")
    parser.add_argument(
        "--rock-field-file",
        type=str,
        help="Path to the CSV file containing rock data.",
    )
    parser.add_argument(
        "--output-blend-file",
        default=None,
        help="The output directory, overwrites the config file.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.blend_file is None and args.mesh_file is None:
        print("Please provide a blend file or a mesh file.")
        return

    # Check arguments
    if args.blend_file is None and not os.path.exists(args.blend_file):
        print("Provided Blend file not found. Please check the path.")
        return

    if not os.path.exists(args.rock_field_file):
        print("rock_field_file CSV file not found. Please check the path.")
        return

    # Load rocks
    terrain_enhancement.RockField().load_rocks_blender(
        args.blend_file,
        args.mesh_file,
        args.rock_field_file,
        rock_source="assets/rocks/earth_scanned/",
    )

    if args.output_blend_file is not None:
        output_blender_file = args.output_blend_file
    else:
        output_blender_file = args.blend_file.replace(".blend", "_rocks.blend")
    blender_helper.save_blender_file(output_blender_file)


if __name__ == "__main__":
    main()
