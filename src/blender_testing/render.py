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
def render(blender_filename):
    import bpy

    bpy.ops.wm.open_mainfile(filepath=blender_filename)
    bpy.context.scene.render.filepath = blender_filename.replace(".blend", ".png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render given file with blender")
    parser.add_argument("file", help="file to render")
    args = parser.parse_args()
    render(args.file)

# Usage: python render.py file.blend
# you need to install bpy: pip install bpy
