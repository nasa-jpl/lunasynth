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

import copy
import glob
import json
import logging
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import humanize
import lunasynth.blender_helper as bh
import lunasynth.terrain_enhancement as terrain_enhancement
import numpy as np


def dth(d: float, minimum_unit: str = "microseconds") -> str:
    """Converts a time in seconds to a human readable string"""
    return humanize.precisedelta(timedelta(seconds=d), minimum_unit=minimum_unit)


class CaseManager:
    cases_list: list[dict]

    def __init__(self) -> None:
        pass

    def cases_grid_sizes(self, render_distributions: dict, n_cases: int) -> tuple[dict[str, int], int]:
        grid_sizes = {}
        for param_value in render_distributions:
            if render_distributions[param_value]["type"] == "grid":
                grid_sizes[param_value] = render_distributions[param_value]["n_values"]
            elif render_distributions[param_value]["type"] == "grid_list":
                grid_sizes[param_value] = len(render_distributions[param_value]["values"])
        print(f"Grid sizes: {grid_sizes}")

        total_grid_cases = self.get_total_grid_cases(grid_sizes)
        print(f"Total grid cases: {total_grid_cases}")

        if n_cases < total_grid_cases:
            print(
                f"Number of cases {n_cases} is too small for the grid cases  {total_grid_cases}."
                f" Setting cases to {total_grid_cases}"
            )
            n_cases = total_grid_cases
        return grid_sizes, n_cases

    def get_total_grid_cases(self, grid_sizes: dict[str, int]) -> int:
        total_grid_cases = 1
        for param_value in grid_sizes:
            total_grid_cases *= grid_sizes[param_value]
        return total_grid_cases

    def cases_grid_indices(self, grid_sizes: dict[str, int], i: int) -> dict[str, int]:
        grid_indices = {}
        i_cases = i % self.get_total_grid_cases(grid_sizes)
        acc_grid_base = 1
        for param_value in grid_sizes:
            grid_indices[param_value] = (i_cases // acc_grid_base) % grid_sizes[param_value]
            acc_grid_base *= grid_sizes[param_value]
        return grid_indices

    def number_grid_params(self, distributions: dict) -> int:
        return sum(
            [
                1
                for param_value in distributions
                if distributions[param_value]["type"] == "grid" or distributions[param_value]["type"] == "grid_list"
            ]
        )

    def generate_cases(self, render_distributions: dict, n_cases: int, camera_type: str) -> list[dict]:
        cases_list = []
        n_grid = self.number_grid_params(render_distributions)
        if n_grid > 0:
            grid_sizes, n_cases = self.cases_grid_sizes(render_distributions, n_cases)

        for i in range(n_cases):
            param_values = {}
            if n_grid > 0:
                grid_indices = self.cases_grid_indices(grid_sizes, i)
                print(f"Grid indices: {grid_indices}")
            for param_value in render_distributions:
                assert "type" in render_distributions[param_value]
                if render_distributions[param_value]["type"] == "uniform":
                    assert "min" in render_distributions[param_value]
                    assert "max" in render_distributions[param_value]
                    param_values[param_value] = random.uniform(
                        render_distributions[param_value]["min"],
                        render_distributions[param_value]["max"],
                    )
                elif render_distributions[param_value]["type"] == "normal":
                    assert "mean" in render_distributions[param_value]
                    assert "std" in render_distributions[param_value]
                    param_values[param_value] = random.normalvariate(
                        render_distributions[param_value]["mean"],
                        render_distributions[param_value]["std"],
                    )
                elif render_distributions[param_value]["type"] == "list":
                    assert "values" in render_distributions[param_value]
                    param_values[param_value] = random.choice(render_distributions[param_value]["values"])
                elif render_distributions[param_value]["type"] == "fixed":
                    assert "value" in render_distributions[param_value]
                    param_values[param_value] = render_distributions[param_value]["value"]
                elif render_distributions[param_value]["type"] == "grid":
                    assert "min" in render_distributions[param_value]
                    assert "max" in render_distributions[param_value]
                    assert "n_values" in render_distributions[param_value]

                    grid_min = render_distributions[param_value]["min"]
                    grid_max = render_distributions[param_value]["max"]
                    n_values = render_distributions[param_value]["n_values"]
                    grid_index = grid_indices[param_value]
                    grid_value = grid_min + (grid_max - grid_min) * grid_index / (n_values - 1)
                    param_values[param_value] = grid_value
                elif render_distributions[param_value]["type"] == "grid_list":
                    assert "values" in render_distributions[param_value]
                    grid_values = render_distributions[param_value]["values"]
                    grid_index = grid_indices[param_value]
                    param_values[param_value] = grid_values[grid_index]
                else:
                    msg = f"Unknown sampling type: {render_distributions[param_value]['type']}"
                    raise ValueError(msg)
            cases_list.append(param_values)
        return cases_list

    def save_cases_description(self, cases_dict: dict) -> None:
        os.makedirs(cases_dict["cases_config"]["output_dir"], exist_ok=True)
        print(f"Saving cases description to {cases_dict['cases_config']['output_dir']}")
        with open(
            str(Path(cases_dict["cases_config"]["output_dir"]) / Path("params.json")),
            "w",
        ) as f:
            json.dump(cases_dict, f, indent=4, sort_keys=True)
        print(f"Cases description saved to {cases_dict['cases_config']['output_dir']}")


class PathEncoder(json.JSONEncoder):
    def default(self, obj: str | Path) -> str:
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


@dataclass
class RenderingManager:
    dataset_config: dict
    time_rendering: list[float]
    time_terrain_creation: list[float]
    time_terrain: list[float]
    time_mesh: list[float]
    render_index: int = 0
    terrain_index: int = 0
    base_mesh_index: int = 0
    redner_case_index: int = 0
    default_dataset_name: str = "dataset"

    def __init__(
        self,
        dataset_config: dict,
        default_dataset_name: str = "dataset",
    ):
        self.dataset_config = dataset_config
        self.time_rendering = []
        self.time_terrain = []
        self.time_terrain_creation = []
        self.time_mesh = []
        self.set_loggers()
        self.default_dataset_name = default_dataset_name

    def setup_rendering(self, config: dict, output_dir: str | Path) -> None:
        print(f"Setting up rendering with config {config}")
        if "depth_output" in config and config["depth_output"]:
            bh.setup_depth_rendering(output_dir=output_dir)

        if "segmentation_output" in config and config["segmentation_output"]:
            bh.setup_segmentation_rendering(
                pass_index_function=lambda x: 2 if x == "Terrain" else 1,
                output_dir=output_dir,
                cases_dict=config,
            )

        if "camera_type" in config:
            bh.set_camera_type(config["camera_type"])

    def set_loggers(self) -> None:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("bpy").setLevel(logging.WARNING)
        logging.getLogger("lunasynth").setLevel(logging.INFO)

        self.logger = logging.getLogger(__name__)

        progress_logger = logging.FileHandler("progress.log")
        progress_logger.setLevel(logging.INFO)
        progress_logger.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(progress_logger)

    def generate_rendering_cases(
        self,
        render_distributions: dict,
        n_cases: int,
        camera_type: str,
        surface_z_interpolant: Callable | None = None,
    ) -> list[dict]:
        self.rendering_cases_manager = CaseManager()
        start = time.time()
        render_distributions = self.adjust_render_distributions(render_distributions, camera_type)
        print(f"Time to adjust render distributions: {dth(time.time() - start)}")
        start = time.time()
        cases_list = self.rendering_cases_manager.generate_cases(render_distributions, n_cases, camera_type)
        print(f"Time to generate cases: {dth(time.time() - start)}")
        start = time.time()
        cases_list = self.adjust_rendering_cases(cases_list, camera_type, surface_z_interpolant)
        print(f"Time to adjust cases: {dth(time.time() - start)}")
        return cases_list

    def generate_traj_cases(self, traj_config: dict) -> list[dict]:
        cases_list = []
        for traj_step in traj_config["trajectory"]:
            param_values = {
                "camera/x": traj_step["camera_x"],
                "camera/y": traj_step["camera_y"],
                "camera/z": traj_step["camera_z"],
                "camera/pitch": traj_step["camera_pitch"],
                "camera/yaw": traj_step["camera_yaw"],
                "sun/elevation": traj_config["scene"]["sun_elevation"],
                "sun/azimuth": traj_config["scene"]["sun_azimuth"],
            }
            cases_list.append(param_values)
        return cases_list

    def adjust_render_distributions(self, render_distributions: dict, camera_type: str = "ORTHO") -> dict:
        if "camera/x" not in render_distributions or "camera/y" not in render_distributions:
            print("Camera x and y not defined, fitting camera to mesh bounds")
            (xmin, ymin, zmin), (xmax, ymax, zmax) = bh.get_mesh_bounds()
            if camera_type == "ORTHO":
                if render_distributions["camera/ortho_scale"]["type"] == "fixed":
                    margin = render_distributions["camera/ortho_scale"]["value"] / 2.0
                else:
                    margin = render_distributions["camera/ortho_scale"]["max"] / 2.0
            else:
                print(f"render render_distributions: {render_distributions}")
                if render_distributions["camera/z"]["type"] == "fixed":
                    margin = render_distributions["camera/z"]["value"]
                elif render_distributions["camera/z"]["type"] == "uniform":
                    margin = render_distributions["camera/z"]["max"]
                elif render_distributions["camera/z"]["type"] == "normal":
                    margin = render_distributions["camera/z"]["mean"]
                else:
                    margin = 100
            render_distributions["camera/x"] = {
                "type": "uniform",
                "min": xmin + margin,
                "max": xmax - margin,
            }
            render_distributions["camera/y"] = {
                "type": "uniform",
                "min": ymin + margin,
                "max": ymax - margin,
            }
        return render_distributions

    def adjust_rendering_cases(
        self, cases_list: list[dict], camera_type: str = "ORTHO", surface_z_interpolant: Callable | None = None
    ) -> list[dict]:
        if camera_type == "ORTHO":
            camera_z_default = bh.fit_camera_to_mesh("Terrain")
            print(f"Adjusting cases for orthographic camera, default camera z: {camera_z_default}")
        else:
            camera_z_default = 100  # TODO: correct

        for case in cases_list:
            if "camera/z" not in case:
                case["camera/z"] = camera_z_default
            if "camera/pitch" not in case:
                case["camera/pitch"] = -np.pi / 2
            if "camera/yaw" not in case:
                case["camera/yaw"] = 0
            if camera_type == "PERSP" and surface_z_interpolant is not None:
                case["camera/z"] += surface_z_interpolant((case["camera/y"], case["camera/x"]))
        return cases_list

    def run_rendering_campaign(
        self,
        cases_dict: dict,
        output_case_dir: str,
    ) -> None:
        print(f"Rendering {len(cases_dict['cases_list'])} cases")
        for i, case in enumerate(cases_dict["cases_list"]):
            self.render_case_index = i
            if "camera/ortho_scale" in case:
                bh.set_camera_ortho_scale(case["camera/ortho_scale"])

            bh.set_camera_pose(
                case["camera/x"],
                case["camera/y"],
                case["camera/z"],
                case["camera/pitch"],
                case["camera/yaw"],
            )
            bh.set_sun_orientation(case["sun/elevation"], case["sun/azimuth"])
            rgb_filename = Path(output_case_dir) / Path(f"rgb_{i:03d}.png")
            start_time = time.time()
            render_filenames_list = bh.render_blender(output_filename=rgb_filename, index=i)
            self.time_rendering.append(time.time() - start_time)
            print(f"Time to render: {dth(time.time() - start_time)}")
            self.print_progress()
            case["files"] = render_filenames_list
            case["case_id"] = i
            case["time_to_render"] = self.time_rendering[-1]
            self.render_index += 1

    def adjust_dataset_config(self) -> None:
        if "name" not in self.dataset_config:
            self.dataset_config["name"] = self.default_dataset_name

        if "output_dir" not in self.dataset_config["output"]:
            if "output_root" not in self.dataset_config["output"]:
                self.dataset_config["output"]["output_root"] = "tmp"
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.dataset_config["output"]["output_dir"] = Path(self.dataset_config["output"]["output_root"]) / Path(
                self.dataset_config["name"] + "_" + date_str
            )
        os.makedirs(self.dataset_config["output"]["output_dir"], exist_ok=True)

        meshes_temp = []
        for mesh_filename in self.dataset_config["base_mesh"]["meshes"]:
            print(f"Mesh {mesh_filename} expanded to: {Path(mesh_filename).resolve()}")
            meshes_temp.extend(glob.glob(mesh_filename))
        # print(f"Resolved Meshes: {meshes_temp}")
        self.dataset_config["base_mesh"]["meshes"] = meshes_temp

        if (
            "resolution_x" in self.dataset_config["rendering"]
            and "camera_type" in self.dataset_config["rendering"]
            and self.dataset_config["rendering"]["camera_type"] == "ORTHO"
            and "desired_spatial_resolution" in self.dataset_config["terrain"]
        ):
            self.dataset_config["rendering_cases"]["distributions"]["camera/ortho_scale"] = {
                "type": "fixed",
                "value": self.dataset_config["rendering"]["resolution_x"]
                * self.dataset_config["terrain"]["desired_spatial_resolution"],
            }

    def save_config(self, config: dict, name: str = "dataset_config.json") -> None:
        output_dir = str(Path(self.dataset_config["output"]["output_dir"]) / Path(name))
        print(f"Saving config {name} to {output_dir}")
        with open(output_dir, "w") as f:
            json.dump(config, f, cls=PathEncoder)

    def print_progress(self) -> None:
        if len(self.time_rendering) > 0:
            # Evaluate time left based on measured time: on the first render,
            # we use the average time per rendering to get an early estimate.
            # Once a terrain or a mesh have completed,
            # we use the average time per terrain or mesh to get a better estimate.
            # Use 'tail -f progress.log' to see the progress

            renderings_left_this_terrain = self.n_rendering_cases - self.render_case_index - 1
            time_renderings_this_terrain = np.average(self.time_rendering) * renderings_left_this_terrain

            terrains_left_this_mesh = self.n_terrain - self.terrain_index - 1
            if len(self.time_terrain) > 0:
                time_per_terrain = np.average(self.time_terrain)
            elif len(self.time_terrain_creation) > 0:
                time_per_terrain = (
                    np.average(self.time_terrain_creation) + np.average(self.time_rendering) * self.n_rendering_cases
                )
            else:
                time_per_terrain = np.average(self.time_rendering) * self.n_rendering_cases
            time_terrains_left_this_mesh = terrains_left_this_mesh * time_per_terrain

            meshes_left = self.n_meshes - self.base_mesh_index - 1
            if len(self.time_mesh) > 0:
                time_per_mesh = np.average(self.time_mesh)
            else:
                time_per_mesh = self.n_terrain * time_per_terrain
            time_meshes_left = meshes_left * time_per_mesh
            time_left = time_meshes_left + time_terrains_left_this_mesh + time_renderings_this_terrain
            # print(
            #     time_meshes_left,
            #     time_terrains_left_this_mesh,
            #     time_renderings_this_terrain,
            # )
            # print(f"Time left: {time_left}")
            expected_end = datetime.now() + timedelta(seconds=time_left)

            time_str = (
                f"Time left: {humanize.naturaldelta(time_left, minimum_unit='seconds')}, "
                f"Expected end: {expected_end:%Y-%m-%d %H:%M}"
            )
        else:
            time_str = ""
        self.logger.info(
            f"Progress {self.render_index}/{self.planned_cases}: {self.base_mesh_index+1}/{self.n_meshes} meshes,"
            f" {self.terrain_index+1}/{self.n_terrain} terrains, "
            f"{self.render_case_index+1}/{self.n_rendering_cases} rendering cases, {time_str}"
        )

    def run_dataset_generation(self) -> None:
        original_dataset_config = copy.deepcopy(self.dataset_config)
        self.adjust_dataset_config()
        self.save_config(original_dataset_config, "original_dataset_config.json")
        self.save_config(self.dataset_config, "adjusted_dataset_config.json")

        self.dataset_config_name = self.dataset_config["name"]
        executed_cases = 0
        meshes = self.dataset_config["base_mesh"]["meshes"]
        self.n_meshes = len(meshes)
        self.n_terrain = self.dataset_config["terrain"]["samples"]
        self.n_rendering_cases = self.dataset_config["rendering_cases"]["cases"]
        planned_cases = self.n_meshes * self.n_terrain * self.n_rendering_cases
        self.planned_cases = planned_cases
        print(
            f"Planned cases {planned_cases}: {self.n_meshes} meshes x {self.n_terrain} "
            f"terrains x {self.n_rendering_cases} rendering cases"
        )
        if self.dataset_config.get("dry_run", False):
            print("Dry run, skipping")
            return
        base_path = Path(self.dataset_config["output"]["output_dir"])
        self.logger.info(
            f"Starting rendering campaign for {self.dataset_config_name} config"
            f"in {self.dataset_config['output']['output_dir']} of {planned_cases} cases"
        )
        start_time_dataset = time.time()
        for mesh_base_index, mesh_file in enumerate(meshes):
            start_time_mesh = time.time()
            print(f"Generating terrain instances for {mesh_file}")
            self.base_mesh_index = mesh_base_index
            for terrain_index in range(self.dataset_config["terrain"]["samples"]):
                start_time_terrain = time.time()
                self.terrain_index = terrain_index
                if self.dataset_config.get("dry_run_terrain_generation", False):
                    continue
                print(f"Generating terrain {terrain_index}")
                output_case_dir = (
                    base_path / Path(f"mesh_{Path(mesh_file).stem}") / Path(f"terrain_{terrain_index:02d}")
                )

                cases_dict = self.run_terrain_rendering(
                    terrain_dict=self.dataset_config["terrain"],
                    mesh_file=mesh_file,
                    cases_config=self.dataset_config["rendering_cases"],
                    render_config=self.dataset_config["rendering"],
                    output_case_dir=str(output_case_dir),
                    dry_run_rendering=self.dataset_config.get("dry_run_rendering", False),
                )
                executed_cases += len(cases_dict["cases_list"])
                self.time_terrain.append(time.time() - start_time_terrain)
            self.time_mesh.append(time.time() - start_time_mesh)
        print(f"Executed cases: {executed_cases}/{planned_cases}")
        self.logger.info(
            f"Rendering done, {executed_cases} cases executed in "
            f"{humanize.naturaldelta(time.time() - start_time_dataset)}"
        )

    def run_terrain_rendering(
        self,
        terrain_dict: dict,
        mesh_file: str,
        cases_config: dict,
        render_config: dict,
        output_case_dir: str,
        dry_run_rendering: bool = False,
    ) -> dict:
        print("Setting up scene")
        bh.setup_moon_scene(device=render_config.get("device", "GPU"))
        bh.setup_render_config(render_config)

        camera_type = render_config.get("camera_type", "ORTHO")
        terrain = terrain_enhancement.Terrain()
        start = time.time()
        terrain.generate(mesh_file, terrain_dict, render_config, output_case_dir)
        self.time_terrain_creation.append(time.time() - start)
        print(f"Time to generate terrain: {dth(time.time() - start)}")

        start = time.time()
        cases_dict = {
            "cases_config_file": cases_config,
            "cases_config": cases_config,
            "cases_list": [],
            "blend_file": mesh_file,
        }
        cases_dict["cases_list"] = self.generate_rendering_cases(
            render_distributions=cases_config["distributions"],
            n_cases=cases_config["cases"],
            camera_type=camera_type,
            surface_z_interpolant=terrain.terrain_interpolant,
        )  # it has to run after adding the mesh during terrain generation
        print(f"Time to generate cases: {dth(time.time() - start)}")

        if not dry_run_rendering:
            self.setup_rendering(render_config, output_dir=output_case_dir)
            self.run_rendering_campaign(cases_dict, output_case_dir)
        if isinstance(cases_dict["cases_config"], dict):
            cases_dict["cases_config"]["output_dir"] = str(output_case_dir)
        CaseManager().save_cases_description(cases_dict)

        if self.dataset_config["output"].get("add_rendering_cases_blender", False):
            start = time.time()
            bh.add_cases_visalization(cases_dict["cases_list"], connect_cases=False)
            print(f"Time to add cases visualization: {dth(time.time() - start)}")

        if self.dataset_config["output"].get("save_blender_file", False):
            start = time.time()
            output_blend_file = str(Path(output_case_dir) / Path("terrain.blend"))
            bh.save_blender_file(output_blend_file)
            print(f"Time to save blend file: {dth(time.time() - start)}")
        return cases_dict
