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


from lunasynth.cli.process_sampling_cases import main


def test_process_sampling_cases_dry_run(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / "test_process_sampling_cases_grid"
    test_args = [
        "process_sampling_cases.py",
        "--blend_file",
        "tests/resources/test_load_rocks.blend",
        "--cases",
        "10",
        "--config",
        "tests/resources/test_cases_config.yaml",
        "--output-dir",
        str(output_dir),
        "--dry-run",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    assert (output_dir / "params.json").exists()

    # read params.json
    import json

    with open(output_dir / "params.json") as f:
        params = json.load(f)

    # check params
    assert "cases_config" in params
    assert "cases_config_file" in params
    assert "cases_list" in params
    assert len(params["cases_list"]) == 24

    required_case_params = [
        "camera/x",
        "camera/y",
        "camera/z",
        "camera/pitch",
        "camera/yaw",
        "sun/elevation",
        "sun/azimuth",
    ]
    for case in params["cases_list"]:
        for param in required_case_params:
            assert param in case


def test_process_sampling_cases_simple(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / "test_process_sampling_cases_simple"
    test_args = [
        "process_sampling_cases.py",
        "--blend_file",
        "tests/resources/test_load_rocks.blend",
        "--cases",
        "2",
        "--config",
        "tests/resources/test_cases_config_simple.yaml",
        "--output-dir",
        str(output_dir),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()

    # Check files in output dir
    output_files = list(output_dir.glob("*"))
    output_files = [f.stem for f in output_files]

    assert len(output_files) == 11
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
