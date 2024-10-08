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
import argparse
import json
import os
from pathlib import Path

import requests


# Function to download a file
def download_file(url, path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Downloaded {path}")
    else:
        print(f"Failed to download {path}. Status code: {response.status_code}")


# Function to process a JSON file
def process_json_file(file_path: str, download_folder: str):
    print(f"Processing {file_path}")
    with open(file_path) as file:
        data = json.load(file)
    for item in data:
        download_path = os.path.join(download_folder, item["path"])
        download_file(item["url"], download_path)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Download files specified in JSON files from a given folder.")
    parser.add_argument("download_folder", type=str, help="The folder where files will be downloaded.")
    parser.add_argument("--configs", nargs="+", help="list of texture configs")

    args = parser.parse_args()

    # Create the download folder if it doesn't exist
    os.makedirs(args.download_folder, exist_ok=True)
    print(f"Download folder: {args.download_folder}")
    print(f"Processing configs: {args.configs}")

    # Iterate over all JSON files in the specified folder
    for texture_config in args.configs:
        if texture_config.endswith(".json"):
            process_json_file(
                texture_config,
                str(Path(args.download_folder) / Path(texture_config).stem),
            )


if __name__ == "__main__":
    main()
