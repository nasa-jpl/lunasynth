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


import pytest
from lunasynth.configuration_manager import CaseManager, RenderingManager


def test_generate_cases():
    # generate the sampling cases
    config = {
        "cases": 10,
        "depth_output": True,
        "segmentation_output": True,
        "render_distributions": {
            "camera/x": {"type": "uniform", "min": -3000.0, "max": 3000.0},
            "camera/y": {"type": "uniform", "min": -3000.0, "max": 3000.0},
            "camera/z": {"type": "uniform", "min": 2000, "max": 2400},
            "camera/pitch": {"type": "fixed", "value": -1.57},
            "camera/yaw": {"type": "uniform", "min": 0.0, "max": 6.28},
            "sun/elevation": {"type": "uniform", "min": 0.14, "max": 0.26},
            "sun/azimuth": {"type": "uniform", "min": 0.0, "max": 6.28},
        },
    }
    cases_list = CaseManager().generate_cases(config["render_distributions"], config["cases"], "PERSP")
    assert len(cases_list) == 10
    for case in cases_list:
        assert "camera/x" in case
        assert case["camera/x"] >= -3000.0
        assert case["camera/x"] <= 3000.0
        assert "camera/y" in case
        assert case["camera/y"] >= -3000.0
        assert case["camera/y"] <= 3000.0
        assert "camera/z" in case
        assert case["camera/z"] >= 2000
        assert case["camera/z"] <= 2400
        assert "camera/pitch" in case
        assert case["camera/pitch"] == pytest.approx(-1.57)
        assert "camera/yaw" in case
        assert "sun/elevation" in case
        assert "sun/azimuth" in case


def test_generate_traj_cases():
    # generate the trajectory cases
    traj_config = {
        "trajectory": [
            {
                "camera_x": 0,
                "camera_y": 0,
                "camera_z": 2,
                "camera_pitch": -1.57,
                "camera_yaw": 0,
            },
            {
                "camera_x": 0,
                "camera_y": 0,
                "camera_z": 2,
                "camera_pitch": -1.57,
                "camera_yaw": 3.14,
            },
        ],
        "scene": {"sun_elevation": 0.14, "sun_azimuth": 0.0},
    }
    cases_list = RenderingManager({}).generate_traj_cases(traj_config)
    assert len(cases_list) == 2
    for case in cases_list:
        assert "camera/x" in case
        assert case["camera/x"] == 0
        assert "camera/y" in case
        assert case["camera/y"] == 0
        assert "camera/z" in case
        assert case["camera/z"] == 2
        assert "camera/pitch" in case
        assert case["camera/pitch"] == -1.57
        assert "camera/yaw" in case
        assert "sun/elevation" in case
        assert case["sun/elevation"] == 0.14
        assert "sun/azimuth" in case
        assert case["sun/azimuth"] == 0.0
