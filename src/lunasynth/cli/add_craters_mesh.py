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
from pathlib import Path

import argcomplete
import lunasynth.blender_helper as blender_helper
import lunasynth.terrain_enhancement as terrain_enhancement


def main():
    parser = argparse.ArgumentParser(description="Load craters from a CSV file.")
    parser.add_argument("--mesh-file", type=str, required=True, help="Path to a mesh file")
    parser.add_argument(
        "--crater-field-file",
        type=str,
        help="Path to the CSV file containing crater data.",
    )
    parser.add_argument(
        "--output-blend-file",
        default=None,
        help="The output directory, overwrites the config file.",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=1.0,
        help="Increase mesh resolution factor.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Check arguments
    if not os.path.exists(args.crater_field_file):
        print("crater_field_file CSV file not found. Please check the path.")
        return

    # Load craters
    crater_field = terrain_enhancement.CraterField()
    crater_field.load_crater_blender(args.mesh_file, args.crater_field_file, args.zoom)

    if args.output_blend_file is not None:
        output_blender_file = args.output_blend_file
    else:
        # replace extension with .blend using Pathlib
        output_blender_file = Path(args.mesh_file).with_suffix(".blend")
    blender_helper.save_blender_file(output_blender_file)


if __name__ == "__main__":
    main()
