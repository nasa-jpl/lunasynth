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

"""Download public Apollo image data from NASA's Apollo Image Gallery website."""

import argparse
import json
import os
import re

import humanize
import requests
from tqdm import tqdm


def download_file(url, fname):
    # check if the file already exists
    if os.path.exists(fname):
        print(f"File {fname} already exists. Skipping download.")
        return 0, False
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        total = int(response.headers.get("content-length", 0))
        with open(fname, "wb") as file, tqdm(
            desc=fname,
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
            position=1,
            leave=False,
        ) as bar:
            for data in response.iter_content(chunk_size=8192):
                size = file.write(data)
                bar.update(size)
        # print(f"Downloaded {url} to {fname}")
        return total, True
    else:
        print(f"Failed to download {url} to {fname}. Status code: {response.status_code}")
        return 0, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_file", help="Path to the metadata file")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Do not download the images")
    parser.add_argument(
        "--max-images",
        type=int,
        default=-1,
        help="Maximum number of images to download",
    )
    args = parser.parse_args()

    # Load the metadata
    with open(args.metadata_file) as f:
        metadata = json.load(f)

    # fields required for download
    required_fields = ["Image Source", "Image Alt", "Hi Resolution Image(s)"]

    # fields to exclude if it has a certain value
    excluded_criteria = {
        "Quality": "Poor",
    }

    # fields required for download with a certain value
    download_criteria = {
        "Image_Type": "Surface",
    }

    # Download the images
    print("Downloading images...")
    selected_images = 0
    downloaded_images = 0
    acc_file_size = 0
    for image in tqdm(metadata, desc="Images", position=0, leave=True):
        if (
            all(field in image for field in required_fields)
            and all(image[field] == download_criteria[field] for field in download_criteria)
            and not any(image[field] for field in excluded_criteria if field in image)
        ):
            selected_images += 1
            if "Hi Resolution Image(s)" in image:
                image_url = image["Hi Resolution Image(s)"]
            else:
                image_url = image["Image Source"]
            image_name = image["Image Alt"]
            image_name = re.sub(r"-", "_", image_name)  # replace hyphens with underscores
            image_name = re.sub(r"\s+", "_", image_name)  # replace spaces with underscores
            image_name = os.path.join(args.output_dir, f"{image_name}.jpg")

            if args.dry_run:
                print(f"Would download {image_url} to {image_name}")
            else:
                file_size, result = download_file(image_url, image_name)
                if result:
                    downloaded_images += 1
                acc_file_size += file_size
            if selected_images == args.max_images:
                break
    print(
        f"Downloaded {downloaded_images} images, "
        f"out of {selected_images} selected images [{len(metadata)} total images]"
    )
    if acc_file_size > 0:
        print(f"Total size of downloaded images: {humanize.naturalsize(acc_file_size)}")


if __name__ == "__main__":
    main()
