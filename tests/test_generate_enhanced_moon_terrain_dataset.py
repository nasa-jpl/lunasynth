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


import os
from pathlib import Path

from lunasynth.cli.generate_enhanced_moon_terrain_dataset import main


def test_generate_enhanced_moon_terrain_dataset_ortho(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / Path("test_generate_enhanced_moon_terrain_dataset_ortho")
    n_cases = 3
    n_terrains = 3
    test_args = [
        "generate_enhanced_moon_terrain_dataset.py",
        "--dataset-config",
        "tests/resources/dataset_config/test_ortho_minimal.yaml",
        "--set",
        "output.output_dir=" + str(output_dir),
        "rendering_cases.cases=" + str(n_cases),
        "terrain.samples=" + str(n_terrains),
        "output.save_blender_file=true",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    mesh_str = "mesh_mesh_100m_5mpix"
    assert (output_dir).exists()
    assert (output_dir / mesh_str).exists()
    for terrain_index in range(n_terrains):
        terrain_str = f"terrain_{terrain_index:02d}"
        assert (output_dir / mesh_str / terrain_str).exists()
        assert (output_dir / mesh_str / terrain_str / "params.json").exists()
        assert (output_dir / mesh_str / terrain_str / "crater_field.csv").exists()
        assert (output_dir / mesh_str / terrain_str / "rock_field.csv").exists()
        assert (output_dir / mesh_str / terrain_str / "terrain.blend").exists()

        # Check how many images
        images = [f for f in os.listdir(output_dir / mesh_str / terrain_str) if f.endswith(".png")]
        print(images)

        prefixes_expected = [
            "rgb",
            "depth_norm",
            "segmentation_integer",
            "segmentation_color",
        ]

        for prefix in prefixes_expected:
            for case_index in range(n_cases):
                assert f"{prefix}_{case_index:03d}.png" in images


def test_generate_enhanced_moon_terrain_dataset_persp(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / Path("test_generate_enhanced_moon_terrain_dataset_persp")
    n_cases = 10
    test_args = [
        "generate_enhanced_moon_terrain_dataset.py",
        "--dataset-config",
        "tests/resources/dataset_config/test_persp_minimal.yaml",
        "--set",
        "output.output_dir=" + str(output_dir),
        "rendering_cases.cases=" + str(n_cases),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    assert (output_dir).exists()
