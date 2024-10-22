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
import lunasynth.terrain_enhancement as terrain_enhancement


def main():
    parser = argparse.ArgumentParser(description="Generate a crater field.")
    parser.add_argument("--CFA", type=float, help="The CFA of the crater field.")
    parser.add_argument("--size_x", type=float, help="The size of the crater field in the x direction.")
    parser.add_argument("--size_y", type=float, help="The size of the crater field in the y direction.")
    parser.add_argument("--h_min", type=float, help="The minimum height of the craters.")
    parser.add_argument("--h_max", type=float, help="The maximum height of the craters.")
    parser.add_argument(
        "--seed",
        type=int,
        required=False,
        default=None,
        help="The seed to use for the random number generator.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="moon_crater_field.csv",
        help="The output file to save the crater field to.",
    )
    parser.add_argument("--plot", action="store_true", help="Plot the crater field.")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Check args
    if args.CFA < 0 or args.CFA > 100:
        print("Error: CFA must be between 0 and 100.")
        exit(1)

    if args.size_x <= 0:
        print(f"Error: size_x must be greater than 0. Got {args.size_x}.")
        exit(1)
    if args.size_y <= 0:
        print(f"Error: size_y must be greater than 0. Got {args.size_y}.")
        exit(1)
    if args.h_min < 0:
        print(f"Error: h_min must be greater than or equal to 0. Got {args.h_min}.")
        exit(1)

    crater_field = terrain_enhancement.CraterField()
    crater_field.generate(
        args.CFA,
        args.size_x,
        args.size_y,
        args.h_min,
        args.h_max,
        x_init=-args.size_x / 2,
        y_init=-args.size_y / 2,
    )
    crater_field.save(args.output)


if __name__ == "__main__":
    main()
