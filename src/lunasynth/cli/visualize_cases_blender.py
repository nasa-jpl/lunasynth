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
import json
from pathlib import Path

import argcomplete
import lunasynth.blender_helper as blender_helper


def main():
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("--blend_file", type=str, default=None, help="The configuration file to use")
    parser.add_argument("--config", required=True, type=str, help="The configuration file to use")
    parser.add_argument(
        "--output-blend-file",
        default=None,
        help="The output directory, overwrites the config file.",
    )
    parser.add_argument(
        "--connect",
        action="store_true",
        help="Connect the cases with a line",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    config_filename = args.config

    with open(args.config) as f:
        config = json.load(f)

    if args.output_blend_file is not None:
        output_blend_file = args.output_blend_file
    else:
        if args.blend_file is not None:
            output_blend_file = args.blend_file.replace(".blend", f"_cases_{config_filename}.blend")
        else:
            output_blend_file = f"cases_{str(Path(config_filename).stem)}.blend"

    if args.blend_file is not None:
        blender_helper.load_blender_file(args.blend_file)
    else:
        # delete all objects
        blender_helper.delete_all_objects()
    blender_helper.add_cases_visalization(config["cases_list"], connect_cases=args.connect)

    blender_helper.save_blender_file(output_blend_file)


if __name__ == "__main__":
    main()
