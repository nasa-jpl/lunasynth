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
import lunasynth.blender_helper as bh
import yaml
from lunasynth.configuration_manager import CaseManager, RenderingManager


def main():
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("--blend_file", type=str, help="The blender file to use")
    parser.add_argument("--config", type=str, help="The configuration file to use")
    parser.add_argument(
        "--cases",
        default=None,
        help="The number of cases to render, overwrites the config file.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="The output directory, overwrites the config file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not render, only generate the cases.",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Visualize the cases in blender.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # check if the blend file exists
    if not Path(args.blend_file).is_file():
        msg = f"Blend file {args.blend_file} not found."
        raise FileNotFoundError(msg)

    # check if the config file exists
    if not Path(args.config).is_file():
        msg = f"Config file {args.config} not found."
        raise FileNotFoundError(msg)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    if args.cases is not None:
        config["cases"] = int(args.cases)

    if "output_dir" not in config:
        # add current time to output dir
        config["output_dir"] = str(Path("render_jobs") / Path(str(Path(args.config).stem)))

    if args.output_dir is not None:
        config["output_dir"] = args.output_dir

    cases_dict = {
        "cases_config_file": args.config,
        "cases_config": config,
        "blend_file": args.blend_file,
        "cases_list": [],
    }

    bh.load_blender_file(args.blend_file)

    rendering_manager = RenderingManager({})
    cases_dict["cases_list"] = rendering_manager.generate_rendering_cases(
        config["render_distributions"], n_cases=config["cases"], camera_type="PERSP"
    )

    if args.visualize:
        bh.add_cases_visalization(cases_dict["cases_list"], connect_cases=False)
        output_blend_file = output_blend_file = f"cases_{str(Path(args.config).stem)}.blend"
        bh.save_blender_file(output_blend_file)

        # call blender to visualize the cases
        os.system(f"blender {output_blend_file}")
        return

    if not args.dry_run:
        rendering_manager.setup_rendering(config, output_dir=config["output_dir"])
        rendering_manager.n_rendering_cases = len(cases_dict["cases_list"])
        rendering_manager.n_terrain = 1
        rendering_manager.n_meshes = 1
        rendering_manager.planned_cases = len(cases_dict["cases_list"])
        rendering_manager.run_rendering_campaign(cases_dict, output_case_dir=config["output_dir"])

    CaseManager().save_cases_description(cases_dict)


if __name__ == "__main__":
    main()
