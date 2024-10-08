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

from lunasynth.cli.assign_pass_index import main as main_assign_pass_index
from lunasynth.cli.render_blendfile import main


def test_render_blendfile_basic(caplog, monkeypatch, tmp_path):
    # render it

    output_path = tmp_path / Path("test_render_blendfile_basic")
    test_args = [
        "render_blendfile.py",
        "tests/resources/test_load_rocks.blend",
        "--output-dir",
        str(output_path),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    # get files in output directory
    files = list(output_path.glob("*"))
    assert len(files) == 1
    assert files[0].name == "test_load_rocks.png"


def test_render_blendfile_depth(caplog, monkeypatch, tmp_path):
    # render it

    output_path = tmp_path / Path("test_render_blendfile_depth")
    test_args = [
        "render_blendfile.py",
        "tests/resources/test_load_rocks.blend",
        "--output-dir",
        str(output_path),
        "--depth",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    # get files in output directory
    files = list(output_path.glob("*"))
    assert len(files) == 3
    assert "test_load_rocks.png" in [f.name for f in files]
    assert "depth.exr" in [f.name for f in files]
    assert "depth_norm.png" in [f.name for f in files]


def test_render_blendfile_segmentation(caplog, monkeypatch, tmp_path):
    output_path = tmp_path / Path("test_render_blendfile_segmentation")
    test_args = [
        "render_blendfile.py",
        "tests/resources/test_load_rocks.blend",
        "--output-dir",
        str(output_path),
        "--segmentation",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    # get files in output directory
    files = list(output_path.glob("*"))
    assert len(files) == 3
    assert "test_load_rocks.png" in [f.name for f in files]
    assert "segmentation_integer.png" in [f.name for f in files]
    assert "segmentation_color.png" in [f.name for f in files]


def test_assign_pass_index(caplog, monkeypatch, tmp_path):
    output_path = tmp_path / Path("test_assign_pass_index")
    output_file = output_path / Path("test_load_rocks_pass_index.blend")
    test_args = [
        "assign_pass_index.py",
        "--blend_file",
        "tests/resources/test_load_rocks.blend",
        "--output_file",
        str(output_file),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main_assign_pass_index()
    captured = caplog.text
    print(captured)

    # get files in output directory
    # assert len(files) == 1
    # assert files[0] == "test_load_rocks_pass_index.blend"
