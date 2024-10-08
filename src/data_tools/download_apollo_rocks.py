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

"""Download public Apollo rock data from NASA's Astromaterials 3D website."""

import json
import os
import zipfile

import requests
import tqdm

use_local_copy = False
if use_local_copy:
    apollo_rock_metadata_file = "config/apollo_data/lunar_sample_metadata.json"
    with open(apollo_rock_metadata_file) as file:
        apollo_rock_metadata = json.load(file)
else:
    apollo_rock_metadata = requests.get(
        "https://ares.jsc.nasa.gov/astromaterials3d/explorer/lunar_sample_metadata.json"
    ).json()
rocks_list = list(apollo_rock_metadata.keys())

print(f"Found {len(rocks_list)} rocks in the Apollo dataset.")


def download_file(url, fname):
    # check if the file already exists
    if os.path.exists(fname):
        print(f"File {fname} already exists. Skipping download.")
        return True
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        total = int(response.headers.get("content-length", 0))
        with open(fname, "wb") as file, tqdm.tqdm(
            desc=fname,
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=8192):
                size = file.write(data)
                bar.update(size)
        print(f"Downloaded {url} to {fname}")
        return True
    else:
        print(f"Failed to download {url} to {fname}. Status code: {response.status_code}")
        return False


def download_apollo_rock(
    rock_name: str,
    output_dir: str = "assets/rocks/apollo",
    download_high_res: bool = True,
    download_low_res: bool = True,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    base_url = f"https://ares-a3d.s3.us-gov-east-1.amazonaws.com/samples/{rock_name}"
    if download_low_res:
        low_res_url = (
            f"{base_url}/2b_{rock_name}_"
            f"SFM_Web-Resolution-Model_Coordinate-Registered/{rock_name}_SFM_Web-Resolution-Model_Coordinate-Registered.zip"
        )
        low_res_path = os.path.join(output_dir, f"{rock_name}_low_res.zip")
        if download_file(low_res_url, low_res_path):
            with zipfile.ZipFile(low_res_path, "r") as zip_ref:
                zip_ref.extractall(output_dir + f"/{rock_name}/low_res")
        else:
            # try again without _SFM and model
            low_res_url = (
                f"{base_url}/2b_{rock_name}_SFM_Web-Resolution-Model_Coordinate-Registered/{rock_name}"
                f"_Web-Resolution-Model_Coordinate-Registered.zip"
            )  # for 12038-7 typo
            if download_file(low_res_url, low_res_path):
                with zipfile.ZipFile(low_res_path, "r") as zip_ref:
                    zip_ref.extractall(output_dir + f"/{rock_name}/low_res")
            else:
                low_res_url = (
                    f"{base_url}/2b_{rock_name}_Web-Resolution-Model_Coordinate-Registered/{rock_name}_"
                    f"Web-Resolution_Coordinate-Registered.zip"
                )  # for 60639-0 typo
                if download_file(low_res_url, low_res_path):
                    with zipfile.ZipFile(low_res_path, "r") as zip_ref:
                        zip_ref.extractall(output_dir + f"/{rock_name}/low_res")

    if download_high_res:
        high_res_url = (
            f"{base_url}/3b_{rock_name}_SFM_Full-Resolution-Model_Coordinate-Unregistered/{rock_name}_"
            f"SFM_Full-Resolution-Model_Coordinate-Unregistered.zip"
        )
        high_res_path = os.path.join(output_dir, f"{rock_name}_high_res.zip")
        if download_file(high_res_url, high_res_path):
            with zipfile.ZipFile(high_res_path, "r") as zip_ref:
                zip_ref.extractall(output_dir + f"/{rock_name}/high_res")


for rock in tqdm.tqdm(rocks_list, desc="Downloading Apollo rocks"):
    print(f"Downloading rock {rock}")
    download_apollo_rock(rock)
