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
# open and show the depth map

# Path: src/view_hdf_depth.py

import argparse

import h5py
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="View depth map from hdf5 file.")
    parser.add_argument("hdf5_file", type=str, help="The hdf5 file to view.")
    args = parser.parse_args()

    with h5py.File(args.hdf5_file, "r") as f:
        # list channels in file
        print(list(f.keys()))
        depth = f["V"][:]

    # show depth map
    depth[depth > 1000] = np.nan
    plt.imshow(depth, cmap="magma")
    plt.colorbar()
    plt.show()


if __name__ == "__main__":
    main()
