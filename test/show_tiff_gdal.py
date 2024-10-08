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
import os

import humanize
import matplotlib.pyplot as plt
import numpy as np
from osgeo import gdal

# Open the TIFF file
tiff_file = "../moon_data/pgda/LM7_final_adj_5mpp_surf.tif"
dataset = gdal.Open(tiff_file)

# Read the raster bands as arrays
band = dataset.GetRasterBand(1)
array = band.ReadAsArray()

# Get image size (dimensions)
width = dataset.RasterXSize
height = dataset.RasterYSize

print(f"Image dimensions: {width} x {height}")

# Get the image size in bytes
file_size = os.path.getsize(tiff_file)
print(f"Image size: {humanize.naturalsize(file_size)}")

# Display the image
plt.imshow(array, cmap="gray")
plt.title("TIFF Image")
plt.axis("off")
plt.show()

# show the image in 3d

fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")
x = np.linspace(0, width, width)
y = np.linspace(0, height, height)
X, Y = np.meshgrid(x, y)
ax.plot_surface(X, Y, array, cmap="gray")
# equal aspect ratio
# ax.set_box_aspect([1, 1, 1])
plt.title("TIFF Image 3D")
plt.show()
