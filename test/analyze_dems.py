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
import math
import os

import numpy as np
import rasterio as rio
from rasterio.warp import transform


def rad_to_dms(rad):
    # Convert radians to degrees
    deg = math.degrees(rad)
    # Get the integer part of the degrees
    d = int(deg)

    # Get the fractional part and convert to minutes
    min_float = (deg - d) * 60
    m = int(min_float)

    # Get the fractional part of minutes and convert to seconds
    s = (min_float - m) * 60
    return d, m, s


def latlong_rad_to_strings(lat, long):
    d, m, s = rad_to_dms(abs(lat))
    n_s = "N" if lat > 0 else "S"
    lat_string = f"{d}°{m}'{s:.0f}\"{n_s}"
    d, m, s = rad_to_dms(long)
    # e_w = "E" if long > math.pi else "W"
    long_string = f"{d}°{m}'{s:.0f}\""
    return lat_string, long_string


def analyze_dems() -> None:
    data_dir = "moon_data/pgda"  # change to the path of the data directory

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

            # center_latitude, center_longitude = rio.transform.xy(
            #     src.transform, src.height // 2, src.width // 2
            # )

            # latitudes and longitudes
            lunar_south_crs = "ESRI:103878"  # Moon 2000 South Pole Stereographic
            lunar_center_crs = "ESRI:104903"  # GCS_Moon_2000
            center_y = (src.bounds.left + src.bounds.right) / 2
            center_x = (src.bounds.top + src.bounds.bottom) / 2
            long, lat = transform(lunar_south_crs, lunar_center_crs, [center_y], [center_x])
            center_latitude, center_longitude = (
                math.radians(lat[0]),
                math.radians(long[0]),
            )
            # center_longitude = (-center_longitude+math.pi/2) % (2 * np.pi)
            center_latitude_str, center_longitude_str = latlong_rad_to_strings(
                center_latitude, center_longitude % (2 * np.pi)
            )
            moon_dem_dict[tif_file]["CenterX"] = center_x / 1000
            moon_dem_dict[tif_file]["CenterY"] = center_y / 1000
            moon_dem_dict[tif_file]["Latitude"] = center_latitude_str
            moon_dem_dict[tif_file]["Longitude"] = center_longitude_str
            moon_dem_dict[tif_file]["bounds"] = src.bounds
            # print(f"Latitude: {center_latitude}")
            # print(f"long {center_longitude}, dxdy angle {dxydy}, diff {center_longitude-dxydy}")
            moon_R = 1737.4 * 1000
            dxdy_norm = np.sqrt(center_x**2 + center_y**2)
            dxdy_angle = np.arcsin(dxdy_norm / moon_R)
            dxdy_sin = dxdy_norm / moon_R
            dxdy_tan = np.tan(dxdy_angle)
            # print(f"long to 0 {center_latitude}, dxdy long {dxdy_angle}, diff {center_longitude - dxydy}")
            # print(f"lat to 90 {np.pi - center_latitude}, dxdy lat {dxdy_angle},
            # diff {np.pi - center_latitude - dxdy_angle}")
            print(
                f"lat to 90 {np.pi/2 - abs(center_latitude)- dxdy_angle}, "
                f"diff {np.pi/2 - abs(center_latitude) - dxdy_sin}, "
                f"diff {np.pi/2 - abs(center_latitude) - dxdy_tan}"
            )

    # total size of all DEMs
    total_size = sum([moon_dem_dict[tif_file]["Size (km^2)"] for tif_file in tif_files])
    print(f"Total size of all DEMs: {total_size:.2f} km^2")

    # get coordinates of 84, 85, 86, 87, 88, 89, degrees circles

    circles_degrees = [84, 87, 89]
    cx = np.zeros(len(circles_degrees))
    for i, lat_deg in enumerate(circles_degrees):
        # lat = math.radians(lat_deg)
        latlong = transform(lunar_center_crs, lunar_south_crs, [0], [-lat_deg])
        print(f"Circle at {lat_deg} degrees latitude, x: {latlong[0][0]:.2f}, y: {latlong[1][0]:.2f}")
        cx[i] = latlong[1][0]

    critical_latitude = 90 - 1.54
    latlong_critical = transform(lunar_center_crs, lunar_south_crs, [0], [-critical_latitude])
    cx_critical = latlong_critical[1][0]

    # print dict as table
    import pandas as pd

    df = pd.DataFrame(moon_dem_dict).T

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.scatter(df["CenterY"], df["CenterX"], color="blue", s=4)
    # plot rectangles for each DEM, using bounds corners, matpliotlib patches
    # for i, txt in enumerate(df["Site"]):

    ax.set_xlabel("South Pole Stereographic X")
    ax.set_ylabel("South Pole Stereographic Y")
    ax.set_title("DEM Center Coordinates")
    for i, txt in enumerate(df["Site"]):
        ax.annotate(txt, (df["CenterY"][i] + 1, df["CenterX"][i] + 1), ha="center", fontsize=10)

        # add text with latitude and longitude strings
        ax.annotate(
            f"{df['Latitude'][i]}\n{df['Longitude'][i]}",
            (df["CenterY"][i], df["CenterX"][i] - 1),
            ha="center",
            va="top",
            color="blue",
            fontsize=8,
        )

        # draw an arrow of size 10km from the center, pointing away from the center
        direction_arrow = np.array([df["CenterY"][i], df["CenterX"][i]])
        direction_arrow = direction_arrow / np.linalg.norm(direction_arrow) * 10

    for i in range(len(circles_degrees)):
        ax.add_patch(plt.Circle((0, 0), cx[i] / 1000, edgecolor="red", fill=False))
        # add text with circle latitude
        ax.annotate(
            f"{circles_degrees[i]}°",
            (0, cx[i] / 1000),
            ha="center",
            va="bottom",
            color="red",
            fontsize=12,
        )
    ax.add_patch(plt.Circle((0, 0), cx_critical / 1000, linestyle="--", edgecolor="red", fill=False))

    # choose columns to print without index
    columns = ["Site", "Dimensions (km,km)", "Latitude", "Longitude"]
    ax.set_aspect("equal", "box")
    ax.grid()
    plt.show()
    print(df[columns].to_string(index=False))


def main() -> None:
    analyze_dems()


if __name__ == "__main__":
    main()
