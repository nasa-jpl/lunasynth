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
import lunasynth.craters as craters
import lunasynth.dem_tools as dem_tools
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from mathutils import Vector
from scipy.interpolate import (
    RegularGridInterpolator,  # interp2d is deprecated
    interp1d,
)


def dth(d: float, minimum_unit: str = "microseconds") -> str:
    return humanize.precisedelta(dt.timedelta(seconds=d), minimum_unit=minimum_unit)


def cumsumr(v: np.ndarray) -> np.ndarray:
    """Cumsum from the end"""
    return np.cumsum(v[::-1])[::-1]


# Rock abundance model of the Moon: q = A + B / k (Li & Wu, 2018, JGR Planets 123, 1061-1088, Eq. 6,
# https://doi.org/10.1029/2017JE005496), fitted to rocks in Chang'E-3 descent images and LRO NAC images.
LUNAR_ROCK_A = 0.5648
LUNAR_ROCK_B = 0.01285


@dataclass
class CfaModel:
    """Cumulative fractional area model of rock size-frequency distributions.

    The fraction of the surface covered by rocks larger than D is ``F(D) = k exp(-q(k) D)`` with
    ``q(k) = A + B / k`` (Golombek & Rapp, 1997, https://doi.org/10.1029/96JE03319). The default A and B are the
    lunar values of Li & Wu (2018). This model describes rocks only; craters follow power-law size distributions,
    see :mod:`lunasynth.craters`.
    """

    value_min: float
    value_max: float
    density: float

    def __init__(
        self,
        value_min: float,
        value_max: float,
        density: float,
        n_points: int = 1000,
        A: float = LUNAR_ROCK_A,
        B: float = LUNAR_ROCK_B,
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
        A: float = LUNAR_ROCK_A,
        B: float = LUNAR_ROCK_B,
    ) -> None:
        """Generates a rock field with rocks of random size, height, and position.
        The rocks are placed randomly within the specified size of the rock field.
        The height of the rocks is randomly generated between h_min and h_max.

        Args:
            k (float): The CFA value as a decimal (e.g. CFA5% would have an input of CFA=0.05)
            size_x (float): The size of the rock field in the x direction.
            size_y (float): The size of the rock field in the y direction.
            h_min (float): The minimum height of the rocks.
            h_max (float): The maximum height of the rocks. Default is 5.0.
            seed (int): The seed for the random number generator. Default is None.
            x_init (float): The initial x position of the rocks. Default is 0.
            y_init (float): The initial y position of the rocks. Default is 0.
            max_type_rocks (int): The maximum number of different types of rocks. Default is 15.
            A (float): Coefficient A of the rock abundance model q = A + B / k. Default is the lunar value.
            B (float): Coefficient B of the rock abundance model. Default is the lunar value.

        """
        self.size_x = size_x
        self.size_y = size_y
        self.k = k
        self.h_min = h_min
        self.h_max = h_max

        self.cfa_model = CfaModel(h_min, h_max, k, A=A, B=B)
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


# smallest crater, in pixels of the base DEM, that the base DEM is assumed to already contain (Robbins et al., 2014,
# consider craters smaller than ~10 pixels unreliable to measure)
DEFAULT_RESOLVABLE_PIXELS = 10.0


def crater_field_arguments(crater_config: dict, base_pixel_size: float) -> dict:
    """Arguments of :meth:`CraterField.generate` from the ``terrain.crater_field`` dataset configuration.

    Values can be distributions, see :func:`sample`. Only craters smaller than ``resolvable_pixels`` pixels of the
    base DEM (``base_pixel_size``) are added, because larger craters are already part of the base DEM. Set
    ``d_max`` to override it.
    """
    if "density" in crater_config:
        msg = (
            "crater_field.density is no longer supported: crater densities now follow the lunar production function. "
            "Set crater_field.surface_age_ga (Gyr) and crater_field.terrain ('highland' or 'mare') instead."
        )
        raise ValueError(msg)
    d_min = crater_config.get("d_min", crater_config.get("h_min", 2.0))
    resolvable = sample(crater_config.get("resolvable_pixels", DEFAULT_RESOLVABLE_PIXELS))
    d_max = crater_config.get("d_max", crater_config.get("h_max"))
    d_max = resolvable * base_pixel_size if d_max is None else min(sample(d_max), resolvable * base_pixel_size)
    arguments = {
        "surface_age_ga": sample(crater_config.get("surface_age_ga", 3.9)),
        "terrain": crater_config.get("terrain", "highland"),
        "d_min": sample(d_min),
        "d_max": d_max,
        "morphology": crater_config.get("morphology", "auto"),
        "visibility_depth_ratio": sample(
            crater_config.get("visibility_depth_ratio", craters.DEFAULT_VISIBILITY_DEPTH_RATIO)
        ),
        "chronology": crater_config.get("chronology", "neukum2001"),
    }
    if "regolith_thickness" in crater_config:
        arguments["regolith_thickness"] = sample(crater_config["regolith_thickness"])
    for key in ("kappa_800", "phi"):
        if key in crater_config:
            arguments[key] = sample(crater_config[key])
    return arguments


@dataclass
class Crater:
    """A crater, as generated and as currently visible after degradation.

    Positions are in meters in the terrain frame, centered on the base mesh (the same frame as rocks).

    Attributes:
        x: Center x coordinate, m.
        y: Center y coordinate, m.
        diameter: Current rim-to-rim diameter, m. Degradation widens craters up to ~1.5 times.
        diameter_initial: Diameter of the fresh crater, m.
        morphology_initial: Morphology of the fresh crater, one of :data:`lunasynth.craters.MORPHOLOGIES`.
        morphology: Current morphology. Degraded central-mound, flat-bottomed, and concentric craters become normal.
        age_myr: Age of the crater, Myr.
        degradation_state: Accumulated topographic diffusion K = kappa * age, m^2.
        depth: Current rim-to-floor depth, m.
        rim_height: Current rim height above the surroundings, m.

    """

    x: float
    y: float
    diameter: float
    diameter_initial: float | None = None
    morphology_initial: str = "normal"
    morphology: str = "normal"
    age_myr: float = 0.0
    degradation_state: float = 0.0
    depth: float | None = None
    rim_height: float | None = None

    def __post_init__(self) -> None:
        if self.diameter_initial is None:
            self.diameter_initial = self.diameter
        if self.depth is None or self.rim_height is None:
            # from the degraded profile of the crater
            h = self.profile(np.linspace(0.0, 2.5, 501))
            if self.depth is None:
                self.depth = float(h.max() - h.min())
            if self.rim_height is None:
                self.rim_height = float(h.max())

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))

    def crater_depth(self, r: float) -> float:
        """Elevation / fresh diameter of the fresh crater at ``r`` crater radii from the center."""
        return float(craters.fresh_profile(r, self.diameter_initial, self.morphology_initial)[0])

    def profile(self, r: np.ndarray) -> np.ndarray:
        """Elevation in meters of the degraded crater at ``r`` fresh radii from the center."""
        table = craters.profile_table()
        h = craters.crater_profiles(
            table,
            np.array([craters.MORPHOLOGIES.index(self.morphology_initial)]),
            np.array([self.diameter_initial]),
            np.array([self.degradation_state]),
        )[0]
        return np.interp(np.asarray(r, dtype=float), table.radii, h, right=0.0) * self.diameter_initial

    def compute_elevation_patch(self, n: int = 100) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Elevation in meters of the crater on a grid of ``n`` x ``n`` points spanning 2.5 fresh radii."""
        x = np.linspace(-2.5, 2.5, n)
        y = np.linspace(-2.5, 2.5, n)
        X, Y = np.meshgrid(x, y)
        self.elevation_patch = self.profile(np.hypot(X, Y))
        return self.elevation_patch, x, y

    def add_crater_mesh(self, verts: np.ndarray) -> np.ndarray:
        """Add the crater to mesh vertex coordinates (N x 3, meters) in place."""
        radius = self.diameter_initial / 2.0
        d = np.hypot(verts[:, 0] - self.x, verts[:, 1] - self.y) / radius
        near = d < craters.COMMON.ejecta_extent * 2.0
        verts[near, 2] += self.profile(d[near])
        return verts


CRATER_CSV_COLUMNS = (
    "x",
    "y",
    "diameter",
    "diameter_initial",
    "morphology_initial",
    "morphology",
    "age_myr",
    "degradation_state",
    "depth",
    "rim_height",
)


class CraterField:
    """A set of craters added to a terrain.

    Craters are generated with :func:`lunasynth.craters.generate_population`: sizes and ages follow the lunar
    production and chronology functions, each crater is degraded by topographic diffusion for its age, and only
    craters still visible are kept. See ``docs/craters.md`` for the model and references.
    """

    def __init__(self) -> None:
        self.craters: list[Crater] = []

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
        size_x: float,
        size_y: float,
        surface_age_ga: float,
        terrain: str = "highland",
        d_min: float = 2.0,
        d_max: float = 50.0,
        morphology: str = "auto",
        regolith_thickness: float | None = None,
        visibility_depth_ratio: float = craters.DEFAULT_VISIBILITY_DEPTH_RATIO,
        chronology: str = "neukum2001",
        kappa_800: float | None = None,
        phi: float | None = None,
        seed: int | None = None,
        x_init: float = 0.0,
        y_init: float = 0.0,
    ) -> None:
        """Generate the visible craters of a surface.

        Args:
            size_x: Size of the area in the x direction, m.
            size_y: Size of the area in the y direction, m.
            surface_age_ga: Age of the surface in Gyr. Polar highlands are about 3.5-3.9 Gyr old.
            terrain: "highland" or "mare". Selects the degradation rate and the regolith thickness.
            d_min: Smallest fresh crater diameter, m.
            d_max: Largest fresh crater diameter, m. Craters larger than what the base DEM resolves are already in it.
            morphology: "auto" to select it from the regolith thickness, or one of
                :data:`lunasynth.craters.MORPHOLOGIES`.
            regolith_thickness: Median regolith thickness, m. Defaults to the typical value of the terrain.
            visibility_depth_ratio: Craters with a smaller depth / diameter are not generated.
            chronology: "neukum2001" or "yue2022".
            kappa_800: Diffusivity at 800 m in m^2/Myr, overrides the terrain value (needs ``phi``).
            phi: Exponent of the size dependence of the diffusivity.
            seed: Seed of the random number generator.
            x_init: Smallest x coordinate of the area, m.
            y_init: Smallest y coordinate of the area, m.

        """
        diffusivity = None
        if kappa_800 is not None or phi is not None:
            if kappa_800 is None or phi is None:
                msg = "kappa_800 and phi must be given together"
                raise ValueError(msg)
            diffusivity = craters.Diffusivity(kappa_800, phi)
        self.size_x = size_x
        self.size_y = size_y
        population = craters.generate_population(
            size_x,
            size_y,
            surface_age_ga,
            terrain=terrain,
            d_min=d_min,
            d_max=d_max,
            morphology=morphology,
            regolith_thickness=regolith_thickness,
            visibility_depth_ratio=visibility_depth_ratio,
            chronology=chronology,
            diffusivity=diffusivity,
            x_init=x_init,
            y_init=y_init,
            rng=np.random.default_rng(seed),
        )
        self.craters = [
            Crater(
                x=float(population.x[i]),
                y=float(population.y[i]),
                diameter=float(population.diameter[i]),
                diameter_initial=float(population.diameter_initial[i]),
                morphology_initial=craters.MORPHOLOGIES[population.morphology_initial[i]],
                morphology=craters.MORPHOLOGIES[population.morphology[i]],
                age_myr=float(population.age_myr[i]),
                degradation_state=float(population.degradation_state[i]),
                depth=float(population.depth[i]),
                rim_height=float(population.rim_height[i]),
            )
            for i in range(len(population))
        ]
        print(
            f"Generated {len(self.craters)} visible craters of {d_min:g}-{d_max:g} m on a {surface_age_ga:g} Gyr "
            f"{terrain} surface"
        )

    def from_csv(self, filename: str) -> None:
        """Load craters from a CSV file. Files with only x, y and diameter load as fresh normal craters."""
        import csv

        craters_list = []
        with open(filename, newline="") as csvfile:
            for row in csv.DictReader(csvfile):
                values = {}
                for key, value in row.items():
                    if key in ("morphology_initial", "morphology"):
                        values[key] = value
                    elif key in CRATER_CSV_COLUMNS:
                        values[key] = float(value)
                craters_list.append(Crater(**values))
        self.craters = craters_list

    def save(self, filename: str) -> None:
        import csv

        # create parent directory if it does not exist
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(CRATER_CSV_COLUMNS)
            writer.writerows([[getattr(crater, column) for column in CRATER_CSV_COLUMNS] for crater in self.craters])

    def place_craters_mesh(self, craters_list: list[Crater], mesh) -> None:
        """Add craters to a Blender mesh. Vertex coordinates are in the same frame as the craters."""
        verts = np.array([vert.co for vert in mesh.vertices])

        start = time.time()
        for crater in tqdm.tqdm(craters_list, desc="Adding craters"):
            verts = crater.add_crater_mesh(verts)
        print(f"Time to add craters {dth(time.time() - start)}")

        start = time.time()
        for i, vert in enumerate(mesh.vertices):
            vert.co = verts[i]
        mesh.update()
        print(f"Time to update mesh {dth(time.time() - start)}")

    def place_craters_dem(
        self,
        craters_list: list[Crater],
        dem: np.ndarray,
        pixel_size: float = 1.0,
        x_min: float = 0.0,
        y_max: float | None = None,
    ) -> np.ndarray:
        """Add craters to a DEM array in place.

        Crater coordinates are in meters. Column 0 of the DEM is at ``x = x_min``. If ``y_max`` is given, row 0 is
        at ``y = y_max`` and rows go towards -y (north up, as in GeoTIFFs and in
        :func:`blender_helper.load_mesh_from_array`). Otherwise row 0 is at ``y = 0`` and rows go towards +y.

        Args:
            craters_list: Craters to add.
            dem: Elevation array, modified in place.
            pixel_size: DEM pixel size, m.
            x_min: x coordinate of column 0, m.
            y_max: y coordinate of row 0, m.

        """
        if len(craters_list) == 0:
            return dem
        x = np.array([crater.x for crater in craters_list])
        y = np.array([crater.y for crater in craters_list])
        cols = (x - x_min) / pixel_size
        rows = y / pixel_size if y_max is None else (y_max - y) / pixel_size
        start = time.time()
        craters.add_craters_to_dem(
            dem,
            rows,
            cols,
            diameters=np.array([crater.diameter_initial for crater in craters_list]),
            morphology=np.array([craters.MORPHOLOGIES.index(crater.morphology_initial) for crater in craters_list]),
            degradation_states=np.array([crater.degradation_state for crater in craters_list]),
            pixel_size=pixel_size,
        )
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
        desired_spatial_resolution = terrain_dict["desired_spatial_resolution"]

        with dem_tools.DEM(mesh_file) as dem:
            base_pixel_size = dem.res[0]
            # zoom to achieve the desired spatial resolution
            zoom_factor = base_pixel_size / desired_spatial_resolution
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
            crater_field.generate(
                size_x=xmax - xmin,
                size_y=ymax - ymin,
                x_init=dem_xmin_center,
                y_init=dem_ymin_center,
                **crater_field_arguments(terrain_dict["crater_field"], base_pixel_size),
            )
            crater_field.save(str(Path(output_case_dir) / Path("crater_field.csv")))
            # load_mesh_from_array spans the mesh size with one vertex per DEM sample, from -x to +x along columns
            # and from +y to -y along rows
            vertex_spacing = mesh_size / (elevation_data.shape[1] - 1)
            elevation_data = crater_field.place_craters_dem(
                crater_field.craters,
                elevation_data,
                vertex_spacing,
                x_min=-mesh_size / 2,
                y_max=mesh_size / 2,
            )

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
