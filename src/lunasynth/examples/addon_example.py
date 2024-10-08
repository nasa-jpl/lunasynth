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
import bpy
from bpy.props import EnumProperty, FloatProperty, StringProperty

bl_info = {
    "name": "Parameter List Addon",
    "blender": (2, 80, 0),
    "category": "Object",
}
# Define the different parameter types
parameter_types = [("NORMAL", "Normal", ""), ("UNIFORM", "Uniform", "")]


# Operator to add a new parameter
class OBJECT_OT_add_parameter(bpy.types.Operator):
    bl_idname = "object.add_parameter"
    bl_label = "Add Parameter"
    bl_options = {"REGISTER", "UNDO"}

    param_type: EnumProperty(  # type: ignore[valid-type]
        name="Parameter Type",
        description="Choose the type of the parameter",
        items=parameter_types,
        default="NORMAL",
    )  # type: ignore[valid-type]
    mean: FloatProperty(name="Mean", default=0.0)  # type: ignore[valid-type]
    std: FloatProperty(name="Standard Deviation", default=1.0)  # type: ignore[valid-type]
    min: FloatProperty(name="Min", default=0.0)  # type: ignore[valid-type]
    max: FloatProperty(name="Max", default=1.0)  # type: ignore[valid-type]

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "param_type")
        if self.param_type == "NORMAL":
            layout.prop(self, "mean")
            layout.prop(self, "std")
        elif self.param_type == "UNIFORM":
            layout.prop(self, "min")
            layout.prop(self, "max")

    def execute(self, context):
        param_list = context.scene.param_list
        new_param = param_list.add()
        new_param.name = f"param_{len(param_list)}"
        new_param.param_type = self.param_type
        if self.param_type == "NORMAL":
            new_param.value1 = self.mean
            new_param.value2 = self.std
        elif self.param_type == "UNIFORM":
            new_param.value1 = self.min
            new_param.value2 = self.max
        return {"FINISHED"}


# UI panel to display the parameters
class OBJECT_PT_parameter_list(bpy.types.Panel):
    bl_idname = "OBJECT_PT_parameter_list"
    bl_label = "Parameter List"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Parameters"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.operator("object.add_parameter", text="Add Parameter")

        for param in scene.param_list:
            box = layout.box()
            row = box.row()
            row.prop(param, "name")
            row.prop(param, "param_type", text="")
            if param.param_type == "NORMAL":
                row = box.row()
                row.prop(param, "value1", text="Mean")
                row.prop(param, "value2", text="Std")
            elif param.param_type == "UNIFORM":
                row = box.row()
                row.prop(param, "value1", text="Min")
                row.prop(param, "value2", text="Max")


# Custom property group for parameters
class ParameterItem(bpy.types.PropertyGroup):
    name: StringProperty()  # type: ignore[valid-type]
    param_type: EnumProperty(name="Parameter Type", description="Type of parameter", items=parameter_types)  # type: ignore[valid-type]
    value1: FloatProperty()  # type: ignore[valid-type]
    value2: FloatProperty()  # type: ignore[valid-type]


# Registering classes and properties
def register():
    bpy.utils.register_class(OBJECT_OT_add_parameter)
    bpy.utils.register_class(OBJECT_PT_parameter_list)
    bpy.utils.register_class(ParameterItem)
    bpy.types.Scene.param_list = bpy.props.CollectionProperty(type=ParameterItem)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_add_parameter)
    bpy.utils.unregister_class(OBJECT_PT_parameter_list)
    bpy.utils.unregister_class(ParameterItem)
    del bpy.types.Scene.param_list


if __name__ == "__main__":
    register()
