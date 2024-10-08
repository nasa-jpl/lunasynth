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
from pathlib import Path

import rasterio
from rasterio.windows import Window

# Example oneliner to cut all tiff files in a folder:
# $ for file in ../moon_data/new_pgda78/*.tif; do poetry run python src/data_tools/cut_tiff.py $file "${file%.*}" --piece_size_km 2.0; done # noqa: E501


def cut_raster_into_pieces(input_tiff: str, output_folder: str, piece_size_km: float = 1):
    """Cut a TIFF file into square pieces of a given size.

    Args:
    ----
        input_tiff (str): Path to the input TIFF file.
        output_folder (str): Path to the output folder.
        piece_size_km (float): Size of the pieces in kilometers. Default is 1.

    """
    print(f"Cutting the raster into {piece_size_km} km x {piece_size_km} km pieces")

    # Open the input TIFF file
    with rasterio.open(input_tiff) as src:
        # Calculate the piece size in pixels
        piece_size_m = piece_size_km * 1000  # Convert km to meters
        pixel_size_x, pixel_size_y = src.res[0], abs(src.res[1])  # Pixel size in meters
        piece_size_pixels_x = int(piece_size_m / pixel_size_x)
        piece_size_pixels_y = int(piece_size_m / pixel_size_y)

        # Get the number of pieces in x and y direction
        num_pieces_x = src.width // piece_size_pixels_x
        num_pieces_y = src.height // piece_size_pixels_y

        print(f"Cutting the raster into {num_pieces_x} x {num_pieces_y} pieces")

        # Iterate over each piece and save as a new TIFF
        for i in range(num_pieces_x):
            for j in range(num_pieces_y):
                window = Window(
                    i * piece_size_pixels_x,
                    j * piece_size_pixels_y,
                    piece_size_pixels_x,
                    piece_size_pixels_y,
                )
                transform = src.window_transform(window)

                # Define output file name
                input_name = str(Path(input_tiff).stem)
                output_filename = os.path.join(output_folder, f"{input_name}_piece_{i}_{j}.tif")

                # Read the window from the source file
                data = src.read(window=window)

                # Write the piece to a new TIFF file
                with rasterio.open(
                    output_filename,
                    "w",
                    driver="GTiff",
                    height=piece_size_pixels_y,
                    width=piece_size_pixels_x,
                    count=src.count,
                    dtype=src.dtypes[0],
                    crs=src.crs,
                    transform=transform,
                ) as dst:
                    dst.write(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cut a TIFF file into 1km x 1km pieces.")
    parser.add_argument("input_tiff", type=str, help="Path to the input TIFF file")
    parser.add_argument("output_folder", type=str, help="Path to the output folder")
    parser.add_argument("--piece_size_km", type=float, default=1, help="Size of the pieces in km")
    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)
    cut_raster_into_pieces(args.input_tiff, args.output_folder, args.piece_size_km)
