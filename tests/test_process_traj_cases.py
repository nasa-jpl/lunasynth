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


import json
from pathlib import Path

from lunasynth.cli.generate_traj_definition import main as main_traj_definition
from lunasynth.cli.process_traj_cases import main as main_process_traj_cases


def test_generate_traj_definition(capsys, monkeypatch, tmp_path):
    output_file = tmp_path / Path("test_traj_definition.json")
    test_args = [
        "generate_traj_definition.py",
        "--trajectory",
        "tests/resources/test_trajectory.csv",
        "--scene",
        "tests/resources/test_scene_config.yaml",
        "--output",
        str(output_file),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main_traj_definition()
    assert output_file.exists()

    # Check the output json file
    with open(output_file) as f:
        output = json.load(f)

    print(output)
    assert "scene" in output
    assert "trajectory" in output
    assert len(output["trajectory"]) > 0
    expected_output = {
        "scene": {
            "sun_elevation": 0.1,
            "sun_azimuth": 0.0,
            "depth_output": True,
            "segmentation_output": True,
        },
        "trajectory": [
            {
                "t": 1.0,
                "camera_x": 0.0,
                "camera_y": 0.0,
                "camera_z": 12.0,
                "camera_pitch": -1.5707963267948963,
                "camera_yaw": 0.0,
            },
            {
                "t": 2.0,
                "camera_x": 0.0,
                "camera_y": 0.0,
                "camera_z": 14.0,
                "camera_pitch": -1.5707963267948963,
                "camera_yaw": 0.0,
            },
        ],
    }
    assert output == expected_output


def test_protraj_cases_dry_run(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / "test_protraj_cases"
    test_args = [
        "process_traj_cases.py",
        "tests/resources/test_load_rocks.blend",
        "--config",
        "tests/resources/test_traj_definition.json",
        "--output-dir",
        str(output_dir),
        "--dry-run",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main_process_traj_cases()
    assert (output_dir / "params.json").exists()


def test_protraj_cases_simple(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / Path("test_protraj_cases_2")
    test_args = [
        "process_traj_cases.py",
        "tests/resources/test_load_rocks.blend",
        "--config",
        "tests/resources/test_traj_definition.json",
        "--output-dir",
        str(output_dir),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main_process_traj_cases()

    assert (output_dir / "params.json").exists()

    # Check files in output dir
    output_files = list(output_dir.glob("*"))
    output_files = [f.stem for f in output_files]

    assert len(output_files) == 11
    print(output_files)
    prefixes_expected = [
        "rgb",
        "depth",
        "depth_norm",
        "segmentation_integer",
        "segmentation_color",
    ]

    for prefix in prefixes_expected:
        assert f"{prefix}_000" in output_files
        assert f"{prefix}_001" in output_files
