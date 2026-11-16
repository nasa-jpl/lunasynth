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


import numpy as np
import pytest
from lunasynth.terrain_enhancement import Crater, CraterField, RockField


@pytest.mark.parametrize("pixel_size", [1.0, 0.5, 0.25])
def test_place_craters_dem_meters(pixel_size):
    # non-square DEM: 40 m tall (rows, y) by 60 m wide (columns, x)
    dem = np.zeros((int(40 / pixel_size), int(60 / pixel_size)))
    # center off the pixel grid: the depth profile is undefined at exactly r=0
    dem = CraterField().place_craters_dem([Crater(x=30.1, y=10.1, diameter=8.0)], dem, pixel_size)

    row, col = np.unravel_index(np.argmin(dem), dem.shape)
    assert row * pixel_size == pytest.approx(10.0, abs=pixel_size)
    assert col * pixel_size == pytest.approx(30.0, abs=pixel_size)
    # crater depth in meters does not depend on the DEM resolution
    assert dem.min() == pytest.approx(-0.635, abs=0.01)


@pytest.mark.parametrize("shape", [(80, 80), (80, 40), (40, 80)])
def test_crater_field_covers_dem(shape):
    pixel_size = 0.5
    np.random.seed(0)
    crater_field = CraterField()
    crater_field.generate(
        k=1.0,
        size_y=shape[0] * pixel_size,
        size_x=shape[1] * pixel_size,
        h_min=2.0,
        h_max=20.0,
    )
    dem = crater_field.place_craters_dem(crater_field.craters, np.zeros(shape), pixel_size)

    # craters reach every quadrant of the DEM
    rows, cols = shape
    for quadrant in (
        dem[: rows // 2, : cols // 2],
        dem[: rows // 2, cols // 2 :],
        dem[rows // 2 :, : cols // 2],
        dem[rows // 2 :, cols // 2 :],
    ):
        assert np.mean(np.abs(quadrant) > 1e-3) > 0.5


def test_generate_rock_field():
    # render it
    rock_field = RockField()
    rock_field.generate_rock_field(
        k=0.06,
        size_x=10,
        size_y=10,
        h_min=0.4,
        h_max=6.0,
    )

    # check rock field
    assert rock_field.rocks is not None
    for rock in rock_field.rocks:
        assert rock.x >= 0
        assert rock.x < 10
        assert rock.y >= 0
        assert rock.y < 10
        assert rock.diameter >= 0.39
        assert rock.diameter <= 6.01
