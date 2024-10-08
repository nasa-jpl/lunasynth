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


from pathlib import Path

from lunasynth.cli.visualize_cases_blender import main


def test_visualize_cases_blender(capsys, monkeypatch, tmp_path):
    output_dir = tmp_path / Path("test_visualize_cases_blender")
    output_file = output_dir / "test_visualize_cases.blend"
    test_args = [
        "visualize_cases_blender.py",
        "--blend_file",
        "tests/resources/test_load_rocks.blend",
        "--config",
        "tests/resources/test_params.json",
        "--output-blend-file",
        str(output_file),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    assert (output_file).exists()
