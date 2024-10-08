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

import argcomplete
import lunasynth.blender_helper as bh


def main():
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("--blend_file", type=str, required=True, help="The Blender file to render.")
    parser.add_argument("--output_file", type=str, default=None, help="The output file.")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    bh.load_blender_file(args.blend_file)
    used_pass_index = bh.setup_pass_index(
        # pass_index_function=lambda x: 2 if x == "Terrain" else 1
    )
    print(f"Used pass index: {used_pass_index}")
    if args.output_file is None:
        output_file = args.blend_file.replace(".blend", "_pass_index.blend")
    else:
        output_file = args.output_file
    bh.save_blender_file(output_filename=output_file)


if __name__ == "__main__":
    main()
