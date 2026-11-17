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
from lunasynth.terrain_enhancement import Crater, CraterField, RockField, crater_field_arguments


@pytest.mark.parametrize("pixel_size", [1.0, 0.5, 0.25])
def test_place_craters_dem_meters(pixel_size):
    # non-square DEM: 40 m tall (rows, y) by 60 m wide (columns, x)
    dem = np.zeros((int(40 / pixel_size), int(60 / pixel_size)))
    dem = CraterField().place_craters_dem([Crater(x=30.1, y=10.1, diameter=8.0)], dem, pixel_size)

    row, col = np.unravel_index(np.argmin(dem), dem.shape)
    assert row * pixel_size == pytest.approx(10.0, abs=pixel_size)
    assert col * pixel_size == pytest.approx(30.0, abs=pixel_size)
    # depth in meters of a fresh normal 8 m crater (Yang et al., 2021), independent of the DEM resolution;
    # the nearest pixel is ~0.14 m from the center
    assert dem.min() == pytest.approx(-0.75, abs=0.01)
    # rim at one radius from the center
    rim_row, rim_col = np.unravel_index(np.argmax(dem), dem.shape)
    assert np.hypot(rim_row * pixel_size - 10.1, rim_col * pixel_size - 30.1) == pytest.approx(4.0, abs=pixel_size)


def test_place_craters_dem_north_up():
    # row 0 at y = y_max, column 0 at x = x_min, as loaded by blender_helper.load_mesh_from_array
    dem = np.zeros((101, 101))
    crater = Crater(x=-20.0, y=30.0, diameter=12.0)
    CraterField().place_craters_dem([crater], dem, 1.0, x_min=-50.0, y_max=50.0)
    row, col = np.unravel_index(np.argmin(dem), dem.shape)
    assert (-50.0 + col, 50.0 - row) == (-20.0, 30.0)


@pytest.mark.parametrize("shape", [(80, 80), (80, 40), (40, 80)])
def test_crater_field_covers_dem(shape):
    pixel_size = 0.5
    crater_field = CraterField()
    # slowly degrading terrain, so the small area has enough visible craters
    crater_field.generate(
        size_y=shape[0] * pixel_size,
        size_x=shape[1] * pixel_size,
        surface_age_ga=3.9,
        d_min=1.0,
        d_max=10.0,
        kappa_800=0.5,
        phi=1.0,
        seed=0,
    )
    assert len(crater_field.craters) > 0
    dem = crater_field.place_craters_dem(crater_field.craters, np.zeros(shape), pixel_size)

    # craters reach every quadrant of the DEM
    rows, cols = shape
    for quadrant in (
        dem[: rows // 2, : cols // 2],
        dem[: rows // 2, cols // 2 :],
        dem[rows // 2 :, : cols // 2],
        dem[rows // 2 :, cols // 2 :],
    ):
        assert np.mean(np.abs(quadrant) > 1e-3) > 0.05


def test_crater_field_csv_round_trip(tmp_path):
    crater_field = CraterField()
    crater_field.generate(size_x=200.0, size_y=200.0, surface_age_ga=3.9, terrain="mare", d_min=2.0, seed=1)
    filename = tmp_path / "crater_field.csv"
    crater_field.save(str(filename))

    loaded = CraterField()
    loaded.from_csv(str(filename))
    assert loaded.craters == crater_field.craters


def test_crater_field_reads_old_csv(tmp_path):
    filename = tmp_path / "old_crater_field.csv"
    filename.write_text("x,y,diameter\n1.0,2.0,8.0\n")
    crater_field = CraterField()
    crater_field.from_csv(str(filename))
    crater = crater_field.craters[0]
    assert (crater.x, crater.y, crater.diameter_initial) == (1.0, 2.0, 8.0)
    assert (crater.morphology, crater.age_myr) == ("normal", 0)


def test_crater_field_arguments():
    config = {"surface_age_ga": {"type": "fixed", "value": 3.5}, "terrain": "mare", "d_min": 1.0}
    arguments = crater_field_arguments(config, base_pixel_size=5.0)
    assert arguments["surface_age_ga"] == 3.5
    assert arguments["terrain"] == "mare"
    # craters the 5 m base DEM resolves are not added again
    assert arguments["d_max"] == 50.0
    assert crater_field_arguments({**config, "d_max": 20.0}, base_pixel_size=5.0)["d_max"] == 20.0
    with pytest.raises(ValueError, match="surface_age_ga"):
        crater_field_arguments({"density": 1.0}, base_pixel_size=5.0)


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
