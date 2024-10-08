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
import json
import os
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def create_bounding_boxes(
    rock_field: dict,
    crater_field: dict,
    rendering_cases: dict,
    size_x: int,
    size_y: int,
    terrain_path: str,
    output_json: str = "params_with_bounding_boxes.json",
) -> None:
    """Create bounding boxes for rocks in the rendering cases

    Args:
    ----
        rock_field (dict): Rock field
        rendering_cases (dict): Rendering cases
        size_x (int): Size of the x-axis
        size_y (int): Size of the y-axis
        output_json (str, optional): Path to the output json file. Defaults to "params_with_bounding_boxes.json".

    """
    for case in rendering_cases["cases_list"]:
        bounding_boxes_rocks = []
        for i, rock in rock_field.iterrows():
            bounding_box = get_bounding_box(
                rock["x"],
                rock["y"],
                rock["diameter"],
                size_x,
                size_y,
                case["camera/x"],
                case["camera/y"],
                case["camera/ortho_scale"],
            )
            if bounding_box is not None:
                bounding_boxes_rocks.append(bounding_box)
        case["rocks"] = bounding_boxes_rocks
        create_mask_image_ellipse(
            bounding_boxes_rocks,
            os.path.join(terrain_path, f"rock_ mask_circular_{case['case_id']:03d}.png"),
            size_x,
            size_y,
        )
        create_mask_image_square(
            bounding_boxes_rocks,
            os.path.join(terrain_path, f"rock_ mask_square_{case['case_id']:03d}.png"),
            size_x,
            size_y,
        )

        bounding_boxes_craters = []
        for i, crater in crater_field.iterrows():
            bounding_box = get_bounding_box(
                crater["x"],
                crater["y"],
                crater["diameter"],
                size_x,
                size_y,
                case["camera/x"],
                case["camera/y"],
                case["camera/ortho_scale"],
            )
            if bounding_box is not None:
                bounding_boxes_craters.append(bounding_box)
        case["craters"] = bounding_boxes_craters
        create_mask_image_ellipse(
            bounding_boxes_craters,
            os.path.join(terrain_path, f"crater_mask_{case['case_id']:03d}.png"),
            size_x,
            size_y,
        )

    print(f"Saving bounding boxes to {output_json}")
    with open(output_json, "w") as f:
        json.dump(rendering_cases, f)


def get_bounding_box(
    x_center_meters: float,
    y_center_meters: float,
    diameter: float,
    size_x: int,
    size_y: int,
    camera_x: float,
    camera_y,
    camera_size: float,
):
    if (
        x_center_meters > camera_x - camera_size / 2
        and x_center_meters < camera_x + camera_size / 2
        and y_center_meters > camera_y - camera_size / 2
        and y_center_meters < camera_y + camera_size / 2
    ):
        x_pixels, y_pixels, diameter_pixels = convert_to_pixel_space(
            rock_x=x_center_meters,
            rock_y=y_center_meters,
            rock_diameter=diameter,
            camera_center_x=camera_x,
            camera_center_y=camera_y,
            camera_size=camera_size,
            size_x=size_x,
            size_y=size_y,
        )
        bounding_box = {
            "x_center_meters": x_center_meters,
            "y_center_meters": y_center_meters,
            "diameter_meters": diameter,
            "x_min_pixels": int(x_pixels - diameter_pixels / 2),
            "y_min_pixels": int(y_pixels - diameter_pixels / 2),
            "x_center_pixels": x_pixels,
            "y_center_pixels": y_pixels,
            "diameter_pixels": diameter_pixels,
            "width_pixels": diameter_pixels,
            "height_pixels": diameter_pixels,
        }
        return bounding_box
    else:
        return None


def create_mask_image_square(bounding_boxes, output_filename, size_x, size_y):
    mask = np.zeros((size_x, size_y))
    for bounding_box in bounding_boxes:
        x_min = bounding_box["x_min_pixels"]
        y_min = bounding_box["y_min_pixels"]
        x_max = x_min + bounding_box["diameter_pixels"]
        y_max = y_min + bounding_box["diameter_pixels"]
        print(f"bounding_box: {bounding_box}")
        print(f"Creating mask for {x_min}, {y_min}, {x_max}, {y_max}")
        mask[x_min:x_max, y_min:y_max] = 1
    plt.imsave(output_filename, mask, cmap="gray")


def create_mask_image_ellipse(bounding_boxes, output_filename, size_x, size_y):
    mask = np.zeros((size_x, size_y))
    for bounding_box in bounding_boxes:
        x_center = bounding_box["x_center_pixels"]
        y_center = bounding_box["y_center_pixels"]
        x_radius = bounding_box["width_pixels"] / 2
        y_radius = bounding_box["height_pixels"] / 2
        for x in range(size_x):
            for y in range(size_y):
                if ((x - x_center) / x_radius) ** 2 + ((y - y_center) / y_radius) ** 2 <= 1:
                    mask[x, y] = 1
    plt.imsave(output_filename, mask, cmap="gray")


def convert_to_pixel_space(
    rock_x: float,
    rock_y: float,
    rock_diameter: float,
    camera_center_x: float,
    camera_center_y: float,
    camera_size: float,
    size_x: int,
    size_y: int,
) -> Tuple[int, int, int]:
    """Converts the rock coordinates to pixel space

    Args:
    ----
        rock_x (float): x-coordinate of the rock
        rock_y (float): y-coordinate of the rock
        rock_diameter (float): diameter of the rock
        camera_center_x (float): x-coordinate of the camera
        camera_center_y (float): y-coordinate of the camera
        camera_size (float): size of the camera
        size_x (int): size of the x-axis
        size_y (int): size of the y-axis

    Returns:
    -------
        Tuple[int, int, int]: x-coordinate, y-coordinate, diameter of the rock in pixel

    """
    rock_pixel_x = int((rock_x - camera_center_x + camera_size / 2) / camera_size * size_x)
    rock_pixel_y = int((rock_y - camera_center_y + camera_size / 2) / camera_size * size_y)
    rock_diameter_pixel = int(rock_diameter / camera_size * size_x)
    return rock_pixel_x, rock_pixel_y, rock_diameter_pixel


def create_bounding_boxes_dataset(dataset_path: str) -> None:
    """Create bounding boxes for rocks in the dataset

    Args:
    ----
        dataset_path (str): Path to the dataset

    """
    params_path = os.path.join(dataset_path, "adjusted_dataset_config.json")
    with open(params_path) as f:
        params = json.load(f)
    size_x = params["rendering"]["resolution_x"]
    size_y = params["rendering"]["resolution_y"]

    print(f"Creating bounding boxes for dataset {dataset_path}. Size: {size_x}x{size_y}")

    mesh_paths_len = len([mesh_folder for mesh_folder in os.listdir(dataset_path) if mesh_folder.startswith("mesh_")])
    print(f"Found {mesh_paths_len} mesh folders in {dataset_path}")
    for mesh_folder in os.listdir(dataset_path):
        if not mesh_folder.startswith("mesh_"):
            continue
        mesh_path = os.path.join(dataset_path, mesh_folder)
        terrain_len = len(
            [terrain_folder for terrain_folder in os.listdir(mesh_path) if terrain_folder.startswith("terrain_")]
        )
        print(f"Found {terrain_len} terrain folders in {mesh_path}")
        for terrain_folder in os.listdir(mesh_path):
            if not terrain_folder.startswith("terrain_"):
                continue
            terrain_path = os.path.join(mesh_path, terrain_folder)

            case_path = os.path.join(terrain_path, "params.json")
            with open(case_path) as f:
                rendering_cases = json.load(f)

            rock_field_path = os.path.join(terrain_path, "rock_field.csv")
            with open(rock_field_path) as f:
                rock_field = pd.read_csv(f)
            print(f"Found {len(rock_field)} rocks in {rock_field_path}")

            crater_field_path = os.path.join(terrain_path, "crater_field.csv")
            with open(crater_field_path) as f:
                crater_field = pd.read_csv(f)
            print(f"Found {len(crater_field)} craters in {crater_field_path}")

            print(f"Creating bounding boxes for {terrain_path}")
            create_bounding_boxes(
                rock_field,
                crater_field,
                rendering_cases,
                size_x,
                size_y,
                terrain_path,
                output_json=os.path.join(terrain_path, "params_with_bounding_boxes.json"),
            )


def main():
    parser = argparse.ArgumentParser(description="Create bounding boxes for rocks")
    parser.add_argument("dataset_path", type=str, help="Path to dataset")
    args = parser.parse_args()

    create_bounding_boxes_dataset(args.dataset_path)


if __name__ == "__main__":
    main()
