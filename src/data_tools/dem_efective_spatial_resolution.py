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
import os
import time

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from numba import njit, prange

# Example oneliner to cut all tiff files in a folder:
# $ for file in ../moon_data/new_pgda78/*.tif; do poetry run python src/data_tools/cut_tiff.py $file "${file%.*}" --piece_size_km 2.0; done # noqa: E501


def compute_efective_spatial_resolution(input_tiff: str, output_tiff: str):
    """Compute the effective spatial resolution of a raster file.

    Args:
    ----
        input_tiff (str): Path to the input TIFF file.

    """
    # check if the file exists
    if not os.path.exists(input_tiff):
        msg = f"Input file {input_tiff} not found."
        raise FileNotFoundError(msg)

    # Open the input TIFF file
    with rasterio.open(input_tiff) as src:
        # Calculate the effective spatial resolution
        pixel_size_x, pixel_size_y = src.res[0], abs(src.res[1])  # Pixel size in meters
        # read fist band
        band = src.read(1)

    print(f"Computing the effective spatial resolution of the raster file {input_tiff}")
    print(f"Raster size: {band.shape}")
    print(f"Pixel size: {pixel_size_x:.2f} x {pixel_size_y:.2f} meters")

    # show a table with the percentage of pixels for each number of points
    unique, counts = np.unique(band, return_counts=True)
    total_pixels = band.size
    for i, (u, c) in enumerate(zip(unique, counts)):
        print(f"Number of points: {u}, Percentage of pixels: {c/total_pixels*100:.2g}%")
    # show a bar plot with the percentage of pixels for each number of points
    plt.bar(unique, counts / total_pixels)
    plt.xlabel("Number of points")
    plt.ylabel("Percentage of pixels")
    plt.title("Number of points per pixel")
    plt.savefig("number_of_points_per_pixel.png")

    start = time.time()
    efective_resolution_matrix = compute_resolution_numba(band, max_distance=1000, cell_size=pixel_size_x)
    print(f"Time elapsed: {time.time() - start}")

    # plot the histogram of the effective resolution
    plt.hist(efective_resolution_matrix.flatten())
    plt.xlabel("Effective resolution")
    plt.ylabel("Number of pixels")
    plt.title("Histogram of the effective resolution")
    plt.savefig("histogram_efective_resolution.png")

    # show a table with the percentage of pixels for each number of points
    unique, counts = np.unique(efective_resolution_matrix, return_counts=True)
    total_pixels = efective_resolution_matrix.size
    for i, (u, c) in enumerate(zip(unique, counts)):
        print(f"Effective resolution: {u}, Percentage of pixels: {c/total_pixels*100:.2g}%")

    # compute the median effective resolution
    median_efective_resolution = np.median(efective_resolution_matrix)
    print(f"Median effective resolution: {median_efective_resolution:.2f} meters")

    # cumulative histogram, percentage of pixels with resolution less than x
    fig, ax = plt.subplots()
    ax.hist(efective_resolution_matrix.flatten(), cumulative=True, density=True)
    ax.set_xlabel("Effective resolution")
    ax.set_ylabel("Percentage of pixels")
    ax.set_title("Cumulative histogram of the effective resolution")
    plt.savefig("cumulative_histogram_efective_resolution.png")

    # Write the piece to a new TIFF file
    with rasterio.open(
        output_tiff,
        "w",
        driver="GTiff",
        height=src.height,
        width=src.width,
        count=1,
        dtype=efective_resolution_matrix.dtype,
        crs=src.crs,
        transform=src.transform,
    ) as dst:
        dst.write(efective_resolution_matrix, 1)


@njit(parallel=True)
def compute_resolution_numba(band, max_distance=1000, cell_size=1):
    # input band has the number of lidar points in each pixel. if the pixel has 0 points,
    # find the closest pixel with points
    # and use the distance to that pixel as the resolution
    # if the pixel has points, the resolution is 0

    efective_resolution_matrix = band.copy()
    n_rows, n_cols = band.shape
    for i in prange(n_rows):
        for j in prange(n_cols):
            if band[i, j] == 0:
                # find the closest pixel with points
                for d in range(1, min(max_distance, max(n_rows, n_cols))):
                    for i_ in range(i - d, i + d + 1):
                        for j_ in range(j - d, j + d + 1):
                            if i_ >= 0 and i_ < n_rows and j_ >= 0 and j_ < n_cols and band[i_, j_] > 0:
                                efective_resolution_matrix[i, j] = (
                                    cell_size * 2 * ((i - i_) ** 2 + (j - j_) ** 2) ** 0.5
                                )
                                break
                    if efective_resolution_matrix[i, j] > 0:
                        break
            else:
                efective_resolution_matrix[i, j] = cell_size
    return efective_resolution_matrix


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute the effective spatial resolution of a raster file.")
    parser.add_argument("input_tiff", type=str, help="Path to the input TIFF file.")
    parser.add_argument("--output", type=str, default=None, help="Path to the output tiff file.")
    args = parser.parse_args()

    if args.output is None:
        args.output = args.input_tiff.replace(".tif", "_efective_spatial_resolution")
    compute_efective_spatial_resolution(args.input_tiff, args.output)
