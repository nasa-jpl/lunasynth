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
from datetime import datetime
from pathlib import Path

import argcomplete
import lunasynth.blender_helper as bh
import yaml
from lunasynth.configuration_manager import CaseManager, RenderingManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("blend_file", type=str, help="The configuration file to use")
    parser.add_argument("--config", type=str, help="The configuration file to use")
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
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    if "output_dir" not in config:
        # add current time to output dir
        config["output_dir"] = str(
            Path("render_jobs") / Path(str(Path(args.config).stem) + "_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        )

    if args.output_dir is not None:
        config["output_dir"] = args.output_dir

    config["depth_output"] = config["scene"]["depth_output"]
    config["segmentation_output"] = config["scene"]["segmentation_output"]

    cases_dict = {
        "cases_config_file": args.config,
        "cases_config": config,
        "blend_file": args.blend_file,
        "cases_list": [],
    }
    rendering_manager = RenderingManager({})
    cases_dict["cases_list"] = rendering_manager.generate_traj_cases(config)

    if not args.dry_run:
        bh.load_blender_file(args.blend_file)
        rendering_manager.setup_rendering(config, output_dir=config["output_dir"])
        rendering_manager.n_rendering_cases = len(cases_dict["cases_list"])
        rendering_manager.n_terrain = 1
        rendering_manager.n_meshes = 1
        rendering_manager.planned_cases = len(cases_dict["cases_list"])
        rendering_manager.run_rendering_campaign(cases_dict, output_case_dir=config["output_dir"])

    CaseManager().save_cases_description(cases_dict)


if __name__ == "__main__":
    main()
