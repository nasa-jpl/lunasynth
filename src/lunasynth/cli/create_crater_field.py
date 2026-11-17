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
import lunasynth.craters as craters
import lunasynth.terrain_enhancement as terrain_enhancement


def main():
    parser = argparse.ArgumentParser(
        description="Generate the visible craters of a lunar surface of a given age and save them to a CSV file."
    )
    parser.add_argument("--size_x", type=float, required=True, help="Size of the area in the x direction, m.")
    parser.add_argument("--size_y", type=float, required=True, help="Size of the area in the y direction, m.")
    parser.add_argument("--age", type=float, default=3.9, help="Age of the surface, Gyr (default: 3.9).")
    parser.add_argument(
        "--terrain",
        choices=sorted(craters.DIFFUSIVITY),
        default="highland",
        help="Terrain type, sets the degradation rate and regolith thickness (default: highland).",
    )
    parser.add_argument("--d_min", type=float, default=2.0, help="Smallest fresh crater diameter, m (default: 2).")
    parser.add_argument("--d_max", type=float, default=50.0, help="Largest fresh crater diameter, m (default: 50).")
    parser.add_argument(
        "--morphology",
        choices=("auto", *craters.MORPHOLOGIES),
        default="auto",
        help="Crater morphology, or auto to select it from the regolith thickness (default: auto).",
    )
    parser.add_argument("--regolith_thickness", type=float, default=None, help="Median regolith thickness, m.")
    parser.add_argument(
        "--chronology", choices=sorted(craters.CHRONOLOGY), default="neukum2001", help="Lunar chronology function."
    )
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
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.size_x <= 0 or args.size_y <= 0:
        parser.error(f"size_x and size_y must be greater than 0. Got {args.size_x} and {args.size_y}.")
    if not 0 < args.d_min < args.d_max:
        parser.error(f"Expected 0 < d_min < d_max. Got {args.d_min} and {args.d_max}.")
    if not 0 < args.age <= 4.5:
        parser.error(f"age must be between 0 and 4.5 Gyr. Got {args.age}.")

    crater_field = terrain_enhancement.CraterField()
    crater_field.generate(
        size_x=args.size_x,
        size_y=args.size_y,
        surface_age_ga=args.age,
        terrain=args.terrain,
        d_min=args.d_min,
        d_max=args.d_max,
        morphology=args.morphology,
        regolith_thickness=args.regolith_thickness,
        chronology=args.chronology,
        seed=args.seed,
        x_init=-args.size_x / 2,
        y_init=-args.size_y / 2,
    )
    crater_field.save(args.output)


if __name__ == "__main__":
    main()
