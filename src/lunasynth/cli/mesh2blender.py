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
from pathlib import Path

import argcomplete
import lunasynth.blender_helper as bh


def main():
    """Import a mesh into Blender"""
    parser = argparse.ArgumentParser(description="Import a mesh into Blender.")
    parser.add_argument("mesh_file", type=str, help="The mesh file to import.")
    parser.add_argument(
        "--import-mode",
        type=str,
        default=None,
        help="The import mode for the mesh. Used for tiff files.",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=1.0,
        help="Increase mesh resolution factor.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="The output filename for the Blender file.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    bh.load_mesh(mesh_file=args.mesh_file, import_mode=args.import_mode, zoom_factor=args.zoom)

    if args.output is None:
        output_blender_filename = Path(args.mesh_file).stem + ".blend"
    else:
        output_blender_filename = args.output
    bh.save_blender_file(output_filename=output_blender_filename)


if __name__ == "__main__":
    main()
