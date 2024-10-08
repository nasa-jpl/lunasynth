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
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

"""Parse the Apollo image metadata from the LPI website

Output:
- apollo_data.json: JSON file containing the metadata for each image
- apollo_all_images.json: JSON file containing all the images
- apollo_all_images.csv: CSV file containing all the images
- apollo_all_images.parquet: Parquet file containing all the images
- magazine_data.json: JSON file containing the metadata for each magazine
- magazine_data.csv: CSV file containing the metadata for each magazine
"""


# Fetch the webpage
def get_soup(url: str) -> BeautifulSoup:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch page: {response.status_code}")
        exit()
    return BeautifulSoup(response.content, "html.parser")


def parse_image_url(image_url: str):
    # Extract image source and alt text
    soup = get_soup(image_url)
    img_tag = soup.find("img", {"class": "space-bottom-small"})
    img_src = img_tag["src"]
    if not img_src.startswith("http"):
        img_src = urllib.parse.urljoin(image_url, img_src)
    img_alt = img_tag["alt"]

    # Extract table data
    table_data = {}
    table = soup.find("table", {"class": "text-table"})
    rows = table.find_all("tr")
    for row in rows:
        columns = row.find_all("td")
        if len(columns) == 2:
            key = columns[0].text.strip().replace(":", "")
            links = columns[1].find_all("a")
            if len(links) > 0:
                # link_text = links[0].text.strip()
                link_url = links[0]["href"]
                if not link_url.startswith("http"):
                    link_url = urllib.parse.urljoin(image_url, link_url)
                value = link_url
            else:
                value = columns[1].text.strip()
            table_data[key] = value

    # Add image source and alt to the data
    table_data["Image Source"] = img_src
    table_data["Image Alt"] = img_alt

    return table_data


def parse_magazine_url(magazine_url: str):
    soup = get_soup(magazine_url)
    data = []
    divs = soup.find_all("div", {"class": "col-4 col-md-3 col-lg-2"})

    for div in divs:
        link = div.find("a")["href"]
        img_src = div.find("img")["src"]
        img_alt = div.find("img")["alt"]

        if not link.startswith("http"):
            link = urllib.parse.urljoin(magazine_url, link)
        if not img_src.startswith("http"):
            img_src = urllib.parse.urljoin(magazine_url, img_src)

        entry = {"Link": link, "Image_Source": img_src, "Image_Alt": img_alt}
        data.append(entry)
    return data


def parse_mission_url(mission: int):
    url = f"https://www.lpi.usra.edu/resources/apollo/catalog/70mm/mission/?{mission}"
    soup = get_soup(url)
    table = soup.find("table", {"class": "text-table"})

    if table is None:
        print("No table found")
        exit()

    data = []
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if len(columns) > 0:
            magazine = columns[0].text.strip()
            link = columns[1].find("a")["href"]
            if not link.startswith("/"):
                link = urllib.parse.urljoin(url, link)
            image_info = columns[2].text.strip()

            # Extract numbers and type using regex
            match = re.search(
                r"(\d+) (color|black & white) images \((\d+) surface; (\d+) orbital; (\d+) other\)",
                image_info,
            )
            if match:
                total_images = int(match.group(1))
                image_color_type = match.group(2)
                surface_images = int(match.group(3))
                orbital_images = int(match.group(4))
                other_images = int(match.group(5))
                if surface_images == total_images:
                    image_type = "Surface"
                elif orbital_images == total_images:
                    image_type = "Orbital"
                elif other_images == total_images:
                    image_type = "Other"
                else:
                    image_type = "Unknown"

            else:
                total_images = 0
                image_type = "Unknown"
                surface_images = 0
                orbital_images = 0
                other_images = 0

            entry = {
                "Magazine": magazine,
                "Link": link,
                "Image_Color_Type": image_color_type,
                "Image_Type": image_type,
                "Total_Images": total_images,
                "Surface_Images": surface_images,
                "Orbital_Images": orbital_images,
                "Other_Images": other_images,
            }
            data.append(entry)
    return data


mission_list = [11, 12, 13, 14, 15, 16, 17]
data = {}
for mission in tqdm(mission_list, desc="Missions", position=0, leave=True):
    data[mission] = parse_mission_url(mission)
    for magazine in tqdm(data[mission], desc="Magazines", position=1, leave=False):
        magazine["data"] = parse_magazine_url(magazine["Link"])
        for image in tqdm(magazine["data"], desc="Images", position=2, leave=False):
            image["image_info"] = parse_image_url(image["Link"])


# Save to JSON
with open("apollo_data.json", "w") as f:
    json.dump(data, f, indent=4)
print("Data has been written to apollo_images.json")

# create a list of all images
all_images = []
for mission in data:
    for magazine in data[mission]:
        for image in magazine["data"]:
            image_dict = image["image_info"]
            image_dict["Mission"] = mission
            image_dict["Magazine"] = magazine["Magazine"]
            image_dict["Image_Color_Type"] = magazine["Image_Color_Type"]
            image_dict["Image_Type"] = magazine["Image_Type"]
            all_images.append(image_dict)

# save magazine data
magazine_data = []
for mission in data:
    for magazine in data[mission]:
        magazine_dict = {
            "Mission": mission,
            "Magazine": magazine["Magazine"],
            "Image_Color_Type": magazine["Image_Color_Type"],
            "Image_Type": magazine["Image_Type"],
            "Total_Images": magazine["Total_Images"],
            "Surface_Images": magazine["Surface_Images"],
            "Orbital_Images": magazine["Orbital_Images"],
            "Other_Images": magazine["Other_Images"],
        }
        magazine_data.append(magazine_dict)

with open("magazine_data.json", "w") as f:
    json.dump(magazine_data, f, indent=4)

# save to csv
df = pd.DataFrame(magazine_data)
df.to_csv("magazine_data.csv", index=False)

# Save to JSON
with open("apollo_all_images.json", "w") as f:
    json.dump(all_images, f, indent=4)

df = pd.DataFrame(all_images)

# save to csv
df.to_csv("apollo_all_images.csv", index=False)

# save to parquet
df.to_parquet("apollo_all_images.parquet", index=False)

print("Data has been written to apollo_all_images.json")
