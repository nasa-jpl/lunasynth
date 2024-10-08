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

from lunasynth.cli.create_rock_field import main


def test_create_rock_field(capsys, monkeypatch, tmp_path):
    # render it
    temp_file = tmp_path / Path("test_rock_field.csv")
    test_args = [
        "create_rock_field.py",
        "--CFA",
        "0.06",
        "--size_x",
        "10",
        "--size_y",
        "10",
        "--h_min",
        "0.4",
        "--h_max",
        "6.0",
        "--output",
        str(temp_file),
    ]
    print(test_args)
    monkeypatch.setattr("sys.argv", test_args)
    main()
    assert temp_file.exists()
