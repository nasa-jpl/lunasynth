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
from datetime import datetime
from enum import Enum
from pathlib import Path

import bpy
import yaml

# import bpy.lib
from bpy.props import (  # type: ignore[attr-defined]
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

# activate virtual environment or define VIRTUAL_ENV environment variable
# cd to lunasynth root directory
# poetry shell
# blender --python src/lunasynth/add_rocks_blender_addon.py

venv_path = os.environ.get("VIRTUAL_ENV")
if venv_path is None:
    print("Error activating virtual environment")
    sys.exit(1)
python_version = "python" + str(sys.version_info.major) + "." + str(sys.version_info.minor)
site_packages_path = os.path.join(venv_path, "lib", python_version, "site-packages")
sys.path.append(site_packages_path)

# add path to lunasynth module
lunasynth_root = os.environ.get("PWD")
if lunasynth_root is None:
    print("Error getting lunasynth root directory")
    sys.exit(1)
luna_synth_path = lunasynth_root + "/src/"
sys.path.append(luna_synth_path)

import lunasynth.blender_helper as blender_helper  # noqa: E402
from lunasynth.configuration_manager import RenderingManager  # noqa: E402

config_path = lunasynth_root + "/config/render_distributions"
config_files = [f for f in os.listdir(config_path) if f.endswith(".yaml")]
config_files_enum = [(f, f, "") for f in config_files]

render_config_path = lunasynth_root + "/config/rendering"
render_files = [f for f in os.listdir(render_config_path) if f.endswith(".yaml")]
render_files_enum = [(f, f, "") for f in render_files]


# Define the different parameter types
parameter_types = [
    ("NORMAL", "Normal", ""),
    ("UNIFORM", "Uniform", ""),
    ("FIXED", "Fixed", ""),
    ("LIST", "List", ""),
    ("GRID", "Grid", ""),
]

bl_info = {
    "name": "lunasynth: add cases",
    "author": "Daniel Pastor",
    "version": (0, 1, 0),
    "blender": (4, 1, 0),
    "location": "View3D > UI > LunaSynth",
    "category": "Object",
    "description": "Add cases to render",
}


class ParameterType(Enum):
    # use fixed, normal, uniform, list, grid
    FIXED = 0
    NORMAL = 1
    UNIFORM = 2
    LIST = 3
    GRID = 4


def str2param_type(param_type: str) -> ParameterType:
    if param_type == "fixed":
        return ParameterType.FIXED
    elif param_type == "normal":
        return ParameterType.NORMAL
    elif param_type == "uniform":
        return ParameterType.UNIFORM
    elif param_type == "list":
        return ParameterType.LIST
    elif param_type == "grid":
        return ParameterType.GRID
    else:
        msg = f"Unknown parameter type {param_type}"
        raise ValueError(msg)


class Parameter:
    def __init__(self, name: str, param_type: ParameterType, values: dict[str, float]):
        self.name = name
        self.param_type = param_type
        self.values = values


class SamplingValues:
    def __init__(self):
        self.values = {}

    def add_value(self, name: str, param_type: ParameterType, values: dict[str, float]):
        self.values[name] = Parameter(name, param_type, values)


class SamplingConfig:
    def __init__(self):
        self.render_distributions = SamplingValues()
        self.cases = 10


class ParameterItem(bpy.types.PropertyGroup):
    name: StringProperty()  # type: ignore[valid-type]
    param_type: EnumProperty(name="Parameter Type", description="Type of parameter", items=parameter_types)  # type: ignore[valid-type]
    value1: FloatProperty()  # type: ignore[valid-type]
    value2: FloatProperty()  # type: ignore[valid-type]
    values: StringProperty()  # type: ignore[valid-type]
    n_values: IntProperty()  # type: ignore[valid-type]


def config_from_item_list(item_list):
    param_list = item_list.param_list
    config = {}
    config["cases"] = item_list.n_cases
    config["render_distributions"] = {}
    for param in param_list:
        param_name = param.name
        param_type = param.param_type
        if param_type == "NORMAL":
            config["render_distributions"][param_name] = {
                "type": "normal",
                "mean": param.value1,
                "std": param.value2,
            }
        elif param_type == "UNIFORM":
            config["render_distributions"][param_name] = {
                "type": "uniform",
                "min": param.value1,
                "max": param.value2,
            }
        elif param_type == "FIXED":
            config["render_distributions"][param_name] = {
                "type": "fixed",
                "value": param.value1,
            }
        elif param_type == "LIST":
            config["render_distributions"][param_name] = {
                "type": "list",
                "values": [float(p) for p in param.values.split(",")],
            }
        elif param_type == "GRID":
            config["render_distributions"][param_name] = {
                "type": "grid",
                "min": param.value1,
                "max": param.value2,
                "n_values": param.n_values,
            }
        else:
            msg = f"Unknown parameter type {param_type}"
            raise ValueError(msg)
    config["depth_output"] = True
    config["segmentation_output"] = True
    return config


class AddCasesOperator(bpy.types.Operator):
    """Add Cases"""

    bl_idname = "object.add_cases_operator"
    bl_label = "Add Case"

    def execute(self, context):
        # config_file = os.path.join(config_path, context.scene.item_list.config_name)
        # with open(config_file, "r") as f:
        #     config = yaml.safe_load(f)

        config = config_from_item_list(context.scene.item_list)

        cases_dict = {}
        rendering_manager = RenderingManager({})
        cases_dict["cases_list"] = rendering_manager.generate_rendering_cases(
            config["render_distributions"], n_cases=config["cases"], camera_type="PERSP"
        )

        case_cone_size = context.scene.item_list.case_marker_size
        blender_helper.add_cases_visalization(
            cases_dict["cases_list"], case_cone_size=case_cone_size, connect_cases=False
        )
        return {"FINISHED"}


class DeleteCasesOperator(bpy.types.Operator):
    """Delete Cases"""

    bl_idname = "object.delete_cases_operator"
    bl_label = "Delete Cases"

    def execute(self, context):
        return {"FINISHED"}


class RenderCasesOperator(bpy.types.Operator):
    """Render Cases"""

    bl_idname = "object.render_cases_operator"
    bl_label = "Render Cases"

    def execute(self, context):
        config = config_from_item_list(context.scene.item_list)
        # render_type_name = context.scene.item_list.render_type_name
        config_name = context.scene.item_list.config_name
        if "output_dir" not in config:
            # add current time to output dir
            config["output_dir"] = str(
                Path("render_jobs")
                / Path(str(Path(config_name).stem) + "_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
            )

        cases_dict = {
            "cases_config_file": config_name,
            "cases_config": config,
            "blend_file": bpy.data.filepath,
            "cases_list": [],
        }
        configuration_manager = RenderingManager({})
        cases_dict["cases_list"] = configuration_manager.generate_rendering_cases(config)
        configuration_manager.setup_rendering(config)
        configuration_manager.run_rendering_campaign(cases_dict)

        return {"FINISHED"}


class SamplingCasesPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_label = "Create Render Cases"
    bl_idname = "OBJECT_PT_sampling_cases_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LuNaSynth"

    def draw(self, context):
        layout = self.layout
        item_list = context.scene.item_list

        layout.prop(item_list, "n_cases")
        layout.prop(item_list, "config_name")
        layout.prop(item_list, "case_marker_size")

        if item_list.param_list is not None and len(item_list.param_list) > 0:
            for param in item_list.param_list:
                box = layout.box()
                row = box.row()
                # row.prop(param, "name")
                row.prop(param, "param_type", text=f"{param.name} type:")
                if param.param_type == "NORMAL":
                    row = box.row()
                    row.prop(param, "value1", text="Mean")
                    row.prop(param, "value2", text="Std")
                elif param.param_type == "UNIFORM":
                    row = box.row()
                    row.prop(param, "value1", text="Min")
                    row.prop(param, "value2", text="Max")
                elif param.param_type == "FIXED":
                    row = box.row()
                    row.prop(param, "value1", text="Value")
                elif param.param_type == "LIST":
                    row = box.row()
                    row.prop(param, "values")
                elif param.param_type == "GRID":
                    row = box.row()
                    row.prop(param, "value1", text="Min")
                    row.prop(param, "value2", text="Max")
                    row.prop(param, "n_values", text="Number Values")

        layout.operator("object.add_cases_operator", text="Add Cases")
        layout.operator("object.save_file", text="Save Blend File")
        layout.operator("object.delete_cases_operator", text="Delete Cases")

        layout.prop(item_list, "render_type_name")
        layout.operator("object.render_cases_operator", text="Render Cases")


class OBJECT_OT_save_cases_file(bpy.types.Operator):
    bl_idname = "object.save_file"
    bl_label = "Save Cases File"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore[valid-type]
    bl_options = {"REGISTER"}

    def execute(self, context):
        filepath = self.filepath

        print(f"Saving file to {filepath}")
        config = config_from_item_list(context.scene.item_list)

        # save the config file
        with open(filepath, "w") as f:
            yaml.dump(config, f)

        self.report({"INFO"}, "File saved successfully")
        return {"FINISHED"}

    def invoke(self, context, event):
        # Use Blender's file browser to select the file path
        # set the file path to current config file
        self.filepath = os.path.join(config_path, context.scene.item_list.config_name)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def update_param_type(self, context):
    set_paramms_from_config(self.config_name, context.scene.item_list)


def load_config_startup():
    print("Loading config files ss")
    for scene in bpy.data.scenes:
        load_config_startup(scene)
        print("Loading config file")
        set_paramms_from_config(scene.item_list.config_name, scene.item_list)
    return 1.0


def set_paramms_from_config(config_name, item_list):
    print(f"Parameter type changed to {config_name}")

    config_file = os.path.join(config_path, config_name)
    # load the config file
    print(f"Loading config file {config_file}")
    with open(config_file) as f:
        config = yaml.safe_load(f)
    item_list.config = config

    # update the parameter list
    param_list = item_list.param_list

    param_list.clear()

    for param_name, param_values in config["render_distributions"].items():
        new_param = param_list.add()
        new_param.name = param_name
        param_type = param_values["type"].upper()
        print(f"Adding parameter {param_name} of type {param_type}")
        new_param.param_type = param_type
        if new_param.param_type == "FIXED":
            new_param.value1 = param_values["value"]
        elif new_param.param_type == "NORMAL":
            new_param.value1 = param_values["mean"]
            new_param.value2 = param_values["std"]
        elif new_param.param_type == "UNIFORM":
            new_param.value1 = param_values["min"]
            new_param.value2 = param_values["max"]
        elif new_param.param_type == "LIST":
            new_param.values = param_values["values"]
        elif new_param.param_type == "GRID":
            new_param.value1 = param_values["min"]
            new_param.value2 = param_values["max"]
            new_param.n_values = param_values["n_values"]


class SamplingCasesItem(bpy.types.PropertyGroup):
    # config_name: enum from config_files
    config_name: EnumProperty(  # type: ignore[valid-type]
        name="Config File",
        description="Config file to use for sampling",
        items=config_files_enum,
        update=update_param_type,  # Set the update callback
    )  # type: ignore[valid-type]
    config: dict
    n_cases: IntProperty(name="Number of Cases", default=10, min=1)  # type: ignore[valid-type]
    case_marker_size: FloatProperty(name="Case Marker Size", default=20.0, min=0.1)  # type: ignore[valid-type]
    param_list: bpy.props.CollectionProperty(type=ParameterItem)  # type: ignore[valid-type]
    render_type_name: EnumProperty(  # type: ignore[valid-type]
        name="Render Config File",
        description="Config file to use for rendering",
        items=render_files_enum,
    )  # type: ignore[valid-type]


def register():
    bpy.utils.register_class(AddCasesOperator)
    bpy.utils.register_class(DeleteCasesOperator)
    bpy.utils.register_class(OBJECT_OT_save_cases_file)
    bpy.utils.register_class(SamplingCasesPanel)
    bpy.utils.register_class(ParameterItem)
    bpy.utils.register_class(SamplingCasesItem)
    bpy.utils.register_class(RenderCasesOperator)
    bpy.types.Scene.item_list = bpy.props.PointerProperty(type=SamplingCasesItem)

    # if bpy.app.background:
    # return
    # for scene in bpy.data.scenes:
    #     load_config_startup(scene)
    bpy.app.timers.register(load_config_startup, first_interval=0.4)
    # bpy.app.handlers.load_post.append(load_config_startup, "")


def unregister():
    bpy.utils.unregister_class(AddCasesOperator)
    bpy.utils.unregister_class(DeleteCasesOperator)
    bpy.utils.unregister_class(OBJECT_OT_save_cases_file)
    bpy.utils.unregister_class(SamplingCasesPanel)
    bpy.utils.unregister_class(SamplingCasesItem)
    bpy.utils.unregister_class(RenderCasesOperator)
    del bpy.types.Scene.item_list
    bpy.utils.unregister_class(ParameterItem)


if __name__ == "__main__":
    register()
