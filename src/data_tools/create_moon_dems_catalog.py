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
import os
import re

import numpy as np
import pandas as pd
import panel as pn
import rasterio as rio
import requests
import tqdm


def parse_size(size_str) -> float:
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


def download_file(url: str, fname: str) -> bool:
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


def get_url(site, instrument="LOLA", resolution=5):
    # example "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif"
    return (
        f"https://pgda.gsfc.nasa.gov/data/{instrument}_{resolution}mpp/{site}/{site}_final_adj_{resolution}mpp_surf.tif"
    )


def compute_histogram(elevation, bins=50):
    histogram, bin_edges = np.histogram(elevation.compressed(), bins=bins)
    return histogram, bin_edges


if __name__ == "__main__":
    data_dir = "../moon_data/pgda"  # Make sure to change this to the correct path of your data
    # imgs_dir = "docs/pgda/thumb/"
    imgs_dir = "http://localhost:8000/"

    # Find all .tif files in the data directory
    tif_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith("_surf.tif")]
    print(f"Found {len(tif_files)} DEMs files in {data_dir}")
    moon_dem_dict = {}
    for tif_file in tif_files:
        moon_dem_dict[tif_file] = {}
        moon_dem_dict[tif_file]["Site"] = os.path.basename(tif_file).split("_")[0]
        moon_dem_dict[tif_file]["Filename"] = os.path.basename(tif_file)
        moon_dem_dict[tif_file]["full_path"] = tif_file

        with rio.open(tif_file) as src:
            moon_dem_dict[tif_file]["Resolution (m/pixel)"] = src.res[0]

            moon_dem_dict[tif_file]["Size (km^2)"] = src.shape[0] * src.shape[1] * (src.res[0] / 1000) ** 2
            moon_dem_dict[tif_file]["Dimensions (km,km)"] = (
                f"{src.shape[0]*src.res[0]/1000}, {src.shape[1]*src.res[0]/1000}"
            )
            moon_dem_dict[tif_file]["Rows"] = src.shape[0]
            moon_dem_dict[tif_file]["Cols"] = src.shape[1]
            moon_dem_dict[tif_file]["Latitude (deg)"] = 84
            moon_dem_dict[tif_file]["Max Elevation"] = 90 - moon_dem_dict[tif_file]["Latitude (deg)"] + 1.4
            moon_dem_dict[tif_file]["File Size"] = os.path.getsize(tif_file)
            moon_dem_dict[tif_file]["Min Elevation (m)"] = float(src.read(1).min())
            moon_dem_dict[tif_file]["Max Elevation (m)"] = float(src.read(1).max())
            moon_dem_dict[tif_file]["Vertical Difference (m)"] = src.read(1).max() - src.read(1).min()
            moon_dem_dict[tif_file]["Creation Date"] = os.path.getctime(tif_file)
            elevation_masked = np.ma.masked_equal(src.read(1), src.nodata)
            (
                moon_dem_dict[tif_file]["histogram"],
                moon_dem_dict[tif_file]["bin_edges"],
            ) = compute_histogram(elevation_masked)
        moon_dem_dict[tif_file]["url"] = get_url(moon_dem_dict[tif_file]["Site"])

    full_moon_dem_df = pd.DataFrame(moon_dem_dict).T
    # full_moon_dem_df.set_index("display_name", inplace=False)

    image_width = 160

    full_moon_dem_df["elevation_histogram_file"] = full_moon_dem_df["Filename"].apply(
        lambda x: imgs_dir + x.replace(".tif", "_histogram.png")
    )
    full_moon_dem_df["Elevation Histogram"] = full_moon_dem_df["elevation_histogram_file"].apply(
        lambda x: f'<img src="{x}" width="{image_width}">'
    )

    full_moon_dem_df["hillshade_file"] = full_moon_dem_df["Filename"].apply(
        lambda x: imgs_dir + x.replace(".tif", "_hillshade_color_relief_lowres.png")
    )
    full_moon_dem_df["Hillshade with Color-Relief Image"] = full_moon_dem_df["hillshade_file"].apply(
        lambda x: f'<img src="{x}" width="{image_width}">'
    )

    full_moon_dem_df["slope_file"] = full_moon_dem_df["Filename"].apply(
        lambda x: imgs_dir + x.replace(".tif", "_slope_bright_lowres.png")
    )
    full_moon_dem_df["Slope Image"] = full_moon_dem_df["slope_file"].apply(
        lambda x: f'<img src="{x}" width="{image_width}">'
    )

    full_moon_dem_df["slope_histogram_file"] = full_moon_dem_df["Filename"].apply(
        lambda x: imgs_dir + x.replace(".tif", "_slope_histogram.png")
    )
    full_moon_dem_df["slope Histogram"] = full_moon_dem_df["slope_histogram_file"].apply(
        lambda x: f'<img src="{x}" width="{image_width}">'
    )

    full_moon_dem_df["Link"] = full_moon_dem_df["url"].apply(lambda x: f'<a href="{x}">Download</a>')
    desired_columns = [
        "Site",
        "Resolution (m/pixel)",
        "Size (km^2)",
        "Dimensions (km,km)",
        "Latitude (deg)",
        "Rows",
        "Cols",
        "File Size",
        "Min Elevation (m)",
        "Max Elevation (m)",
        "Vertical Difference (m)",
        # "Creation Date",
        "Link",
        "Elevation Histogram",
        "slope Histogram",
        "Slope Image",
        "Hillshade with Color-Relief Image",
        # "Renders 0,90,180,270",
    ]
    editors = {column: None for column in desired_columns}
    moon_dem_df = full_moon_dem_df[desired_columns]
    pn.extension("tabulator")
    pn.widgets.Tabulator.theme = "bootstrap4"
    from bokeh.models.widgets.tables import NumberFormatter

    filesize_formatter = NumberFormatter(format="0.0 b")
    formatters = {
        "Slope Image": {"type": "html"},
        "Elevation Histogram": {"type": "html"},
        "slope Histogram": {"type": "html"},
        "Hillshade with Color-Relief Image": {"type": "html"},
        "Link": {"type": "html"},
        "File Size": filesize_formatter,
        "Min Elevation": NumberFormatter(format="0.0"),
        "Max Elevation": NumberFormatter(format="0.0"),
        "Vertical Difference": NumberFormatter(format="0.0"),
        # "Creation Date": {"type": "datetime"},
    }

    moon_dem_table = pn.widgets.Tabulator(
        moon_dem_df,
        show_index=False,
        formatters=formatters,
        editors=editors,  # Disable editing
    )
    context_image_url = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/ContextMap.png"
    context_image_pane = pn.pane.Image(context_image_url, width=1000, height=1000)
    colorbar_image_pane = pn.pane.Image("config/lola_colors.png", width=1000)
    moon_dem_catalog = pn.Column(
        pn.pane.Markdown(
            """
            # Moon DEM Catalog
            This table shows the catalog of Digital Elevation Models (DEMs) of the Moon.
            The data was downloaded from the Planetary Geodynamics Laboratory (PGDA) at NASA Goddard Space Flight Center
            """
        ),
        colorbar_image_pane,
        moon_dem_table,
        context_image_pane,
    )
    moon_dem_catalog.servable()
    pn.serve(moon_dem_catalog)

    # save the file
    moon_dem_catalog.save("docs/moon_dem_table.html", embed=True)
