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
    """Render a Blender file.
    Usage:
    python render_blendfile.py path/to/file.blend

    This will render the file and save the output as file.png.

    You can also save the Blender file after rendering:
    python render_blendfile.py path/to/file.blend --save-blender-file

    You can also render a depth map or a segmentation map:
    python render_blendfile.py path/to/file.blend --depth
    python render_blendfile.py path/to/file.blend --segmentation
    """
    parser = argparse.ArgumentParser(description="Render a file.")
    parser.add_argument("blend_file", type=str, help="The Blender file to render.")
    parser.add_argument(
        "--save-blender-file",
        action="store_true",
        help="Save the Blender file after rendering",
    )
    parser.add_argument(
        "--depth",
        action="store_true",
        help="Setup and render depth map.",
    )
    parser.add_argument(
        "--render-config",
        type=str,
        default=None,
        help="The render configuration file.",
    )
    parser.add_argument(
        "--segmentation",
        action="store_true",
        help="Setup and render segmentation map.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="The output directory for the rendered files.",
    )
    parser.add_argument(
        "--output-blend-file",
        type=str,
        default=None,
        help="The output filename for the Blender file.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    bh.load_blender_file(args.blend_file)

    if args.render_config is not None:
        bh.setup_render_config(args.render_config)

    if args.segmentation:
        bh.setup_segmentation_rendering()

    if args.depth:
        bh.setup_depth_rendering()

    if args.output_dir is None:
        args.output_dir = Path(args.blend_file).parent

    output_filename = str(Path(args.output_dir) / Path(args.blend_file).stem) + ".png"
    bh.render_blender(output_filename=output_filename)
    if args.save_blender_file:
        if args.output_blend_file is None:
            print(f"output filename: {output_filename}")
            print(f"Saving Blender file as {output_filename.replace('.png', '_render.blend')}")
            output_blender_filename = output_filename.replace(".png", "_render.blend")
        else:
            output_blender_filename = args.output_blend_file
        bh.save_blender_file(output_filename=output_blender_filename)


if __name__ == "__main__":
    main()
