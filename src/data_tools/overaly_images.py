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

from PIL import Image


def overlay_images(base_image_path, overlay_image_path, output_path, scale, rotation, margin):
    # Open the base image
    base_image = Image.open(base_image_path).convert("RGBA")

    # Open the overlay image
    overlay_image = Image.open(overlay_image_path).convert("RGBA")

    # Scale the overlay image to a percentage of the base image size
    base_width, base_height = base_image.size
    overlay_image = overlay_image.resize((int(base_width * scale), int(base_height * scale)), Image.LANCZOS)

    # Rotate the overlay image
    overlay_image = overlay_image.rotate(rotation, expand=True)

    # Calculate position to paste the overlay image (top right corner with margin)
    overlay_width, overlay_height = overlay_image.size
    position = (base_width - overlay_width - margin, margin)

    # Create a new image with the same size as the base image and an alpha layer (transparent)
    combined_image = Image.new("RGBA", base_image.size)
    combined_image.paste(base_image, (0, 0))
    combined_image.paste(overlay_image, position, overlay_image)

    # Save the combined image
    combined_image.save(output_path, format="PNG")


def main():
    parser = argparse.ArgumentParser(
        description="Overlay a given PNG onto another PNG with scaling, rotation, margin, and an arrow."
    )
    parser.add_argument("base_image", type=str, help="Path to the base image (PNG).")
    parser.add_argument("overlay_image", type=str, help="Path to the overlay image (PNG).")
    parser.add_argument("output_image", type=str, help="Path to save the output image (PNG).")
    parser.add_argument(
        "--scale",
        type=float,
        default=0.2,
        help="Scaling factor for the overlay image relative to the base image size (default is 0.2).",
    )
    parser.add_argument(
        "--rotation",
        type=float,
        default=0.0,
        help="Rotation angle for the overlay image in degrees (default is 0.0).",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=10,
        help="Margin from the top right corner for the overlay image (default is 10 pixels).",
    )

    args = parser.parse_args()

    overlay_images(
        args.base_image,
        args.overlay_image,
        args.output_image,
        args.scale,
        args.rotation,
        args.margin,
        args.arrow_rotation,
    )


if __name__ == "__main__":
    main()
