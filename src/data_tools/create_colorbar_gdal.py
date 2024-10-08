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

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt


def read_color_table(file_path):
    color_table = []
    with open(file_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 4:  # Ignore 'nv' or malformed lines
                value, r, g, b = map(int, parts)
                color_table.append((value, (r / 255, g / 255, b / 255)))
    return color_table


def create_colorbar(color_table, output_file):
    # Prepare colors and positions
    values, colors = zip(*color_table)
    min_value = min(values)
    max_value = max(values)
    norm = mcolors.Normalize(vmin=min_value, vmax=max_value)

    # Normalize the value points to range [0, 1]
    normalized_values = [(v - min_value) / (max_value - min_value) for v in values]

    # Create a colormap with gradients
    cdict = {"red": [], "green": [], "blue": []}
    for norm_value, color in zip(normalized_values, colors):
        r, g, b = color
        cdict["red"].append((norm_value, r, r))
        cdict["green"].append((norm_value, g, g))
        cdict["blue"].append((norm_value, b, b))

    cmap = mcolors.LinearSegmentedColormap("custom_cmap", cdict)

    # Create a colorbar
    fig, ax = plt.subplots(figsize=(8, 1))
    fig.subplots_adjust(bottom=0.5)

    cbar = fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=ax,
        orientation="horizontal",
        label="Elevation",
    )

    # Set ticks to be at the boundaries
    cbar.set_ticks(values)
    cbar.set_ticklabels([str(v) for v in values])

    # Save the colorbar to a file
    plt.savefig(output_file, bbox_inches="tight")
    # plt.show()


def main():
    parser = argparse.ArgumentParser(description="Create a colorbar for a color-relief file.")
    parser.add_argument("color_file", type=str, help="Path to the color.txt file.")
    parser.add_argument("output_file", type=str, help="Path to the output colorbar image file.")

    args = parser.parse_args()

    color_table = read_color_table(args.color_file)
    create_colorbar(color_table, args.output_file)


if __name__ == "__main__":
    main()
