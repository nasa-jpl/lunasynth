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
import lunasynth.image_tools as image_tools


def exr2hdf(input_path, output_path):
    img, channels = image_tools.load_exr(input_path)
    image_tools.save_to_hdf5(img, channels, output_path)


def main():
    parser = argparse.ArgumentParser(description="Convert an EXR file to an HDF5 file.")
    parser.add_argument("input_path", type=str, help="The input EXR file to use")
    parser.add_argument("output_path", type=str, help="The output HDF5 file to use")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    exr2hdf(args.input_path, args.output_path)


if __name__ == "__main__":
    main()
