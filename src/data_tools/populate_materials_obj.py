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

# find all obj files in this folder. If the obj file has a corresponding mtl file,
# then load the mtl file and assign it to the obj file. If the obj file does not have a corresponding mtl file,
# then create a new material and assign it to the obj file.

import os
from pathlib import Path


def populate_materials_obj(obj_directory, ref_mtl_filepath: str = "ref.mtl") -> None:
    # Check if the ref.mtl file exists using Path
    if not Path(ref_mtl_filepath).is_file():
        print(f"Reference material file {ref_mtl_filepath} not found.")
        return

    print(f"Populating materials for obj files in {obj_directory}")
    for file in os.listdir(obj_directory):
        if file.endswith(".obj"):
            obj_filepath = os.path.join(obj_directory, file)
            mtl_filepath = os.path.splitext(obj_filepath)[0] + ".mtl"

            if not os.path.exists(mtl_filepath):
                # copy ref.mat to obj_filename.mat
                with open(os.path.join(obj_directory, "ref.mtl")) as ref_file:
                    with open(mtl_filepath, "w") as new_file:
                        new_file.write(ref_file.read())
                print(f"Created {mtl_filepath}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Populate materials for obj files in a directory.")
    parser.add_argument("obj_directory", help="Directory containing obj files.")
    parser.add_argument("-r", default="ref.mtl", help="Reference material file path.")
    args = parser.parse_args()
    populate_materials_obj(args.obj_directory, args.r)


if __name__ == "__main__":
    main()
