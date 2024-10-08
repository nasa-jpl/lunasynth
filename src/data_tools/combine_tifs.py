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

import numpy as np
import rasterio
from matplotlib import pyplot as plt


# File paths
def main() -> None:
    parser = argparse.ArgumentParser(description="Combine two tifs using alpha blending")
    parser.add_argument("--tif1", type=str, help="Path to first tif file")
    parser.add_argument("--tif2", type=str, help="Path to second tif file")
    parser.add_argument("--output", type=str, default=None, help="Path to the output blended image")
    parser.add_argument("--alpha", type=float, default=0.5, help="Alpha blending")
    parser.add_argument("--plot", action="store_true", help="Plot the blended image")
    args = parser.parse_args()

    tif1_path = args.tif1
    tif2_path = args.tif2
    if args.output is None:
        output_path = tif1_path.replace(".tif", "_blended.tif")
    else:
        output_path = args.output

    # Read tif1
    with rasterio.open(tif1_path) as tif1_src:
        tif1 = tif1_src.read(1)

    # Read color relief
    with rasterio.open(tif2_path) as tif2_src:
        tif2 = tif2_src.read([1, 2, 3])  # Read RGB bands
        tif2_profile = tif2_src.profile

    # Normalize tif1 to range [0, 1]
    tif1_normalized = tif1 / 255.0

    # Normalize color relief to range [0, 1]
    tif2_normalized = tif2 / 255.0

    # Alpha blending
    alpha = args.alpha
    blended = (1 - alpha) * tif2_normalized + alpha * tif1_normalized

    # Clip values to range [0, 255] and convert to uint8
    blended = np.clip(blended * 255, 0, 255).astype(np.uint8)

    # Update profile for output
    output_profile = tif2_profile
    output_profile.update(dtype=rasterio.uint8, count=3)

    # Write blended image to a new file
    with rasterio.open(output_path, "w", **output_profile) as dst:
        dst.write(blended[0], 1)
        dst.write(blended[1], 2)
        dst.write(blended[2], 3)
    print(f"Blended image saved to {output_path}")

    if args.plot:
        # Plot and save the blended image
        plt.figure(figsize=(10, 10))
        plt.imshow(np.moveaxis(blended, 0, -1))  # Rearrange dimensions to (height, width, RGB)
        plt.axis("off")
        plt.show()


if __name__ == "__main__":
    main()
