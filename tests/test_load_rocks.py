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

from lunasynth.cli.load_rocks import main


def test_load_rocks(caplog, monkeypatch, tmp_path):
    # render it

    test_args = [
        "load_rocks.py",
        "--blend-file",
        "tests/resources/test_load_rocks.blend",
        "--rock-field-file",
        "tests/resources/test_rock_field.csv",
        "--output-blend-file",
        str(tmp_path / Path("test_load_rocks_rocks.blend")),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    main()
    captured = caplog.text
    print(captured)

    assert (tmp_path / Path("test_load_rocks_rocks.blend")).exists()
