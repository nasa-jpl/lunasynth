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
import json
import os
import re

import pandas as pd
import panel as pn
import requests
import tqdm


def parse_size(size_str):
    # Define a mapping of units to their corresponding byte values
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
        "PB": 1024**5,
    }

    # Use regular expressions to parse the number and unit from the string
    match = re.match(r"([\d.]+)\s*([a-zA-Z]+)", size_str)

    if not match:
        msg = "Invalid size format"
        raise ValueError(msg)

    # Extract the number and unit
    number, unit = match.groups()
    number = float(number)
    unit = unit.upper()

    if unit not in units:
        msg = "Invalid unit"
        raise ValueError(msg)

    # Convert the size to bytes
    return number * units[unit]


def get_rock_json(use_local_copy: bool = False) -> dict:
    if use_local_copy:
        apollo_rock_metadata_file = "config/apollo_data/lunar_sample_metadata.json"
        with open(apollo_rock_metadata_file) as file:
            apollo_rock_metadata = json.load(file)
    else:
        apollo_rock_metadata = requests.get(
            "https://ares.jsc.nasa.gov/astromaterials3d/explorer/lunar_sample_metadata.json"
        ).json()
    return apollo_rock_metadata


def get_rock_list() -> list:
    use_local_copy = False
    apollo_rock_metadata = get_rock_json(use_local_copy)
    rocks_list = list(apollo_rock_metadata.keys())
    print(f"Found {len(rocks_list)} rocks in the Apollo dataset.")
    return rocks_list


def download_file(url, fname) -> bool:
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


def get_imag_url(rock_name: str) -> str:
    return f"https://ares.jsc.nasa.gov/astromaterials3d/_images/_samples/HRPP_{rock_name}.jpg"


def download_apollo_rocks_images(rock_name: str, output_dir: str = "assets/rocks/apollo"):
    os.makedirs(output_dir, exist_ok=True)
    # example: https://ares.jsc.nasa.gov/astromaterials3d/_images/_samples/HRPP_12013-11.jpg
    image_url = get_imag_url(rock_name)
    image_path = os.path.join(output_dir, f"{rock_name}/{rock_name}_table_photo.jpg")
    download_file(image_url, image_path)


def download_table_photos():
    rocks_list = get_rock_list()
    for rock in tqdm.tqdm(rocks_list, desc="Downloading Apollo rocks"):
        print(f"Downloading rock {rock}")
        download_apollo_rocks_images(rock)


if __name__ == "__main__":
    using_local_photos = False
    if not os.path.exists("assets/rocks/apollo") and using_local_photos:
        download_table_photos()
    rock_json = get_rock_json()

    links = {}
    for rock_id in rock_json:
        links[rock_id] = (
            f'<a href="https://ares.jsc.nasa.gov/astromaterials3d/sample-details.htm?sample={rock_id}">Astromaterials</a> '  # noqa: E501
        )
        if "curation_url" in rock_json[rock_id]:
            links[rock_id] += f'<a href="{rock_json[rock_id]["curation_url"]}">Curation</a> '
        if "watch_url" in rock_json[rock_id]:
            links[rock_id] += f'<a href="{rock_json[rock_id]["watch_url"]}">Watch</a>'

    # create pandas dataframe with rocks. set index to key
    full_rock_df = pd.DataFrame(rock_json).T
    full_rock_df.set_index("display_name", inplace=False)
    full_rock_df["Apollo Mission"] = full_rock_df["origin_category_title"].str.split().str[1]
    full_rock_df["rock_id"] = full_rock_df.index.str.replace(",", "-")
    full_rock_df["rock_image_url_path"] = full_rock_df["rock_id"].apply(lambda x: get_imag_url(x))
    full_rock_df["rock_image_local_path"] = full_rock_df["rock_id"].apply(
        lambda x: f"assets/rocks/apollo/{x}/{x}_table_photo.jpg"
    )
    full_rock_df["Image"] = full_rock_df["rock_image_url_path"].apply(lambda x: f'<img src="{x}" width="100">')
    full_rock_df["detailsField_vertices"] = full_rock_df["detailsField_vertices"].apply(
        lambda x: int(x.replace(",", "")) if x != "" else "N/A"
    )
    full_rock_df["detailsField_webVertices"] = full_rock_df["detailsField_webVertices"].apply(
        lambda x: int(x.replace(",", "")) if x != "" else "N/A"
    )
    full_rock_df["Links"] = full_rock_df["rock_id"].apply(lambda x: links[x])

    full_rock_df["detailsField_meshSize"] = full_rock_df["detailsField_meshSize"].apply(parse_size)
    full_rock_df["detailsField_webMeshSize"] = full_rock_df["detailsField_webMeshSize"].apply(parse_size)

    df = full_rock_df.rename(
        columns={
            "display_name": "Rock Name",
            "classification": "Rock Type",
            "detailsField_vertices": "High Res Verts",
            "detailsField_textureRes": "Texture Resolution",
            "detailsField_meshSize": "High Res Size",
            "detailsField_webMeshSize": "Low Res Size",
            "detailsField_webVertices": "Low Res Verts",
        }
    )
    desired_columns = [
        "Rock Name",
        "Apollo Mission",
        "Rock Type",
        "High Res Verts",
        "High Res Size",
        "Low Res Size",
        "Texture Resolution",
        "Links",
        "Image",
    ]
    editors = {column: None for column in desired_columns}
    rock_df = df[desired_columns]
    # do not include index in the table
    pn.extension("tabulator")
    pn.widgets.Tabulator.theme = "bootstrap4"
    from bokeh.models.widgets.tables import NumberFormatter

    filesize_formatter = NumberFormatter(format="0.0 b")
    rock_table = pn.widgets.Tabulator(
        rock_df,
        show_index=False,
        formatters={
            "Image": {"type": "html"},
            "Links": {"type": "html"},
            "High Res Size": filesize_formatter,
            "Low Res Size": filesize_formatter,
        },
        editors=editors,  # Disable editing for the image column
    )
    rock_table.servable()
    pn.serve(rock_table)

    # save the file
    rock_table.save("docs/rock_table.html", embed=True)
