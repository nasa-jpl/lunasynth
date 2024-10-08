#!/usr/bin/env python
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

import colorsys
import logging
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

# Implementation note: Blender keeps its own state,
# so we don't need to keep track of the state of the scene in this module.
import bpy
import numpy as np
import tqdm
import yaml
from lunasynth.dem_tools import DEM

# set logging for render to a different file and not the terminal
logging.basicConfig(
    filename="blender_render.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


class CaptureOutput:
    def __init__(self, log_filename):
        self.log_filename = log_filename
        self.logger = None

    def __enter__(self):
        self.stdout_fd = sys.stdout.fileno()
        self.stderr_fd = sys.stderr.fileno()

        self.saved_stdout_fd = os.dup(self.stdout_fd)
        self.saved_stderr_fd = os.dup(self.stderr_fd)

        self.temp_stdout = tempfile.TemporaryFile(mode="w+")
        self.temp_stderr = tempfile.TemporaryFile(mode="w+")

        os.dup2(self.temp_stdout.fileno(), self.stdout_fd)
        os.dup2(self.temp_stderr.fileno(), self.stderr_fd)

        # Set up logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=self.log_filename,
            filemode="w",
        )
        self.logger = logging.getLogger("CaptureLogger")

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.dup2(self.saved_stdout_fd, self.stdout_fd)
        os.dup2(self.saved_stderr_fd, self.stderr_fd)

        os.close(self.saved_stdout_fd)
        os.close(self.saved_stderr_fd)

        self.temp_stdout.seek(0)
        self.temp_stderr.seek(0)

        self.stdout = self.temp_stdout.read()
        self.stderr = self.temp_stderr.read()

        self.temp_stdout.close()
        self.temp_stderr.close()

        # Log the captured output
        self.logger.info("Captured stdout:\n%s", self.stdout)
        self.logger.error("Captured stderr:\n%s", self.stderr)


def delete_all_objects():
    """Deletes all objects in the scene.

    Parameters
    ----------
        None

    Returns
    -------
        None

    """
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def reset_blender():
    bpy.ops.wm.read_factory_settings()

    # for scene in bpy.data.scenes:
    #     for obj in scene.objects:
    #         scene.objects.unlink(obj)

    # only worry about data in the startup scene
    for bpy_data_iter in (
        bpy.data.objects,
        bpy.data.meshes,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for id_data in bpy_data_iter:
            bpy_data_iter.remove(id_data)


def load_blender_file(blender_file: str):
    """Loads a Blender file.

    Parameters
    ----------
    blender_file (str): The path to the Blender file.

    Returns
    -------
    None

    """
    bpy.ops.wm.open_mainfile(filepath=blender_file)


def save_blender_file(output_filename: str = "output.blend"):
    """Saves the current Blender file.

    Parameters
    ----------
    output_filename (str): The name of the output file.

    Returns
    -------
    None

    """
    print(f"Saving blender file to {output_filename}")
    # make sure the output directory exists
    Path(output_filename).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_filename))


def add_material(blend_file: str, material_name: str = ""):
    """Adds a texture from a Blender file.

    Parameters
    ----------
    blend_file (str): The path to the Blender file.
    texture_name (str): The name of the texture.

    Returns
    -------
    None

    """
    # check the file exists
    if not os.path.exists(blend_file):
        print(f"Could not find blend file {blend_file}")
        return
    bpy.ops.wm.append(
        filename=material_name,
        filepath=blend_file + "/Material/" + material_name,
        directory=blend_file + "/Material",
    )


def set_camera_type(camera_type: str = "PERSP"):
    """Sets the camera type.

    Parameters
    ----------
    camera_type (str): The type of the camera.

    Returns
    -------
    None

    """
    # check there is at least one camera in the scene
    if len(bpy.data.cameras) == 0:
        print("No camera found in scene")
        return
    # check the camera type is valid
    if camera_type not in ["PERSP", "ORTHO"]:
        print(f"Invalid camera type: {camera_type}")
        return
    print(f"Setting camera type to {camera_type}")
    bpy.context.scene.camera.data.type = camera_type


def render_blender(
    output_filename: str = "output.png", index: int | None = None, remove_index: bool = True
) -> list[str]:
    """Renders the scene and saves the output to a file.

    Parameters
    ----------
    output_filename (str): The name of the output file.

    Returns
    -------
    None

    """
    if index is not None:
        assert index >= 0, f"Invalid index: {index}"
    bpy.context.scene.render.use_file_extension = True
    bpy.context.scene.render.filepath = str(output_filename)

    # setup path for all output nodes
    files_prefixes_to_correct = []
    if bpy.context.scene.use_nodes:
        for node in bpy.context.scene.node_tree.nodes:
            if node.type == "OUTPUT_FILE":
                node.base_path = os.path.dirname(output_filename)
                node_output_filename = node.label
                if index is not None:
                    node_output_filename += f"_{index:03d}"
                files_prefixes_to_correct.append(node_output_filename)

                node.file_slots[0].path = node_output_filename + "__#####"

    print(f"Rendering {index} to {output_filename}...")
    # with CaptureOutput("blender_render.log") as capture:
    bpy.ops.render.render(write_still=True)

    render_files = [str(Path(output_filename).name)]

    # find all files in the output directory, remove __##### from the name
    if remove_index and len(files_prefixes_to_correct) > 0:
        pattern = r"__\d{5}"
        render_files += correct_output_filenames(os.path.dirname(output_filename), files_prefixes_to_correct, pattern)

    return render_files


def correct_output_filenames(output_dir: str, files_to_correct: list[str], pattern: str) -> list[str]:
    logging.debug(f"Correcting {files_to_correct} in {output_dir} with pattern {pattern}")
    render_files = []
    for file in os.listdir(output_dir):
        for file_to_correct in files_to_correct:
            # find pattern in the file name
            if re.search(f"{file_to_correct}{pattern}", file):
                new_file = re.sub(pattern, "", file)
                logging.debug(f"Renaming {file} to {new_file}")
                os.rename(
                    os.path.join(output_dir, file),
                    os.path.join(output_dir, new_file),
                )
                render_files.append(new_file)
    return render_files


def setup_moon_scene(device: str = "GPU") -> None:
    """Sets up the scene for rendering.

    Parameters
    ----------

    """
    reset_blender()
    print(f"Setting up scene using {device}")

    # Add sun light
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 10000))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 10.0
    sun.data.angle = 0.52 * math.pi / 180  # as seen from earth/moon system
    sun.data.use_shadow = True

    # Load regolith materials
    default_material_source = "assets/materials/moon_shaders.blend"
    default_material_name = "Regolith7_MAT"
    add_material(default_material_source, default_material_name)

    # Add camera
    bpy.ops.object.camera_add(location=(0, 0, 0), rotation=(0, 0, 0))
    camera = bpy.context.active_object
    camera.name = "Camera"
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100000
    camera.data.ortho_scale = 10000

    bpy.context.preferences.addons["cycles"].preferences.refresh_devices()
    for device_cyles in bpy.context.preferences.addons["cycles"].preferences.devices:
        # if "RTX" in device["name"]:
        device_cyles["use"] = 1  # enable the device

    # devices = bpy.context.preferences.addons["cycles"].preferences.get_devices()

    for scene in bpy.data.scenes:
        scene.camera = camera

        # Remove background, set world color to black
        scene.world.use_nodes = False
        scene.world.color = (0, 0, 0)

        # Change output of the render BW
        scene.render.image_settings.color_mode = "BW"
        # scene.render.image_settings.color_depth = "16"

        # Color management to raw
        scene.render.image_settings.color_management = "OVERRIDE"
        scene.view_settings.view_transform = "Raw"

        # set cycles
        scene.render.engine = "CYCLES"
        scene.cycles.device = device
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "OPTIX"

    # exit()

    # bpy.context.scene.cycles.samples = 2048

    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024


def load_mesh(
    mesh_file: str,
    import_mode: str | None = None,
    zoom_factor: float = 1.0,
    material_name=None,
) -> bool:
    """Loads a mesh file.

    Parameters
    ----------
    mesh_file (str): The path to the mesh file.

    Returns
    -------
    bool: True if the mesh was loaded successfully, False otherwise.

    """
    if not os.path.exists(mesh_file):
        print(f"Could not find mesh file {mesh_file}")
        return False

    if mesh_file.endswith(".obj"):
        bpy.ops.import_scene.obj(filepath=mesh_file)
    elif mesh_file.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=mesh_file)
    elif mesh_file.endswith(".tiff") or mesh_file.endswith(".tif"):
        load_tiff(mesh_file, import_mode, zoom_factor, material_name)
    elif mesh_file.endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=mesh_file)
    elif mesh_file.endswith(".ply"):
        bpy.ops.import_mesh.ply(filepath=mesh_file)
    else:
        print(f"Unsupported mesh file format: {mesh_file}")
        return False
    return True


def fit_camera_to_mesh(obj_name: str | None = None):
    """Fits the camera to the mesh.

    Parameters
    ----------
    mesh_file (str): The path to the mesh file.

    Returns
    -------
    None

    """
    # select the object
    bpy.ops.object.select_all(action="DESELECT")
    if obj_name is None:
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                obj_name = obj.name
                break
    else:
        if obj_name not in bpy.data.objects:
            print(f"Could not find object {obj_name}. Available objects: {bpy.data.objects.keys()}")
            exit(1)
    bpy.data.objects[obj_name].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[obj_name]

    # set camera
    bpy.context.scene.camera.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera.data.type = "ORTHO"
    bpy.context.scene.camera.data.clip_end = 100000

    # Set the camera to the mesh
    bpy.ops.view3d.camera_to_view_selected()
    x, y, z = bpy.context.scene.camera.location
    return z


def get_mesh_bounds(obj=None):
    if obj is None:
        # find first mesh object
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                print(f"Using object {obj.name} for bounds")
                break

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


def load_tiff(tiff_file, mode: str | None = "mesh", zoom_factor: float = 1.0, material_name=None):
    """Load a tiff file as a mesh or subdiv"""
    if mode is None:
        mode = "mesh"

    if mode == "mesh":
        load_tiff_dem_primitive_grid(tiff_file, zoom_factor, material_name)
    elif mode == "subdiv":
        load_tiff_subdiv(tiff_file)
    else:
        print(f"Unsupported mode: {mode}")
        return False


def set_viewport_clip(clip_end: float = 20000.0):
    for a in bpy.context.screen.areas:
        if a.type == "VIEW_3D":
            for s in a.spaces:
                if s.type == "VIEW_3D":
                    s.clip_end = clip_end


def load_tiff_dem_primitive_grid(tiff_file: str, zoom_factor: float = 1.0, material_name=None):
    print(f"Loading tiff file {tiff_file} as a mesh")
    with DEM(tiff_file) as dem:
        if zoom_factor != 1.0:
            dem.zoom(zoom_factor)
        elevation_data = dem.band1
        mesh_size = elevation_data.shape[0] * dem.res[0]
    load_mesh_from_array(elevation_data, mesh_size, material_name)


def load_mesh_from_array(elevation_data: np.ndarray, mesh_size: float, material_name=None):
    height, width = elevation_data.shape
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=width - 1, y_subdivisions=height - 1, size=mesh_size)
    plane = bpy.context.active_object
    plane.name = "Terrain"
    print(f"Loaded mesh with size {mesh_size}x{mesh_size}")

    # Reshape the elevation data to match the vertex coordinates
    elevation_data_reshaped = np.flipud(elevation_data).flatten()

    # Apply the changes back to the mesh vertices
    mesh = plane.data
    for i, vertex in enumerate(mesh.vertices):
        vertex.co.z = elevation_data_reshaped[i]

    # add new material to mesh. set albedo to 0.14
    material_default = bpy.data.materials.new(name="TerrainMat")
    material_default.diffuse_color = (0.14, 0.14, 0.14, 1)
    if material_name is None:
        material = material_default
    else:
        material = bpy.data.materials.get(material_name, material_default)
    plane.data.materials.append(material)
    set_viewport_clip()
    bpy.ops.object.shade_smooth()


def load_tiff_subdiv(tiff_file):
    pass


def setDisplacer(obj, rast, uvTxtLayer, mid=0, interpolation=False):
    # Config displacer
    displacer = obj.modifiers.new("DEM", type="DISPLACE")
    demTex = bpy.data.textures.new("demText", type="IMAGE")
    demTex.image = rast.bpyImg
    demTex.use_interpolation = interpolation
    demTex.extension = "CLIP"
    demTex.use_clamp = False  # Needed to get negative displacement with float32 texture
    displacer.texture = demTex
    displacer.texture_coords = "UV"
    displacer.uv_layer = uvTxtLayer.name
    displacer.mid_level = mid  # Texture values below this value will result in negative displacement
    if rast.depth < 32:
        # 8 or 16 bits unsigned values (signed int16 must be converted to float to be usuable)
        displacer.strength = 2**rast.depth - 1
    else:
        # 32 bits values
        # with float raster, blender give directly raw float values(non normalied)
        # so a texture value of 100 simply give a displacement of 100
        displacer.strength = 1
    bpy.ops.object.shade_smooth()
    return displacer


def add_subdiv_modifier(obj, levels: int = 6):
    n_subdivs = levels // 6 + 1  # 6 levels per subdivision
    for i in range(n_subdivs):
        levels_left = levels - i * 6
        subsurf = obj.modifiers.new("DEM", type="SUBSURF")
        subsurf.subdivision_type = "SIMPLE"
        subsurf.levels = levels_left if levels_left < 6 else 6
        subsurf.render_levels = levels_left if levels_left < 6 else 6
        # bpy.ops.object.modifier_apply(modifier=subsurf.name)


def subdivide_mesh(obj, subdivisions: int = 10):
    bpy.context.view_layer.objects.active = obj

    # Switch to edit mode
    bpy.ops.object.mode_set(mode="EDIT")

    # Subdivide the mesh
    bpy.ops.mesh.subdivide(number_cuts=subdivisions)

    # Switch back to object mode
    bpy.ops.object.mode_set(mode="OBJECT")


def get_blender_object(object_name: str) -> bpy.types.Object:
    assert object_name in bpy.data.objects, f'Could not find object "{object_name}"'
    obj = bpy.data.objects[object_name]
    return obj


def set_object_position(xyz: list[float], object_name: str = "Camera") -> None:
    obj = get_blender_object(object_name)
    obj.location.x = xyz[0]
    obj.location.y = xyz[1]
    obj.location.z = xyz[2]


def set_object_orientation(rpy: list[float], object_name: str = "Camera", euler_type: str = "XYZ") -> None:
    obj = get_blender_object(object_name)
    obj.rotation_mode = euler_type
    obj.rotation_euler[0] = rpy[0]
    obj.rotation_euler[1] = rpy[1]
    obj.rotation_euler[2] = rpy[2]


def set_camera_pose(x: float, y: float, z: float, pitch: float, yaw: float) -> None:
    set_object_position([x, y, z], "Camera")
    set_object_orientation([math.pi / 2 + pitch, 0.0, yaw], "Camera")


def set_camera_ortho_scale(ortho_scale: float) -> None:
    bpy.context.scene.camera.data.ortho_scale = ortho_scale


def set_sun_orientation(elevation: float, azimuth: float, auto_adjust_sun_power: bool = True) -> None:
    """Set the orientation of the sun in the scene.
    - Elevation is the angle from the horizon to the sun, 0 is at the horizon, 90 is directly overhead
    - Azimuth is the angle from the north, 0 is north, 90 is east, 180 is south, 270 is west

    Parameters
    ----------
        elevation (float): The elevation of the sun in radians.
        azimuth (float): The azimuth of the sun in radians.
        auto_adjust_sun_power (bool): Whether to automatically adjust the sun power based on the elevation.

    Returns
    -------
    None

    """
    lights = [obj for obj in bpy.data.objects if obj.type == "LIGHT"]
    sun = [light for light in lights if light.data.type == "SUN"]
    if len(sun) == 0:
        print("No sun found in scene")
        return
    if len(sun) > 1:
        print("Multiple suns found in scene, using the first one")
    set_object_orientation([math.pi / 2 - elevation, 0.0, azimuth], sun[0].name)

    if auto_adjust_sun_power:
        reference_power_at_90_degrees = 1.0  # power at 90 degrees elevation, not touching blender gain
        sun[0].data.energy = reference_power_at_90_degrees / math.sin(elevation)
        sun[0].data.energy = min(sun[0].data.energy, 10.0)  # limit to 10
        sun[0].data.energy = max(sun[0].data.energy, 2.0)  # limit to 3


def setup_depth_rendering(output_dir: str = ".") -> None:
    """Set up the rendering pipeline for depth rendering.
    - Create raw depth using OpenEXR format
    - Create normalized depth using PNG format
    """
    print("Setting up depth rendering")
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    links = tree.links

    # enable depth pass
    bpy.context.scene.view_layers["ViewLayer"].use_pass_z = True

    # create input image node
    scene = bpy.context.scene
    if "Render Layers" in scene.node_tree.nodes:
        rl_node = scene.node_tree.nodes["Render Layers"]
    else:
        print("Creating Render Layers node")
        rl_node = tree.nodes.new("CompositorNodeRLayers")

    # Check if has been setup before
    expected_nodes = ["depth", "depth_norm"]
    for node in bpy.context.scene.node_tree.nodes:
        if node.type == "OUTPUT_FILE" and node.label in expected_nodes:
            print("Depth rendering has already been setup, exiting...")
            return

    # create output node
    depth_raw_output_node = tree.nodes.new("CompositorNodeOutputFile")
    depth_raw_output_node.base_path = str(output_dir)
    depth_raw_output_node.format.file_format = "OPEN_EXR"
    depth_raw_output_node.format.color_depth = "32"
    # depth_raw_output_node.format.compression = 0
    depth_raw_output_node.label = "depth"
    depth_raw_output_node.file_slots[0].path = "depth"
    links.new(rl_node.outputs["Depth"], depth_raw_output_node.inputs["Image"])

    # create normalized depth output node
    norm_node = tree.nodes.new("CompositorNodeNormalize")
    links.new(rl_node.outputs["Depth"], norm_node.inputs["Value"])

    depth_norm_output_node = tree.nodes.new("CompositorNodeOutputFile")
    depth_norm_output_node.base_path = str(output_dir)
    depth_norm_output_node.format.file_format = "PNG"
    depth_norm_output_node.label = "depth_norm"
    depth_norm_output_node.file_slots[0].path = "depth_norm"
    depth_norm_output_node.format.color_mode = "BW"
    depth_norm_output_node.format.color_depth = "16"
    links.new(norm_node.outputs["Value"], depth_norm_output_node.inputs["Image"])
    bpy.context.view_layer.update()


def setup_pass_index(pass_index_function=None, pass_index_dict: dict[str, int] | None = None):
    # Set up object index pass, 3 options
    # 1. pass_index_function: a function that takes an object and returns the pass index.
    #    Useful to filter by object name
    # 2. pass_index_dict: a dictionary that maps object names to pass indices. Useful to set specific pass indices
    # 3. If neither is provided, pass indices will be assigned incrementally starting from 1

    bpy.context.scene.view_layers["ViewLayer"].use_pass_object_index = True  # enable object index pass, required

    pass_index_dict = pass_index_dict or {}
    max_pass_index = max(pass_index_dict.values(), default=0)
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        if obj.name in pass_index_dict:
            obj.pass_index = pass_index_dict[obj.name]
            # print(f"Setting pass index for {obj.name} to {obj.pass_index}")
        elif pass_index_function is not None:
            obj.pass_index = pass_index_function(obj.name)
            # print(
            #     f"Setting pass index for {obj.name} to {obj.pass_index} using pass_index_function"
            # )
        else:
            max_pass_index += 1
            obj.pass_index = max_pass_index
            pass_index_dict[obj.name] = obj.pass_index
    return pass_index_dict


def setup_segmentation_rendering(
    output_dir: str = ".",
    set_pass_index: bool = True,
    pass_index_function=None,
    pass_index_dict=None,
    cases_dict=None,
):
    """Set up the rendering pipeline for segmentation rendering.
    - Create integer segmentation using PNG format
    - Create color segmentation using PNG format
    """
    print("Setting up segmentation rendering")
    bpy.context.scene.view_layers["ViewLayer"].use_pass_object_index = True
    if set_pass_index:
        pass_index_dict = setup_pass_index(pass_index_function=pass_index_function)

    if bpy.context.scene.use_nodes:
        # Check if has been setup before
        expected_nodes = ["segmentation_integer", "segmentation_color"]
        for node in bpy.context.scene.node_tree.nodes:
            if node.type == "OUTPUT_FILE" and node.label in expected_nodes:
                print("Segmentation rendering has already been setup")
                return
    else:
        bpy.context.scene.use_nodes = True

    if cases_dict is not None:
        cases_dict["pass_index_dict"] = pass_index_dict

    # ensure we are using Cycles renderer
    if bpy.context.scene.render.engine != "CYCLES":
        print(f"Switching to Cycles renderer from {bpy.context.scene.render.engine}")
        bpy.context.scene.render.engine = "CYCLES"

    tree = bpy.context.scene.node_tree
    links = tree.links

    # Collect pass_index
    mesh_pass_indices = {}
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            mesh_pass_indices[obj.name] = obj.pass_index

    n_objects = len(mesh_pass_indices)
    unique_pass_indices = set(mesh_pass_indices.values())
    n_unique_pass_indices = len(unique_pass_indices)

    print(f"Found {n_objects} objects with {n_unique_pass_indices} unique pass indices.")
    # if n_unique_pass_indices < 255:
    color_depth_str = "16"
    number_colors_steps = 255

    scene = bpy.context.scene
    if "Render Layers" in scene.node_tree.nodes:
        rl_node = scene.node_tree.nodes["Render Layers"]
    else:
        print("Creating Render Layers node")
        rl_node = tree.nodes.new("CompositorNodeRLayers")

    i_IndexOB = list(rl_node.outputs.keys()).index("IndexOB")

    divide_node = tree.nodes.new("CompositorNodeMath")
    divide_node.operation = "DIVIDE"
    divide_node.inputs[1].default_value = number_colors_steps
    # print(divide_node.inputs[1].default_value)
    # print(f"number_colors_steps: {number_colors_steps}")

    links.new(rl_node.outputs[i_IndexOB], divide_node.inputs[0])

    integer_segmentation_output_node = tree.nodes.new("CompositorNodeOutputFile")  # Output Node
    integer_segmentation_output_node.base_path = str(output_dir)
    integer_segmentation_output_node.format.color_mode = "BW"
    integer_segmentation_output_node.format.file_format = "PNG"  # Output format
    integer_segmentation_output_node.format.color_depth = color_depth_str
    integer_segmentation_output_node.label = "segmentation_integer"
    integer_segmentation_output_node.file_slots[0].path = "segmentation_integer_####"  # Filename and frame number
    links.new(divide_node.outputs[0], integer_segmentation_output_node.inputs["Image"])

    if n_unique_pass_indices < 32:  # if we have less than 32 objects, we can use color ramp
        segmentation_color_ramp_node = tree.nodes.new("CompositorNodeValToRGB")
        segmentation_color_ramp_node.color_ramp.interpolation = "CONSTANT"
        links.new(divide_node.outputs[0], segmentation_color_ramp_node.inputs["Fac"])

        #  distribute colors along the hue spectrum
        colors = {}
        for pass_index in unique_pass_indices:
            color_hue = pass_index / n_unique_pass_indices
            color_hsv = (color_hue, 1.0, 1.0)
            colors[pass_index] = colorsys.hsv_to_rgb(*color_hsv)

        # set colors for each object type
        segmentation_color_ramp_node.color_ramp.elements.remove(
            segmentation_color_ramp_node.color_ramp.elements.values()[1]
        )
        for pass_index in unique_pass_indices:
            ramp_position = (pass_index - 0.5) / number_colors_steps
            color_ramp_element = segmentation_color_ramp_node.color_ramp.elements.new(ramp_position)
            color_ramp_element.color = (*colors[pass_index], 1)
            logging.debug(f"index: {pass_index}, color: {colors[pass_index]}, ramp_pos: {ramp_position}")

        color_segmentation_output_node = tree.nodes.new("CompositorNodeOutputFile")  # Output Node
        color_segmentation_output_node.base_path = str(output_dir)
        color_segmentation_output_node.format.file_format = "PNG"  # Output format
        color_segmentation_output_node.label = "segmentation_color"
        color_segmentation_output_node.format.color_mode = "RGB"
        color_segmentation_output_node.format.color_depth = "16"
        color_segmentation_output_node.file_slots[0].path = "segmentation_color_####"  # Filename and frame number

        links.new(
            segmentation_color_ramp_node.outputs["Image"],
            color_segmentation_output_node.inputs["Image"],
        )


def add_cases_visalization(
    cases_list: list[dict],
    case_cone_size: float | None = None,
    connect_cases: bool = False,
    cases_collection: bpy.types.Collection = None,
) -> None:
    """Visualizes the cases in the configuration file.

    Parameters
    ----------
    cases_list (list[dict]): The list of cases to visualize.
    case_cone_size (float): The size of the case cone.
    connect_cases (bool): Whether to connect the cases with a trajectory.
    cases_collection (bpy.types.Collection): The collection to add the cases to.

    Returns
    -------
    None

    """
    if cases_collection is None:
        if "Sampling Cases" in bpy.data.collections:
            cases_collection = bpy.data.collections["Sampling Cases"]
            for obj in list(cases_collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            cases_collection = bpy.data.collections.new("Sampling Cases")
            bpy.context.scene.collection.children.link(cases_collection)

    print(f"Adding {len(cases_list)} cases to the scene")
    # print(cases_list[0])
    if case_cone_size is None and "camera/ortho_scale" not in cases_list[0]:
        print("Calculating case cone size")
        cases_to_test = min(4, len(cases_list) - 1)
        distance_min = 1000000
        for case_base_index in range(cases_to_test):
            assert "camera/x" in cases_list[case_base_index], "camera/x not found"
            for case_target_index, case_target in enumerate(cases_list):
                assert "camera/x" in case_target, "camera/x not found in target"
                if case_base_index == case_target_index:
                    continue
                distance_min = min(
                    np.sqrt(
                        (case_target["camera/x"] - cases_list[case_base_index]["camera/x"])
                        + (case_target["camera/y"] - cases_list[case_base_index]["camera/y"])
                    ),
                    distance_min,
                )
        z_min = np.min([case["camera/z"] for case in cases_list])
        case_cone_size = distance_min / 3
        print(f"distance_min: {distance_min:.2f}, z_min: {z_min:.2f}: case_cone_size: {case_cone_size:.2f}")

    print(f"Adding {len(cases_list)} cases to the scene")
    camera_list = []
    time_per_case = []
    for case in tqdm.tqdm(cases_list, desc="Adding cases"):
        start_time = time.time()
        x, y, z = case["camera/x"], case["camera/y"], case["camera/z"]
        pitch, yaw, roll = case["camera/pitch"], case["camera/yaw"], 0.0
        camera_list.append((x, y, z, pitch, yaw, roll))

        # add a mesh cone to visualize the camera
        if "camera/ortho_scale" in case:
            bpy.ops.mesh.primitive_cone_add(
                vertices=4,
                radius1=case["camera/ortho_scale"] / np.sqrt(2),
                radius2=case["camera/ortho_scale"] / np.sqrt(2),
                depth=case["camera/ortho_scale"] / 4,
                location=(x, y, z),
                end_fill_type="NOTHING",
                rotation=(pitch + math.pi / 2, roll, yaw + np.pi / 4),
            )
        else:
            if case_cone_size is None:
                case_cone_size = 1
            bpy.ops.mesh.primitive_cone_add(
                vertices=4,
                radius1=case_cone_size,
                radius2=case_cone_size * 0.3,
                depth=case_cone_size,
                location=(x, y, z),
                end_fill_type="NOTHING",
                rotation=(pitch + math.pi / 2, roll, yaw),
            )
        case_object = bpy.context.active_object
        # for collection in bpy.data.collections:
        # check if case_object is already in collection, unlink it if so
        # if case_object.name in collection.objects:
        # collection.objects.unlink(case_object)
        cases_collection.objects.link(case_object)
        time_per_case.append(time.time() - start_time)
    print(f"Time per case: {np.mean(time_per_case)}")
    cases_collection.hide_render = True
    if connect_cases:
        add_trajectory(camera_list, cases_collection)


def add_trajectory(traj: list[tuple[float, float, float, float, float, float]], cases_collection=None):
    """Adds a trajectory to the scene.

    Parameters
    ----------
    traj (dict): The trajectory dictionary.

    Returns
    -------
    None

    """
    curve_data = bpy.data.curves.new(name="Trajectory", type="CURVE")
    curve_data.dimensions = "3D"

    # Create a new Bezier spline
    spline = curve_data.splines.new(type="BEZIER")
    spline.bezier_points.add(len(traj) - 1)

    # Assign the points to the Bezier spline
    for i, (x, y, z, psi, phi, roll) in enumerate(traj):
        bez_point = spline.bezier_points[i]
        bez_point.co = (x, y, z)
        bez_point.handle_left_type = "AUTO"
        bez_point.handle_right_type = "AUTO"

    # Create a new object with the curve data
    curve_object = bpy.data.objects.new("TrajectoryObject", curve_data)

    # Link the object to the scene collection
    if cases_collection is None:
        bpy.context.collection.objects.link(curve_object)
    else:
        cases_collection.objects.link(curve_object)


def setup_render_config(render_config_file: str):
    """Loads a render configuration file.

    Parameters
    ----------
    render_config_file (str): The path to the render configuration file.

    Returns
    -------
    None

    """
    # check if render_config_file is a dict or a file
    if isinstance(render_config_file, dict):
        render_config = render_config_file
    else:
        with open(render_config_file) as f:
            render_config = yaml.safe_load(f)

    # Example render_config.yaml:
    # render_engine: CYCLES
    # sampling_render: 4096
    # resolution_x: 2048
    # resolution_y: 2048

    # Set render engine
    if "render_engine" in render_config:
        bpy.context.scene.render.engine = render_config["render_engine"]

    # Set sampling
    if "sampling_render" in render_config:
        bpy.context.scene.cycles.samples = render_config["sampling_render"]

    # Set resolution
    if "resolution_x" in render_config and "resolution_y" in render_config:
        bpy.context.scene.render.resolution_x = render_config["resolution_x"]
        bpy.context.scene.render.resolution_y = render_config["resolution_y"]
