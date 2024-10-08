#!/usr/bin/env python
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

# import yaml
import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# def load_images(image_dir: str) -> np.ndarray:
from PIL import Image


def get_dataset_dataframe(dataset_path: str) -> pd.DataFrame:
    # load adjusted_dataset_config.json
    # with open(os.path.join(dataset_path, "adjusted_dataset_config.json"), "r") as f:
    #     dataset_config = yaml.safe_load(f)

    # df = pd.DataFrame(columns=["mesh_name", "terrain_index", "image_index", "image_path"])

    # Find folders that start with "mesh_"
    mesh_folders = []
    images = []
    number_craters = 0
    number_rocks = 0
    for folder in os.listdir(dataset_path):
        if folder.startswith("mesh_"):
            print(f"Found mesh folder: {folder}")
            mesh_folder = folder
            mesh_name = folder.split("mesh_")[1]
            mesh_folders.append(folder)
            # for each folder, find folders that start with "terrain_XX"
            terrain_folders = []
            for folder in os.listdir(os.path.join(dataset_path, mesh_folder)):
                if folder.startswith("terrain_"):
                    terrain_folders.append(folder)
                    terrain_folder = folder
                    terrain_index = int(folder.split("_")[1])

                    cases_config = read_cases_config(
                        os.path.join(dataset_path, mesh_folder, terrain_folder, "params.json")
                    )
                    number_rocks += count_rocks(
                        os.path.join(dataset_path, mesh_folder, terrain_folder, "rock_field.csv")
                    )
                    number_craters += count_craters(
                        os.path.join(
                            dataset_path,
                            mesh_folder,
                            terrain_folder,
                            "crater_field.csv",
                        )
                    )
                    plot_cases_ortho(
                        cases_config["cases_list"],
                        output=os.path.join(dataset_path, mesh_folder, terrain_folder, "cases_ortho.png"),
                    )

                    # for each folder, find the images
                    for filename in os.listdir(os.path.join(dataset_path, mesh_folder, terrain_folder)):
                        if filename.startswith("rgb_") and filename.endswith(".png"):
                            image_index = int(filename.split("_")[-1].split(".")[0])
                            image_file = filename

                            image_path = os.path.join(dataset_path, mesh_folder, terrain_folder, image_file)

                            # classes, classes_distribution = get_classes_distribution_image(image_path)
                            dark_pixels = calculate_percentage_below_threshold(image_path, 0.1)

                            # print(f"Classes: {classes}")

                            # add to dataframe
                            images.append(
                                {
                                    "mesh_name": mesh_name,
                                    "terrain_index": terrain_index,
                                    "image_index": image_index,
                                    "image_path": image_path,
                                    "dark_pixels": dark_pixels,
                                }
                            )

    df = pd.DataFrame(images)
    print(f"Number of images: {len(df):,}")
    print(f"Number of rocks: {number_rocks:,}, Number of craters: {number_craters:,}")
    print(df)
    return df


def count_rocks(rock_field_path: str) -> int:
    with open(rock_field_path) as f:
        rock_field = pd.read_csv(f)
    return len(rock_field)


def count_craters(crater_field_path: str) -> int:
    with open(crater_field_path) as f:
        crater_field = pd.read_csv(f)
    return len(crater_field)


def read_cases_config(cases_config_path: str) -> list:
    with open(cases_config_path) as f:
        cases_config = json.load(f)
    # cases_list = cases_config["cases_list"]

    return cases_config


def plot_cases_ortho(cases_list: list, output: str = None):
    fig, ax = plt.subplots()

    for case in cases_list:
        x = case["camera/x"]
        y = case["camera/y"]
        case_size = case["camera/ortho_scale"]
        # draw square of at x,y with size case_size
        rect = plt.Rectangle(
            (x - case_size / 2, y - case_size / 2),
            case_size,
            case_size,
            edgecolor="black",
            facecolor="none",
        )
        ax.add_patch(rect)
    # plot border limit

    map_size = [2000, 2000]
    rect = plt.Rectangle(
        (-map_size[0] / 2, -map_size[1] / 2),
        map_size[0],
        map_size[1],
        edgecolor="blue",
        facecolor="none",
    )
    ax.add_patch(rect)

    plt.axis("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Orthographic projection of cases")
    if output is not None:
        plt.savefig(output)
        plt.close()
    else:
        plt.show()


def get_classes_distribution_image(image: str):
    # load image
    image = plt.imread(image)
    # get classes distribution
    classes, counts = np.unique(image, return_counts=True)
    return classes, counts


def calculate_percentage_below_threshold(image_path, threshold):
    # Open the image file
    with Image.open(image_path) as img:
        # Convert the image to grayscale
        grayscale_img = img.convert("L")
        # Convert the grayscale image to a numpy array
        img_array = np.array(grayscale_img)

    # Calculate the total number of pixels
    total_pixels = img_array.size

    # Count the number of pixels below the threshold
    pixels_below_threshold = np.sum(img_array < threshold)

    # Calculate the percentage
    percentage_below_threshold = (pixels_below_threshold / total_pixels) * 100

    return percentage_below_threshold


def get_image_histogram(image: str):
    # load image
    image = plt.imread(image)
    # get histogram
    histogram, bins = np.histogram(image, bins=10, range=(0, 1))
    return histogram, bins


def get_dark_percentrage(image: str, threshold: float = 0.1) -> float:
    histogram, bins = get_image_histogram(image)
    dark_pixels = np.sum(histogram[: int(threshold * len(histogram))])
    total_pixels = np.sum(histogram)
    return dark_pixels / total_pixels


def analyze_dataset(dataset_path: str, output: str = None):
    df = get_dataset_dataframe(dataset_path)

    # make a histogram of "dark_pixels"

    # plot histogram
    plt.hist(df["dark_pixels"], bins=100)
    plt.xlabel("Percentage of dark pixels")
    plt.ylabel("Number of images")
    plt.title("Histogram of dark pixels")
    if output is not None:
        plt.savefig(output)
        plt.close()
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Analyze a dataset.")
    parser.add_argument("dataset_path", type=str, help="The dataset to analyze.")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="The output filename for the outputs",
    )
    args = parser.parse_args()

    analyze_dataset(args.dataset_path, args.output)


if __name__ == "__main__":
    main()
