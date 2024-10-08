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
import math

import numpy as np
import rasterio as rio
from rasterio.warp import transform
from scipy.ndimage import zoom


class DEM:
    """A class to represent a Digital Elevation Model (DEM)."""

    def __init__(self, file_path):
        """Initialize a DEM object from a given file path.

        Args:
        ----
        file_path (str): Path to the DEM file (GeoTIFF)

        """
        self.file_path = file_path
        self.dataset = rio.open(file_path)
        self.band1 = self.dataset.read(1)
        self.res = self.dataset.res
        self.meta = self.dataset.meta
        self.crs = self.dataset.crs
        self.bounds = self.dataset.bounds
        self.transform = self.dataset.transform
        self.profile = self.dataset.profile
        self.width = self.dataset.width
        self.height = self.dataset.height

    def __str__(self):
        return f"DEM: {self.file_path}"

    def __repr__(self):
        return f"DEM({self.file_path})"

    def __del__(self):
        self.dataset.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.dataset.close()

    def show(self):
        rio.plot.show(self.band1, title=self.file_path)

    def save(self, file_path):
        with rio.open(file_path, "w", **self.meta) as dst:
            dst.write(self.band1, 1)

    def crop(self, x1: float, y1: float, x2: float, y2: float):
        """Crop the DEM to a given bounding box.

        Args:
        ----
            x1 (float): Left coordinate of the bounding box
            y1 (float): Top coordinate of the bounding box
            x2 (float): Right coordinate of the bounding box
            y2 (float): Bottom coordinate of the bounding box

        Raises:
        ------
            ValueError: If the bounding box is outside the DEM bounds

        """
        assert x1 < x2, "x1 must be less than x2"
        assert y1 < y2, "y1 must be less than y2"
        assert x1 >= self.bounds.left, "x1 must be greater than or equal to the left bound"
        assert x2 <= self.bounds.right, "x2 must be less than or equal to the right bound"
        assert y1 >= self.bounds.top, "y1 must be greater than or equal to the top bound"
        assert y2 <= self.bounds.bottom, "y2 must be less than or equal to the bottom bound"

        cropped_array = self.band1[int(y1) : int(y2), int(x1) : int(x2)]
        new_transform = self.transform * self.transform.translation(x1, y1)
        new_meta = {
            "driver": "GTiff",
            "height": cropped_array.shape[0],
            "width": cropped_array.shape[1],
            "count": 1,
            "dtype": cropped_array.dtype,
            "crs": self.crs,
            "transform": new_transform,
        }
        self.band1 = cropped_array
        self.meta = new_meta

    def zoom(self, factor: float = 2.0):
        """Increase the resolution of the DEM by a given factor using bilinear interpolation.

        Args:
        ----
            factor (float): Zoom factor > 1 (default is 2.0)

        Raises:
        ------
            ValueError: If the zoom factor is less than or equal to 1

        """
        assert factor > 1, "Zoom factor must be greater than 1"
        zoomed_array = zoom(self.band1, factor)
        new_transform = self.transform * self.transform.scale(
            (self.width / zoomed_array.shape[-1]),
            (self.height / zoomed_array.shape[-2]),
        )
        self.meta = {
            "driver": "GTiff",
            "height": zoomed_array.shape[0],
            "width": zoomed_array.shape[1],
            "count": 1,
            "dtype": zoomed_array.dtype,
            "crs": self.crs,
            "transform": new_transform,
        }
        self.band1 = zoomed_array
        self.profile.update(
            {
                "height": zoomed_array.shape[0],
                "width": zoomed_array.shape[1],
                "transform": new_transform,
            }
        )
        self.res = (self.res[0] / factor, self.res[1] / factor)

    def analyze(self):
        print("Metadata:")
        print(self.meta)
        print("CRS:", self.crs)
        print("Bounds:", self.bounds)
        print("Transform:", self.transform)

    def get_latlong(self):
        """Get the latitude and longitude of the center of the DEM.

        Returns
        -------
            Tuple[float, float]: Latitude and longitude in radians

        """
        # from http://downloads.esri.com/support/documentation/ims_/ArcXML9/Support_files/elements/gcs.htm
        lunar_south_crs = "ESRI:103878"  # Moon 2000 South Pole Stereographic
        lunar_center_crs = "ESRI:104903"  # GCS_Moon_2000
        center_y = (self.dataset.bounds.left + self.dataset.bounds.right) / 2
        center_x = (self.dataset.bounds.top + self.dataset.bounds.bottom) / 2
        long, lat = transform(lunar_south_crs, lunar_center_crs, [center_y], [center_x])
        return math.radians(lat[0]), math.radians(long[0])


def rad_to_dms(rad):
    # Convert radians to degrees
    deg = math.degrees(rad)
    # Get the integer part of the degrees
    d = int(deg)

    # Get the fractional part and convert to minutes
    min_float = (deg - d) * 60
    m = int(min_float)

    # Get the fractional part of minutes and convert to seconds
    s = (min_float - m) * 60
    return d, m, s


def latlong_rad_to_strings(lat, long):
    d, m, s = rad_to_dms(abs(lat))
    n_s = "N" if lat > 0 else "S"
    lat_string = f"{d}°{m}'{s:.0f}\"{n_s}"
    d, m, s = rad_to_dms(long)
    # e_w = "E" if long > math.pi else "W"
    long_string = f"{d}°{m}'{s:.0f}\""
    return lat_string, long_string


def compute_sun_elevation_azimuth(latitude: float, sun_hour_normalized: float = 0.0, sun_season: float = 0.0):
    """Compute the elevation and azimuth of the sun for a given latitude, sun hour, and sun season.

    Sun hour represents the time of the day normalized to the range (-1, 1),
    where -1 is sunrise, 0 is solar noon, and 1 is sunset. Sun season represents
    the time of the year normalized to the range (-1, 1), where -1 is winter, 0 is spring,
    and 1 is summer. Lunar declination is assumed to be 1.54 degrees.

    Args:
    ----
        latitude (float): Latitude in radians
        sun_hour_normalized (float): Sun hour normalized to the range (-1, 1)
        sun_season: Sun season normalized to the range (-1, 1)

    Returns:
    -------
        Tuple[float, float]: Elevation and azimuth of the sun in radians

    """
    moon_axis_tilt = 1.54 * np.pi / 180
    moon_declination = moon_axis_tilt * sun_season

    if abs(latitude) < np.pi / 2 - abs(moon_declination):
        # Normal case, sun rises and sets. Only case for latitude < 88.46 degrees
        zero_elevation_sun_angle = np.arccos(
            -np.sin(latitude) * np.sin(moon_declination) / np.cos(latitude) / np.cos(moon_declination)
        )
    else:
        # Sun does not rise or set
        if abs(latitude + moon_declination) < np.pi / 2:
            print(f"Warning: Sun is below the horizon for latitude {latitude} and moon declination {moon_declination}")
        zero_elevation_sun_angle = np.pi

    sun_angle = zero_elevation_sun_angle * sun_hour_normalized

    Sx = np.cos(moon_declination) * np.sin(sun_angle)
    Sy = np.cos(latitude) * np.sin(moon_declination) - np.sin(latitude) * np.cos(moon_declination) * np.cos(sun_angle)
    Sz = np.sin(latitude) * np.sin(moon_declination) + np.cos(latitude) * np.cos(moon_declination) * np.cos(sun_angle)
    elevation = np.arcsin(Sz)
    azimuth = np.arctan2(-Sx, -Sy)
    return elevation, azimuth
