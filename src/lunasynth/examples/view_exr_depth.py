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

import lunasynth.image_tools as image_tools

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Display an EXR file.")
    parser.add_argument("file_path", type=str, help="Path to the EXR file")
    args = parser.parse_args()

    img, channels = image_tools.load_exr(args.file_path)
    image_tools.display_exr(img, channels)
