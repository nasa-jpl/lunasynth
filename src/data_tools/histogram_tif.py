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

import matplotlib.pyplot as plt
import numpy as np
import rasterio


def read_geotiff(tif_path):
    with rasterio.open(tif_path) as src:
        elevation = src.read(1)
        elevation = np.ma.masked_equal(elevation, src.nodata)

    return elevation


def compute_histogram(elevation, bins=50):
    histogram, bin_edges = np.histogram(elevation.compressed(), bins=bins)
    return histogram, bin_edges


def create_histogram_figure(histogram, bin_edges, output_file, label="Elevation"):
    plt.figure(figsize=(10, 10))
    # show bins as area
    # use ticks of 10^3
    min_value = bin_edges.min()
    max_value = bin_edges.max()
    diff_value = max_value - min_value
    ticks_order_mag = int(np.floor(np.log10(diff_value)))
    ticks = [
        th * 10**ticks_order_mag
        for th in range(
            int(np.floor(min_value / 10**ticks_order_mag)),
            int(np.ceil(max_value / 10**ticks_order_mag)),
        )
    ]
    plt.xticks(ticks, fontsize=38)
    plt.bar(bin_edges[:-1], histogram, width=np.diff(bin_edges))
    plt.yticks([])
    plt.savefig(output_file, dpi=300, bbox_inches="tight")


def main():
    parser = argparse.ArgumentParser(description="Compute and plot histogram of elevation values from a TIFF file.")
    parser.add_argument("tif_file", type=str, help="Path to the input TIFF file.")
    parser.add_argument("output_file", type=str, help="Path to the output histogram image file.")
    parser.add_argument("--bins", type=int, default=50, help="Number of bins for the histogram.")
    parser.add_argument("--label", type=str, default="Elevation", help="label")

    args = parser.parse_args()

    elevation = read_geotiff(args.tif_file)
    histogram, bin_edges = compute_histogram(elevation, bins=args.bins)
    create_histogram_figure(histogram, bin_edges, args.output_file, label=args.label)


if __name__ == "__main__":
    main()
