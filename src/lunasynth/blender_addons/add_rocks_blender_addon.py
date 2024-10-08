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

# add path of this script to the path so we can import the terrain_enhancement module
import sys

import bpy
from bpy.props import FloatProperty, PointerProperty

# activate virtual environment or define VIRTUAL_ENV environment variable
# cd to lunasynth root directory
# poetry shell
# blender --python src/lunasynth/add_rocks_blender_addon.py

venv_path = os.environ.get("VIRTUAL_ENV")
if venv_path is None:
    print("Activating virtual environment")
    print("Error activating virtual environment")
    sys.exit(1)
python_version = "python" + str(sys.version_info.major) + "." + str(sys.version_info.minor)
site_packages_path = os.path.join(venv_path, "lib", python_version, "site-packages")
sys.path.append(site_packages_path)

# add path to lunasynth module
lunasynth_root = os.environ.get("PWD")
if lunasynth_root is None:
    print("Error: PWD environment variable not set")
    sys.exit(1)
luna_synth_path = lunasynth_root + "/src/"
sys.path.append(luna_synth_path)
asset_directory = lunasynth_root + "/assets/rocks/earth_scanned"

import lunasynth.terrain_enhancement as terrain_enhancement  # noqa: E402

rock_field = terrain_enhancement.RockField()

bl_info = {
    "name": "lunasynth: add rock field",
    "author": "Daniel Pastor",
    "version": (0, 1, 0),
    "blender": (4, 1, 0),
    "location": "View3D > UI > LunaSynth",
    "category": "Object",
    "description": "Add rocks to a mesh following moon distribution",
}


def get_mesh_bounds(obj):
    if obj.type == "MESH":
        # Get the object's world matrix
        world_matrix = obj.matrix_world
        # Transform all vertex coordinates to global coordinates
        global_coords = [world_matrix @ v.co for v in obj.data.vertices]
        # Calculate the bounding box in global coordinates
        xmin = min(global_coords, key=lambda v: v.x).x
        xmax = max(global_coords, key=lambda v: v.x).x
        ymin = min(global_coords, key=lambda v: v.y).y
        ymax = max(global_coords, key=lambda v: v.y).y
        zmin = min(global_coords, key=lambda v: v.z).z
        zmax = max(global_coords, key=lambda v: v.z).z
        return (xmin, ymin, zmin), (xmax, ymax, zmax)
    else:
        msg = "The provided object is not a mesh."
        raise TypeError(msg)


class AddRocksOperator(bpy.types.Operator):
    """Add Rocks To Mesh Following moon distribution"""

    bl_idname = "object.add_rocks_operator"
    bl_label = "Add Rocks To Mesh"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        h_max = 6
        add_rocks_item = context.scene.add_rocks_item
        # get xinit, yinit, xend, yend from target mesh
        if add_rocks_item.target_mesh is None:
            print("No target mesh selected")
            return {"FINISHED"}
        (xmin, ymin, zmin), (xmax, ymax, zmax) = get_mesh_bounds(add_rocks_item.target_mesh)
        print(f"Using target mesh: {add_rocks_item.target_mesh.name}")
        size_x = xmax - xmin
        size_y = ymax - ymin
        print(f"Mesh bounds: {xmin}, {ymin}, {zmin}, {xmax}, {ymax}, {zmax}")
        rock_field.generate_rock_field(
            add_rocks_item.rock_density,
            size_x,
            size_y,
            add_rocks_item.h_min,
            h_max,
            x_init=xmin,
            y_init=ymin,
        )

        rock_field.place_rocks(
            rock_field.rocks,
            asset_directory,
            target_mesh=add_rocks_item.target_mesh,
        )

        return {"FINISHED"}


class DeleteRocksOperator(bpy.types.Operator):
    """Delete Rocks From Mesh"""

    bl_idname = "object.delete_rocks_operator"
    bl_label = "Delete Rocks From Mesh"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        terrain_enhancement.delete_rocks()
        return {"FINISHED"}


class AddRocksPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_label = "Add Rocks Panel"
    bl_idname = "OBJECT_PT_add_rocks_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LuNaSynth"

    def draw(self, context):
        layout = self.layout
        item_list = context.scene.add_rocks_item

        layout.prop(item_list, "rock_density")
        layout.prop(item_list, "h_min")
        layout.prop(item_list, "target_mesh")
        layout.operator("object.add_rocks_operator")
        layout.operator("object.delete_rocks_operator")


class AddRocksItem(bpy.types.PropertyGroup):
    rock_density: FloatProperty(name="Rock Density", default=0.06, min=0.01, max=1)  # type: ignore[valid-type]
    rock_field_extension: FloatProperty(name="Rock Field Exentsion", default=1.0, min=0, max=1)  # type: ignore[valid-type]
    h_min: FloatProperty(name="H Min", default=0.4, min=0.1)  # type: ignore[valid-type]
    target_mesh: PointerProperty(name="Target Mesh", type=bpy.types.Object)  # type: ignore[valid-type]


def register():
    bpy.utils.register_class(AddRocksOperator)
    bpy.utils.register_class(DeleteRocksOperator)
    bpy.utils.register_class(AddRocksPanel)
    bpy.utils.register_class(AddRocksItem)
    bpy.types.Scene.add_rocks_item = bpy.props.PointerProperty(type=AddRocksItem)


def unregister():
    bpy.utils.unregister_class(AddRocksOperator)
    bpy.utils.unregister_class(DeleteRocksOperator)
    bpy.utils.unregister_class(AddRocksPanel)
    bpy.utils.unregister_class(AddRocksItem)
    del bpy.types.Scene.add_rocks_item


if __name__ == "__main__":
    register()
