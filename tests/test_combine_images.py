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

from lunasynth.cli.combine_images import main


def test_combine_images(caplog, monkeypatch, tmp_path):
    # render it
    output_path = tmp_path / Path("combined_basic")
    test_args = [
        "combine_images.py",
        "tests/resources/combine_images",
        "--prefixes",
        "rock",
        "pebble",
        "--output-prefix",
        "rocks",
        "--output-dir",
        str(output_path),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    # list files in output directory
    print(f"files in output_path {list(output_path.iterdir())}")

    print(f'{str(output_path / Path("rocks_0000.png"))}')

    assert (output_path / Path("rocks_0000.png")).exists()
    assert (output_path / Path("rocks_0001.png")).exists()


def test_combine_images_collage(caplog, monkeypatch, tmp_path):
    output_path = tmp_path / Path("combined_collage")
    test_args = [
        "combine_images.py",
        "tests/resources/combine_images",
        "--prefixes",
        "rock",
        "pebble",
        "--output-dir",
        str(output_path),
        "--collage",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    assert len(list(output_path.iterdir())) == 1  # only one file
    assert (output_path / Path("combined.png")).exists()

    output_path = tmp_path / Path("combined_collage_prefixes")
    # test with output prefix
    test_args = [
        "combine_images.py",
        "tests/resources/combine_images",
        "--prefixes",
        "rock",
        "pebble",
        "--output-prefix",
        "rocks",
        "--output-dir",
        str(output_path),
        "--collage",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    assert len(list(output_path.iterdir())) == 1  # only one file
    assert (output_path / Path("rocks.png")).exists()
