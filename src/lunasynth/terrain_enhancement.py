#!/usr/bin/env python3
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

import datetime as dt
import json
import os
import random
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import bpy
import humanize
import lunasynth.blender_helper as blender_helper
import lunasynth.dem_tools as dem_tools
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from mathutils import Vector
from numba import njit, prange
from scipy.interpolate import (
    RegularGridInterpolator,  # interp2d is deprecated
    interp1d,
)


def dth(d: float, minimum_unit: str = "microseconds") -> str:
    return humanize.precisedelta(dt.timedelta(seconds=d), minimum_unit=minimum_unit)


def cumsumr(v: np.ndarray) -> np.ndarray:
    """Cumsum from the end"""
    return np.cumsum(v[::-1])[::-1]


@dataclass
class CfaModel:
    """Represents a cumulative frequency area model."""

    value_min: float
    value_max: float
    density: float

    def __init__(
        self,
        value_min: float,
        value_max: float,
        density: float,
        n_points: int = 1000,
        A: float = 0.5648,
        B: float = 0.01285,
    ):
        self.value_min = value_min
        self.value_max = value_max
        self.density = density
        self.n_points = n_points
        self.A = A
        self.B = B

    def compute_values(self, area: float, seed: int | None = None) -> tuple[list[float], float]:
        self.area = area
        if seed is not None:
            np.random.seed(seed)
        D = np.logspace(np.log10(self.value_min), np.log10(self.value_max), self.n_points)
        N = self.num_pdf(D, self.density)
        d_diff = np.diff(D)
        NumCDF = np.cumsum(
            N[:-1] * d_diff,
        )
        NumCDF = NumCDF / NumCDF[-1]

        self.N = N
        self.D = D
        self.NumCDF = NumCDF
        q = self.q(self.density)

        CFA_for_h_min = self.density * np.exp(-q * self.value_min)

        f = interp1d(NumCDF, D[:-1], kind="cubic", fill_value="extrapolate")

        dia = []
        self.computed_CFA = 0.0
        batch_size = max(int(area / 100), 1)  # to get around 3 batch_iterations
        batch_iterations = 0
        while self.computed_CFA < CFA_for_h_min:
            batch_iterations += 1
            dia.extend(list(f(np.random.rand(batch_size))))
            CFA_cumsum = np.cumsum([np.pi / 4 * d**2 for d in dia]) / area
            self.computed_CFA = CFA_cumsum[-1]

        # get how many rocks until CFA_for_h_min is reached
        self.diameters = dia[: np.argmax(CFA_cumsum > CFA_for_h_min)]
        if len(self.diameters) == 0:
            print("No rocks generated. Check the input parameters and try again.")
            print(f"Computed CFA: {self.computed_CFA*100:.2f}%")
            print(f"Target CFA: {CFA_for_h_min*100:.2f}%")
            print(f"Target density: {self.density}")
            print(f"Target value_min: {self.value_min}")
            print(f"Target value_max: {self.value_max}")
            print(f"CFA_cumsum: {CFA_cumsum}")
            msg = "No rocks generated. Check the input parameters and try again."
            raise ValueError(msg)
        self.computed_CFA = (np.cumsum([np.pi / 4 * d**2 for d in self.diameters]) / (area))[-1]

        print(
            f"Generated {len(self.diameters)} values with CFA={self.computed_CFA*100:.2f}%"
            f"in {batch_iterations} iterations"
        )
        return self.diameters, self.computed_CFA

    def plot_creation(self, show: bool = False, filename: str | None = None) -> None:
        """Plots the rock field creation process."""
        self.creation_fig, self.creation_ax = plt.subplots(1, sharex=True)
        self.creation_fig.subplots_adjust(hspace=0)
        self.creation_ax.plot(self.D, self.N, label="Theoretical Number Density")
        self.creation_ax.hist(
            self.diameters,
            bins=10,
            density=True,
            alpha=0.6,
            label="Generated Rocks Density",
        )
        self.creation_ax.set_yscale("log")
        self.creation_ax.set_ylabel("Number Density")
        self.creation_ax.set_xlabel("Diameter (m)")
        self.creation_ax.legend()
        self.creation_ax.set_title("Rock Field Number Density")

        if filename is not None:
            plt.savefig(filename)
        if show:
            plt.show()

    def plot_cum_rock_size(self, show: bool = False, filename: str | None = None) -> None:
        """Plots the cumulative rock size distribution."""
        sorted_diameters = np.sort(self.diameters)
        area_factor = np.pi / 4 / self.area
        cum_rocks = cumsumr(sorted_diameters**2) * area_factor
        cum_theoretical = [self.density * np.exp(-self.q(self.density) * d) for d in sorted_diameters]

        self.cfa_fig, self.cfa_ax = plt.subplots()
        self.cfa_ax.loglog(sorted_diameters, cum_rocks, label="Generated Rocks CDF", linewidth=2)
        self.cfa_ax.loglog(sorted_diameters, cum_theoretical, label="Theoretical CDF", linewidth=1)
        self.cfa_ax.plot(
            [sorted_diameters[0], sorted_diameters[-1]],
            [self.computed_CFA, self.computed_CFA],
            label="Computed CFA",
            linestyle="--",
            color="red",
            linewidth=1,
        )
        self.cfa_ax.plot(
            [sorted_diameters[0], sorted_diameters[-1]],
            [self.density, self.density],
            label="Target CFA",
            linestyle="--",
            color="green",
            linewidth=1,
        )
        self.cfa_ax.plot(
            [self.value_min, self.value_min],
            [cum_theoretical[0], cum_theoretical[-1]],
            label="value_min",
            linestyle="--",
            color="black",
            linewidth=1,
        )
        self.cfa_ax.plot(
            [self.value_max, self.value_max],
            [cum_theoretical[0], cum_theoretical[-1]],
            label="value_max",
            linestyle="--",
            color="orange",
            linewidth=1,
        )

        self.cfa_ax.legend()
        self.cfa_ax.set_xlabel("Diameter (m)")
        self.cfa_ax.set_ylabel("CDF")
        self.cfa_ax.grid()
        self.cfa_ax.set_title("Cumulative Area Rock Size Distribution")

        if filename is not None:
            plt.savefig(filename)
        if show:
            plt.show()

    def num_pdf(self, D: np.ndarray, k: float = 0.05) -> list[float]:
        """Generates a number density function for the rock field.

        Parameters
        ----------
        D (np.ndarray): An array of rock sizes.

        Returns
        -------
        np.ndarray: An array of number densities for the rock sizes.

        """
        P = self.area_pdf(D, k)
        return [p / (d**2) * 4 / np.pi for p, d in zip(P, D)]

    def area_pdf(self, D: np.ndarray, k: float = 0.05) -> list[float]:
        """Generates an area density function for the rock field.

        Parameters
        ----------
        D (np.ndarray): An array of rock sizes.

        Returns
        -------
        np.ndarray: An array of area densities for the rock sizes.

        """
        q = self.q(k)
        return [k * q * np.exp(-q * d) for d in D]

    def q(self, k: float) -> float:
        """Calculates the q value for a given k value, as q = A + B/k

        Parameters
        ----------
        k (float): The k value to calculate the q value for.

        Returns
        -------
        float: The q value.

        """
        return self.A + self.B / k


@dataclass
class Rock:
    x: float
    y: float
    diameter: float
    height: float
    shape_type: int
    rot_x: float
    rot_y: float
    rot_z: float
    z_shift: float

    def __init__(
        self,
        x: float,
        y: float,
        diameter: float,
        height: float,
        shape_type: int,
        rot_x: float,
        rot_y: float,
        rot_z: float,
        z_shift: float,
    ):
        self.x = x
        self.y = y
        self.diameter = diameter
        self.height = height
        self.shape_type = shape_type
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z
        self.z_shift = z_shift

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class RockField:
    rocks: list[Rock]
    computed_CFA: float

    def __init__(self) -> None:
        pass

    @property
    def xv(self) -> list[float]:
        """Creates a list of x values"""
        return [rock.x for rock in self.rocks]

    @property
    def yv(self) -> list[float]:
        """Creates a list of y values"""
        return [rock.y for rock in self.rocks]

    @property
    def diameters(self) -> list[float]:
        """Creates a list of diameters"""
        return [rock.diameter for rock in self.rocks]

    def to_dict(self) -> dict:
        return {
            "rocks": [rock.to_dict() for rock in self.rocks],
            "computed_CFA": self.computed_CFA,
        }

    def to_json(self, file_path: str | Path | None = None) -> str:
        data_dict = self.to_dict()
        json_string = json.dumps(data_dict)
        if file_path:
            with open(file_path, "w") as file:
                json.dump(data_dict, file, indent=4)
        return json_string

    def to_csv(self, filename: str) -> None:
        import csv

        with open(filename, mode="w") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "x",
                    "y",
                    "diameter",
                    "height",
                    "shape_type",
                    "rot_x",
                    "rot_y",
                    "rot_z",
                    "z_shift",
                ]
            )
            rows = [
                [
                    rock.x,
                    rock.y,
                    rock.diameter,
                    rock.height,
                    rock.shape_type,
                    rock.rot_x,
                    rock.rot_y,
                    rock.rot_z,
                    rock.z_shift,
                ]
                for rock in self.rocks
            ]
            writer.writerows(rows)

    def from_csv(self, filename: str) -> None:
        import csv

        rocks = []
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                x, y, diameter, height, shape_type, rot_x, rot_y, rot_z, z_shift = map(float, row)
                shape_type = int(shape_type)
                rocks.append(Rock(x, y, diameter, height, shape_type, rot_x, rot_y, rot_z, z_shift))
        self.rocks = rocks

    def save(self, filename: str) -> None:
        """Saves the rock field to a json and csv file.

        Parameters
        ----------
            filename (str): The name of the file to save the rock field to, without the file extension.

        """
        filename = str(filename)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        if "." in filename:
            filename = filename.split(".")[0]
        print(f"Saving rock field to {filename} json and csv files.")

        self.to_csv(filename + ".csv")
        # self.to_json(filename + ".json")

    def plot(self, filename: str | None = None, show: bool = False) -> None:
        size_factor = 1
        self.rock_field_fig, self.rock_field_ax = plt.subplots()
        self.rock_field_ax.scatter(
            self.xv,
            self.yv,
            s=[d * size_factor for d in self.diameters],
            c="black",
            alpha=0.5,
        )
        self.rock_field_ax.set_xlabel("x (m)")
        self.rock_field_ax.set_ylabel("y (m)")
        self.rock_field_ax.set_aspect("equal")
        self.rock_field_ax.set_title(
            f"Rock Field with {len(self.rocks)} rocks in {self.computed_CFA*100:.1f}% area coverage,"
            f"total CFA={self.k*100:.1f}%"
        )
        if filename is not None:
            plt.savefig(filename)
        if show:
            plt.show()

    def generate_rock_field(
        self,
        k: float,
        size_x: float,
        size_y: float,
        h_min: float,
        h_max: float = 5.0,
        seed: int | None = None,
        x_init: float = 0,
        y_init: float = 0,
        max_type_rocks: int = 15,
    ) -> None:
        """Generates a rock field with rocks of random size, height, and position.
        The rocks are placed randomly within the specified size of the rock field.
        The height of the rocks is randomly generated between h_min and h_max.

        Args:
        ----
            k (float): The CFA value as a decimal (e.g. CFA5% would have an input of CFA=0.05)
            size_x (float): The size of the rock field in the x direction.
            size_y (float): The size of the rock field in the y direction.
            h_min (float): The minimum height of the rocks.
            h_max (float): The maximum height of the rocks. Default is 5.0.
            seed (int): The seed for the random number generator. Default is None.
            x_init (float): The initial x position of the rocks. Default is 0.
            y_init (float): The initial y position of the rocks. Default is 0.
            max_type_rocks (int): The maximum number of different types of rocks. Default is 15.

        """
        self.size_x = size_x
        self.size_y = size_y
        self.k = k
        self.h_min = h_min
        self.h_max = h_max

        self.cfa_model = CfaModel(h_min, h_max, k)
        rock_diameters, computed_CFA = self.cfa_model.compute_values(size_x * size_y, seed=seed)
        n_rocks = len(rock_diameters)

        self.computed_CFA = computed_CFA

        xv = np.random.rand(n_rocks) * size_x + x_init
        yv = np.random.rand(n_rocks) * size_y + y_init

        shape_type = np.random.randint(1, max_type_rocks, n_rocks)
        height_factor = np.random.uniform(0.1, 0.6, n_rocks)
        rot_x = np.random.uniform(-0.2, 0.2, n_rocks)
        rot_y = np.random.uniform(-0.2, 0.2, n_rocks)
        rot_z = np.random.uniform(0, 2 * np.pi, n_rocks)
        z_shift = np.random.uniform(-0.4, 0.1, n_rocks)

        self.rocks = [
            Rock(
                xv[i],
                yv[i],
                rock_diameters[i],
                rock_diameters[i] * height_factor[i],
                shape_type=shape_type[i],
                rot_x=rot_x[i],
                rot_y=rot_y[i],
                rot_z=rot_z[i],
                z_shift=z_shift[i] * rock_diameters[i],
            )
            for i in range(n_rocks)
        ]

    def load_rocks_blender(
        self,
        blender_file: str,
        mesh_file: str,
        rock_field_file: str,
        rock_source: str,
    ) -> None:
        rock_field = RockField()
        rock_field.from_csv(rock_field_file)
        print(f"Loaded {len(rock_field.rocks)} rocks.")
        if blender_file is not None:
            blender_helper.load_blender_file(blender_file)
        else:
            blender_helper.delete_all_objects()
            blender_helper.setup_moon_scene()
        if mesh_file is not None:
            blender_helper.load_mesh(mesh_file)
        self.place_rocks(rock_field.rocks, rock_source=rock_source)

    def get_rock_z_ray_cast(self, rock_python_obj: Rock) -> float | None:
        # return 0.0
        location_above = Vector((rock_python_obj.x, rock_python_obj.y, 0)) + Vector((0, 0, 1000))
        direction_down = Vector((0, 0, -1))
        hit, location, normal, index, object, matrix = bpy.context.scene.ray_cast(
            bpy.context.view_layer.depsgraph, location_above, direction_down
        )

        if hit:
            return location.z + rock_python_obj.height * rock_python_obj.z_shift
        else:
            print("Ray casting did not hit the terrain.")
            return None

    def create_procedural_rock(
        self,
        n_rocks: int,
        material_name: str = "Regolith7_MAT",
        detail_level: int = 3,
    ) -> dict:
        assert n_rocks > 0
        assert detail_level in [1, 2, 3]
        # make sure the addon is enabled
        if "add_mesh_extra_objects" not in bpy.context.preferences.addons.keys():
            bpy.ops.preferences.addon_enable(module="add_mesh_extra_objects")

        if material_name is not None:
            material = bpy.data.materials.get(material_name)
            if material is None:
                print(f"Material {material_name} not found.")

        reference_rocks_collection = bpy.data.collections.new("Reference Rocks")
        bpy.context.scene.collection.children.link(reference_rocks_collection)

        new_rocks = {}
        for i in range(n_rocks):
            bpy.ops.mesh.add_mesh_rock(
                use_random_seed=False,
                user_seed=i,
                display_detail=1,
                detail=detail_level,
            )
            rock_obj = bpy.context.selected_objects[-1]
            rock_obj.name = f"Rock_{i}"
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
            if material is not None:
                rock_obj.data.materials.append(material)
            for collection in bpy.data.collections:
                if rock_obj.name in collection.objects:
                    collection.objects.unlink(rock_obj)
            reference_rocks_collection.objects.link(rock_obj)
            new_rocks[rock_obj.name] = rock_obj
        reference_rocks_collection.hide_viewport = True
        reference_rocks_collection.hide_render = True
        return new_rocks

    def load_objs(
        self,
        rock_data: list[Rock],
        asset_directory: str,
        material_name: str | None = None,
    ) -> dict:
        loaded_objs = {}

        if "Reference Rocks" in bpy.data.collections:
            reference_rocks_collection = bpy.data.collections["Reference Rocks"]
            loaded_objs = {int(obj.name): obj for obj in reference_rocks_collection.all_objects}
            return loaded_objs

        if material_name is not None:
            material = bpy.data.materials.get(material_name)
            if material is None:
                print(f"Material {material_name} not found.")

        reference_rocks_collection = bpy.data.collections.new("Reference Rocks")
        bpy.context.scene.collection.children.link(reference_rocks_collection)

        # Load all the rocks in asset_directory, each rock is of form rock{index}.obj
        pattern = re.compile(r"rock(\d+)\.(obj|ply)")
        for file in os.listdir(asset_directory):
            match = pattern.match(file)
            if match:
                filepath = os.path.join(
                    asset_directory,
                    file,
                )
                print(f"loading {filepath}")
                if filepath.endswith(".obj"):
                    bpy.ops.wm.obj_import(filepath=filepath)
                elif filepath.endswith(".ply"):
                    bpy.ops.wm.ply_import(filepath=filepath)

                rock_index = int(match.group(1))
                loaded_objs[rock_index] = bpy.context.selected_objects[-1]
                loaded_objs[rock_index].name = f"{rock_index}"
                bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

                if material is not None:
                    loaded_objs[rock_index].data.materials.append(material)

                for collection in bpy.data.collections:
                    if loaded_objs[rock_index].name in collection.objects:
                        collection.objects.unlink(loaded_objs[rock_index])
                reference_rocks_collection.objects.link(loaded_objs[rock_index])

        reference_rocks_collection.hide_viewport = True
        reference_rocks_collection.hide_render = True
        return loaded_objs

    def get_z_rock_from_terrain(self, terrain_interpolant, target_x: np.ndarray, target_y: np.ndarray) -> np.ndarray:
        # Get the elevation at the target location
        return terrain_interpolant((target_y, target_x))

    def place_rocks(
        self,
        rock_data: list[Rock],
        rock_source: str = "procedural",
        target_mesh: bpy.types.Object = None,
        max_unique_rocks: int = 6,
        terrain_interpolant: RegularGridInterpolator = None,
    ) -> None:
        # Load the default material
        default_material_source = "assets/materials/moon_shaders.blend"
        default_material_name = "Regolith7_MAT"
        blender_helper.add_material(default_material_source, default_material_name)

        # load all obj files first
        if rock_source == "procedural":
            print("Creating procedural rocks.")
            loaded_objs = self.create_procedural_rock(max_unique_rocks, material_name=default_material_name)
        else:
            print(f"Loading rocks from {rock_source}")
            loaded_objs = self.load_objs(
                rock_data,
                str(Path(rock_source)),
                material_name=default_material_name,
            )
        print(f"Loaded {len(loaded_objs)} reference objects.")

        if "Rocks" in bpy.data.collections:
            rocks_collection = bpy.data.collections["Rocks"]
            for obj in list(rocks_collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            rocks_collection = bpy.data.collections.new("Rocks")
            bpy.context.scene.collection.children.link(rocks_collection)

        valid_objs = 0
        rock_random_choices = np.random.choice(list(loaded_objs.keys()), len(rock_data), replace=True)
        time_per_rock = []
        rock_obj = loaded_objs[rock_random_choices[0]]

        if terrain_interpolant is not None:
            print("Using terrain interpolant to get rock z.")
            zrocks = self.get_z_rock_from_terrain(
                terrain_interpolant,
                np.array([rock.x for rock in rock_data]),
                np.array([rock.y for rock in rock_data]),
            )
        else:
            zrocks = np.zeros(len(rock_data))
            for i, rock in enumerate(rock_data):
                zrocks[i] = self.get_rock_z_ray_cast(rock)

        valid_rocks = 0
        rock_index = 0
        for rock in tqdm.tqdm(rock_data):
            # for rock in rock_data:
            start = time.time()
            # rock_obj = loaded_objs[rock_random_choices[valid_objs]]
            # rock_obj = loaded_objs
            valid_objs += 1

            new_rock_obj = rock_obj.copy()
            bpy.context.collection.objects.link(new_rock_obj)

            # add to rocks collection
            # for collection in bpy.data.collections:
            #     if new_rock_obj.name in collection.objects:
            #         collection.objects.unlink(new_rock_obj)
            rocks_collection.objects.link(new_rock_obj)

            # Positioning and scaling
            new_rock_obj.location = (rock.x, rock.y, 0)
            new_rock_obj.scale = (rock.diameter, rock.diameter, rock.height)
            new_rock_obj.rotation_euler = (rock.rot_x, rock.rot_y, rock.rot_z)

            # z_rock = get_rock_z(new_rock_obj, rock)
            # z_rock = np.random.uniform(0, 100)
            z_rock = zrocks[rock_index]
            if z_rock is not None:
                new_rock_obj.location = Vector((new_rock_obj.location[0], new_rock_obj.location[1], z_rock))
                valid_rocks += 1
            else:
                bpy.data.objects.remove(new_rock_obj)

            rock_index += 1
            time_per_rock.append(time.time() - start)

        print(
            f"Time to copy {dth(np.sum(time_per_rock))},  "
            f"Average time per rock: {dth(float(np.mean(time_per_rock)))}"
        )

        print(f"Placed {valid_rocks} rocks out of {valid_objs} valid objects and {len(rock_data)} total rocks.")

    def delete_rocks(self) -> None:
        rocks_collection = bpy.data.collections.get("Rocks")
        if rocks_collection:
            bpy.data.collections.remove(rocks_collection)
        reference_rocks_collection = bpy.data.collections.get("Reference Rocks")
        if reference_rocks_collection:
            bpy.data.collections.remove(reference_rocks_collection)


def sample(distribution: dict | float) -> float:
    if isinstance(distribution, (int, float)):
        return distribution
    elif isinstance(distribution, str):
        return float(distribution)

    if "type" in distribution:
        if distribution["type"] == "uniform":
            return random.uniform(distribution["min"], distribution["max"])
        elif distribution["type"] == "normal":
            return random.normalvariate(distribution["mean"], distribution["std"])
        elif distribution["type"] == "list":
            return random.choice(distribution["values"])
        elif distribution["type"] == "fixed":
            return distribution["value"]
        else:
            msg = f"Unknown distribution type: {distribution['type']}"
            raise ValueError(msg)
    else:
        msg = f"Unknown distribution: {distribution}"
        raise ValueError(msg)


@dataclass
class Crater:
    x: float
    y: float
    diameter: float
    transect: np.ndarray
    type: str
    depth: float
    rim_height: float
    elevation_patch: np.ndarray

    def __init__(
        self,
        x: float,
        y: float,
        diameter: float,
    ):
        self.x = x
        self.y = y
        self.diameter = diameter

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))

    @classmethod
    def crater_depth(cls, r: float) -> float:
        # normal crater as in https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2021GL095537
        D = r / 2.0
        hr = 0.02513 * D ** (-0.0757)
        if r < 1.0:
            a = -2.85
            b = 5.8270
            d0 = 0.114 * D ** (-0.002)
            C = d0 * (np.exp(a) + 1) / (np.exp(b) - 1)
            h = C * (np.exp(b * r) - np.exp(b)) / (1 + np.exp(a + b * r)) + hr
        else:
            alpha = -3.1906
            h = hr * r**alpha
        return h

    def compute_elevation_patch(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        x = np.linspace(-2.5, 2.5, 100)
        y = np.linspace(-2.5, 2.5, 100)
        X, Y = np.meshgrid(x, y)

        self.elevation_patch = np.zeros_like(X)
        for i, xi in enumerate(x):
            for j, yj in enumerate(y):
                rij = np.sqrt(xi**2 + yj**2)
                self.elevation_patch[i, j] = self.crater_depth(rij)
        return self.elevation_patch, x, y

    def add_crater_mesh(self, verts: list) -> list:
        for vert in verts:
            d = np.sqrt((vert[0] - self.x) ** 2 + (vert[1] - self.y) ** 2)
            crater_effect_multiplier = 3.5
            if d < self.diameter * crater_effect_multiplier:
                vert[2] += self.crater_depth(d / self.diameter) * self.diameter
                # print(f"Crater depth: {self.crater_depth(d / self.diameter) * self.diameter * 10.0}")
        return verts


class CraterField:
    def __init__(self) -> None:
        pass

    @property
    def xv(self) -> list[float]:
        """Creates a list of x values"""
        return [crater.x for crater in self.craters]

    @property
    def yv(self) -> list[float]:
        """Creates a list of y values"""
        return [crater.y for crater in self.craters]

    @property
    def diameters(self) -> list[float]:
        """Creates a list of diameters"""
        return [crater.diameter for crater in self.craters]

    def generate(
        self,
        k: float,
        size_x: float,
        size_y: float,
        h_min: float,
        h_max: float = 10.0,
        seed: int | None = None,
        x_init: float = 0,
        y_init: float = 0,
    ) -> None:
        """Generates a rock field with rocks of random size, height, and position.
        The rocks are placed randomly within the specified size of the rock field.
        The height of the rocks is randomly generated between h_min and h_max.

        Parameters
        ----------
        CFA (float): CFA value as a decimal (e.g. CFA5% would have an input of CFA=0.05)
        size_x (float): The size of the rock field in the x direction.
        size_y (float): The size of the rock field in the y direction.
        h_min (float): The minimum height of the rocks.

        """
        self.size_x = size_x
        self.size_y = size_y
        self.k = k
        self.h_min = h_min
        self.h_max = h_max

        self.cfa_model = CfaModel(h_min, h_max, k)
        crater_diameters, computed_CFA = self.cfa_model.compute_values(size_x * size_y, seed=seed)
        n_craters = len(crater_diameters)

        self.computed_CFA = computed_CFA

        xv = np.random.rand(n_craters) * size_x + x_init
        yv = np.random.rand(n_craters) * size_y + y_init

        self.craters = [
            Crater(
                xv[i],
                yv[i],
                crater_diameters[i],
            )
            for i in range(n_craters)
        ]

    def from_csv(self, filename: str) -> None:
        import csv

        craters = []
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                x, y, diameter = map(float, row)
                craters.append(Crater(x, y, diameter))
        self.craters = craters

    def save(self, filename: str) -> None:
        import csv

        # create parent directory if it does not exist
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, mode="w") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "x",
                    "y",
                    "diameter",
                ]
            )
            rows = [
                [
                    crater.x,
                    crater.y,
                    crater.diameter,
                ]
                for crater in self.craters
            ]
            writer.writerows(rows)

    def place_craters_mesh(self, craters, mesh) -> None:
        # Get a list of all vertex coordinates
        verts = np.array([vert.co for vert in mesh.vertices])

        time_per_crater = []
        for crater in tqdm.tqdm(craters, desc="Adding craters"):
            start = time.time()
            verts = crater.add_crater_mesh(verts)
            time_per_crater.append(time.time() - start)
        print(
            f"Time to add craters {dth(np.sum(time_per_crater))},  "
            f"Average time per crater: {dth(float(np.mean(time_per_crater)))}"
        )

        start = time.time()
        for i, vert in enumerate(mesh.vertices):
            vert.co = verts[i]
        mesh.update()
        print(f"Time to update mesh {dth(time.time() - start)}")

    def place_craters_dem(self, craters: list[Crater], dem: np.ndarray) -> np.ndarray:
        x_coords = np.array([crater.x for crater in craters])
        y_coords = np.array([crater.y for crater in craters])
        diameters = np.array([crater.diameter for crater in craters])
        start = time.time()
        dem = place_crater_dems_numba(x_coords, y_coords, diameters, dem)
        print(f"Time to add craters {dth(time.time() - start)}")
        return dem

    def load_crater_blender(
        self,
        mesh_file: str,
        crater_field_file: str,
        zoom_factor: float = 1.0,
    ) -> None:
        crater_field = CraterField()
        crater_field.from_csv(crater_field_file)
        print(f"Loaded {len(crater_field.craters)} craters.")
        # check extension of mesh_file
        if mesh_file.endswith(".blend"):
            blender_helper.load_blender_file(mesh_file)
        else:
            blender_helper.delete_all_objects()
            blender_helper.setup_moon_scene()
            if mesh_file is not None:
                blender_helper.load_mesh(mesh_file, zoom_factor=zoom_factor)
                # apply subdivision

        # select the first mesh object
        # iterate over all objects, select the first mesh one
        for obj_local in bpy.data.objects:
            if obj_local.type == "MESH":
                obj = obj_local
                break

        bpy.ops.object.mode_set(mode="OBJECT")
        mesh = obj.data
        self.place_craters_mesh(crater_field.craters, mesh)


@njit(parallel=True)
def place_crater_dems_numba(
    x_coords: np.ndarray, y_coords: np.ndarray, diameters: np.ndarray, dem: np.ndarray
) -> np.ndarray:
    def crater_depth_numba(
        r: float,
        c1: float = 0.02513,
        c2: float = -0.0757,
        a: float = -2.85,
        b: float = 5.8270,
        c4: float = 0.114,
        c5: float = -0.002,
        alpha: float = -3.1906,
    ) -> float:
        # normal crater as in https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2021GL095537
        D = r / 2.0

        hr = c1 * D ** (c2)
        if r < 1.0:
            d0 = c4 * D ** (c5)
            C = d0 * (np.exp(a) + 1) / (np.exp(b) - 1)
            h = C * (np.exp(b * r) - np.exp(b)) / (1 + np.exp(a + b * r)) + hr
        else:
            h = hr * r**alpha
        return h

    crater_effect_multiplier = 3.5  # how many radius away to affect
    for idx in prange(len(x_coords)):
        x = x_coords[idx]
        y = y_coords[idx]
        diameter = diameters[idx]

        x_min = max(int(x - diameter * crater_effect_multiplier), 0)
        x_max = min(int(x + diameter * crater_effect_multiplier), dem.shape[0])
        y_min = max(int(y - diameter * crater_effect_multiplier), 0)
        y_max = min(int(y + diameter * crater_effect_multiplier), dem.shape[1])

        crater_patch = np.zeros((x_max - x_min, y_max - y_min))
        for i in range(x_min, x_max):
            for j in range(y_min, y_max):
                d = np.sqrt((i - x) ** 2 + (j - y) ** 2)
                if d < diameter * crater_effect_multiplier:
                    crater_patch[i - x_min, j - y_min] = crater_depth_numba(d / diameter) * diameter
        dem[x_min:x_max, y_min:y_max] += crater_patch
    return dem


@dataclass
class Terrain:
    base_mesh: str
    base_mesh_filename: str
    spatial_resolution: float
    rock_field: RockField
    crater_field: CraterField

    def __init__(self) -> None:
        pass

    def generate(self, mesh_file: str, terrain_dict: dict, render_config: dict, output_case_dir: str) -> None:
        print(f"Loading mesh {mesh_file}")
        # compute zoom factor to achieve desired spatial resolution
        mesh_spatial_resolution = 5.0  # TODO: get from GeoTIFF
        desired_spatial_resolution = terrain_dict["desired_spatial_resolution"]
        zoom_factor = mesh_spatial_resolution / desired_spatial_resolution

        with dem_tools.DEM(mesh_file) as dem:
            if zoom_factor != 1.0:
                dem.zoom(zoom_factor)
            elevation_data = dem.band1
            mesh_size = elevation_data.shape[0] * dem.res[0]
            ymin = dem.bounds[1]
            ymax = dem.bounds[3]
            xmin = dem.bounds[0]
            xmax = dem.bounds[2]

        dem_center_x = (xmin + xmax) / 2
        dem_center_y = (ymin + ymax) / 2
        dem_xmin_center = xmin - dem_center_x
        dem_ymin_center = ymin - dem_center_y
        dem_xmax_center = xmax - dem_center_x
        dem_ymax_center = ymax - dem_center_y

        self.terrain_interpolant = self.get_terrain_interpolant(
            elevation_data,
            dem_xmin_center,
            dem_ymin_center,
            dem_xmax_center,
            dem_ymax_center,
        )

        if terrain_dict.get("add_craters", True):
            crater_field = CraterField()
            crater_density = sample(terrain_dict["crater_field"]["density"])
            crater_field.generate(
                k=crater_density,
                size_y=ymax - ymin,
                size_x=xmax - xmin,
                h_min=terrain_dict["crater_field"]["h_min"],
                h_max=terrain_dict["crater_field"]["h_max"],
                x_init=0,
                y_init=0,
            )
            crater_field.save(str(Path(output_case_dir) / Path("crater_field.csv")))
            elevation_data = crater_field.place_craters_dem(crater_field.craters, elevation_data)

        mesh_material = terrain_dict.get("mesh_material", "Regolith7_MAT")
        start_time = time.time()
        blender_helper.load_mesh_from_array(elevation_data, mesh_size, mesh_material)
        print(f"Time to load mesh: {dth(time.time() - start_time)}")

        if terrain_dict.get("add_rocks", True):
            rock_field = RockField()
            rock_density = sample(terrain_dict["rock_field"]["density"])
            rock_field.generate_rock_field(
                k=rock_density,
                size_y=ymax - ymin,
                size_x=xmax - xmin,
                h_min=terrain_dict["rock_field"]["h_min"],
                h_max=terrain_dict["rock_field"]["h_max"],
                x_init=dem_xmin_center,
                y_init=dem_ymin_center,
            )
            output_rock_field = str(Path(output_case_dir) / Path("rock_field.csv"))
            rock_field.save(output_rock_field)
            rock_field.place_rocks(
                rock_field.rocks,
                rock_source=terrain_dict["rock_field"]["rock_source"],
                terrain_interpolant=self.terrain_interpolant,
            )

    def get_terrain_interpolant(
        self, elevation_data: np.ndarray, xmin: float, ymin: float, xmax: float, ymax: float
    ) -> RegularGridInterpolator:
        x = np.linspace(xmin, xmax, elevation_data.shape[0])
        y = np.linspace(ymin, ymax, elevation_data.shape[1])
        terrain_interpolant = RegularGridInterpolator(
            (x, y), np.flipud(elevation_data), bounds_error=False, fill_value=None
        )
        return terrain_interpolant
