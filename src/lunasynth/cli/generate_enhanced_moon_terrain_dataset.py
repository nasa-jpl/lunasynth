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
import lunasynth.configuration_manager as configuration_manager
from lunasynth.config_loader import ConfigLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Render file from different camera angles.")
    parser.add_argument("--dataset-config", type=str, required=True, help="Dataset configuration file.")
    parser.add_argument(
        "--set",
        nargs="*",
        default=[],
        help="Set any value in the format key=value,"
        "where key is a key in the config file and it can be nested using dots.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    dataset_config = ConfigLoader(args.dataset_config, args_updates=args.set).config

    dataset_rendering_manager = configuration_manager.RenderingManager(
        dataset_config=dataset_config,
        default_dataset_name=str(Path(args.dataset_config).stem),
    )
    dataset_rendering_manager.run_dataset_generation()


if __name__ == "__main__":
    main()
