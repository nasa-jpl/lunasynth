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

import lunasynth.image_tools as image_tools


def main():
    parser = argparse.ArgumentParser(description="Combine multiple camera frames to a video.")
    parser.add_argument("data_dir", type=str, help="The directory containing the camera frames.")
    parser.add_argument("--prefixes", nargs="+", type=str, help="The prefixes of the camera frames.")
    parser.add_argument("--output_file", type=str, help="The output file to write the video to.")
    parser.add_argument(
        "--frame_image_size",
        nargs=2,
        type=int,
        default=(640, 480),
        help="The size of the frames in the video.",
    )
    parser.add_argument("--fps", type=int, default=30, help="The frames per second of the video.")
    parser.add_argument("-s", "--start", type=int, default=0, help="The frame to start from.")
    parser.add_argument("-e", "--end", type=int, default=-1, help="The frame to end at.")
    args = parser.parse_args()

    # Check args
    if os.path.isdir(args.data_dir) is False:
        print("Data directory does not exist.")
        exit(1)

    if args.prefixes is None or len(args.prefixes) == 0:
        print("No prefixes provided.")
        exit(1)

    if args.fps <= 0:
        print("FPS must be a positive number.")
        exit(1)

    if args.frame_image_size[0] <= 0 or args.frame_image_size[1] <= 0:
        print("Frame image size must be positive.")
        exit(1)

    if args.start < 0:
        print("Start frame must be positive.")
        exit(1)

    image_tools.create_multiview_video(
        args.data_dir,
        args.prefixes,
        args.output_file,
        args.frame_image_size,
        args.fps,
        args.start,
        args.end,
    )


if __name__ == "__main__":
    main()
