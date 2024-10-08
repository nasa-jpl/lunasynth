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
# This script is used to view the segmentation image from the black and white png image.

# Path: src/view_segmentation_image.py

import argparse

import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="View segmentation image from black and white png image.")
    parser.add_argument("segmentation_image", type=str, help="The segmentation image to view.")
    args = parser.parse_args()

    segmentation_image = plt.imread(args.segmentation_image)
    segmentation_image = np.array(segmentation_image)  # convert to 2D array
    print(f"Segmentation image shape: {segmentation_image.shape}")

    # Count how many different values are in the image
    if len(segmentation_image.shape) == 3:
        flat_image = segmentation_image.reshape(-1, 3)
    else:
        flat_image = segmentation_image.reshape(-1, 1)
    npixels, nchannels = flat_image.shape
    unique_values = np.unique(flat_image, axis=0)

    number_colors_steps = 255

    [print(f"{value*number_colors_steps}") for value in unique_values]

    # what percentage of the image is each value
    print(f"{len(unique_values)} unique values")
    for value in unique_values:
        percentage = np.sum(flat_image == value) / npixels / nchannels
        print(f"{value}: {percentage:.2%}")

    plt.matshow(segmentation_image)  # display image
    plt.colorbar()
    plt.show()


if __name__ == "__main__":
    main()
