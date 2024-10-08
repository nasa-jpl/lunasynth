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

import rasterio
from rasterio.enums import Resampling


def interpolate_geotiff(input_path, output_path, factor):
    with rasterio.open(input_path) as src:
        data = src.read(
            out_shape=(src.count, int(src.height * factor), int(src.width * factor)),
            resampling=Resampling.bilinear,
        )

        transform = src.transform * src.transform.scale((src.width / data.shape[-1]), (src.height / data.shape[-2]))

        profile = src.profile
        profile.update({"height": data.shape[1], "width": data.shape[2], "transform": transform})

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data)


def main():
    parser = argparse.ArgumentParser(description="Interpolate a GeoTIFF file by a specified factor.")
    parser.add_argument("input", type=str, help="Path to the input GeoTIFF file.")
    parser.add_argument("output", type=str, help="Path to the output GeoTIFF file.")
    parser.add_argument("--factor", type=float, default=5.0, help="Interpolation factor.")

    args = parser.parse_args()

    interpolate_geotiff(args.input, args.output, args.factor)


if __name__ == "__main__":
    main()
