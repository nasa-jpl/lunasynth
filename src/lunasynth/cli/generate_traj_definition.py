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

import argcomplete
import pandas as pd
import yaml


def main():
    parser = argparse.ArgumentParser(description="Combine a trajectory with a scene.")
    parser.add_argument("--trajectory", type=str, required=True, help="The trajectory file to use")
    parser.add_argument("--scene", type=str, required=True, help="The scene file to use")
    parser.add_argument(
        "--output",
        type=str,
        default="trajectory_scene.json",
        help="The output filename.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    with open(args.scene) as f:
        scene = yaml.safe_load(f)

    # read trajectory from csv
    trajectory = pd.read_csv(args.trajectory)
    trajectory = trajectory.to_dict(orient="records")

    # combine scene with trajectory, save as json
    with open(args.output, "w") as f:
        json.dump({"scene": scene, "trajectory": trajectory}, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    main()
