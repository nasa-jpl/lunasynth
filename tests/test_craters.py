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
from lunasynth import craters
from scipy.integrate import trapezoid
from scipy.special import i0e


def exact_diffusion(h0: np.ndarray, r: np.ndarray, k_r: float) -> np.ndarray:
    """Exact solution of axisymmetric linear diffusion, with ``k_r = K / R0**2``."""
    R, Rp = np.meshgrid(r, r, indexing="ij")
    kernel = np.exp(-((R - Rp) ** 2) / (4 * k_r)) * i0e(R * Rp / (2 * k_r)) * Rp / (2 * k_r)
    return trapezoid(kernel * h0[None, :], r, axis=1)


@pytest.mark.parametrize("morphology", craters.MORPHOLOGIES)
def test_fresh_profile_shape(morphology):
    r = np.linspace(0, 3, 3001)
    h = craters.fresh_profile(r, 80.0, morphology)
    assert np.all(np.isfinite(h))
    # rim at one radius, depth/diameter of fresh small mare craters (Yang et al., 2021)
    assert r[np.argmax(h)] == pytest.approx(1.0, abs=1e-3)
    assert h.max() - h.min() == pytest.approx(0.113, abs=0.002)
    # ejecta reach the surrounding surface at 2.5 radii
    assert np.all(h[r >= 2.5] == 0.0)
    # continuous profile
    assert np.max(np.abs(np.diff(h))) < 2e-3


def test_fresh_profiles_match_published_values():
    # Yang et al. (2021), Table 1, for D = 50 m: d0 = 0.114 D^-0.002, hr = 0.02513 D^-0.0757, alpha = -3.1906
    D = 50.0
    d0, hr, alpha = 0.114 * D**-0.002, 0.02513 * D**-0.0757, -3.1906
    shift = hr * (1 - 2.5**alpha)
    # floor of the normal, central-mound and flat-bottomed craters
    assert craters.fresh_profile(0.0, D, "normal")[0] == pytest.approx(-d0 + shift, abs=1e-3)
    assert craters.fresh_profile(0.0, D, "flat_bottomed")[0] == pytest.approx(-d0 + shift, rel=1e-9)
    rm, hm = 0.293 * D**-0.086, 0.23e-3 * D**0.64
    assert craters.fresh_profile(0.0, D, "central_mound")[0] == pytest.approx(hm - d0 + shift, rel=1e-9)
    rb = 0.793 * D**-0.242
    assert craters.fresh_profile((rm + rb) / 2, D, "central_mound")[0] == pytest.approx(-d0 + shift, rel=1e-9)
    # concentric inner bowl C1 r^2 + C2 r - d0
    assert craters.fresh_profile(0.2, D, "concentric")[0] == pytest.approx(0.192 * 0.04 + 0.01 * 0.2 - d0 + shift)
    # ejecta hr * r^alpha
    assert craters.fresh_profile(1.5, D, "normal")[0] == pytest.approx(hr * (1.5**alpha - 2.5**alpha))


def test_small_craters_keep_the_40m_shape():
    r = np.linspace(0, 2.5, 101)
    assert np.allclose(craters.fresh_profile(r, 5.0), craters.fresh_profile(r, 40.0))


def test_diffusion_matches_exact_solution_and_conserves_volume():
    dr = 0.005
    r = (np.arange(1000) + 0.5) * dr
    h0 = craters.fresh_profile(r, 60.0)
    states = [0.002, 0.01, 0.03]  # K / D0^2
    h = craters.diffuse_profiles(h0, dr, states)
    for i, state in enumerate(states):
        exact = exact_diffusion(h0, r, 4 * state)
        assert np.max(np.abs(h[i] - exact)) < 2e-4
        assert trapezoid((h[i] - h0) * r, r) == pytest.approx(0.0, abs=1e-6)


def test_normal_crater_becomes_invisible_as_in_yang_2021():
    # Yang et al. (2021), Figure 2 data: a 100 m normal crater becomes invisible (d/D = 0.02) at kappa*t = 328 m^2,
    # when it has widened to ~1.5 times its initial diameter
    table = craters.profile_table()
    i = list(table.diameters).index(100.0)
    depth_ratio = table.depth_ratio[craters.NORMAL, i]
    state = np.interp(-0.02, -depth_ratio, table.degradation_states)
    assert state * 100.0**2 == pytest.approx(328.0, rel=0.02)
    widening = np.interp(state, table.degradation_states, table.rim_radius[craters.NORMAL, i])
    assert widening == pytest.approx(1.49, abs=0.03)


def test_degraded_craters_change_morphology():
    table = craters.profile_table()
    last = table.morphology_current[:, :, -1]
    assert np.all(last == craters.NORMAL)
    assert np.all(table.morphology_current[:, :, 0] == np.arange(4)[:, None])


def test_production_function():
    production = craters.ProductionModel()
    # N(>1 km) is the chronology function
    assert production.cumulative(1000.0, 1.0) == pytest.approx(8.38e-4, rel=1e-3)
    assert production.cumulative(1000.0, 3.9) == pytest.approx(production.n1(3.9))
    # cumulative slope of small craters
    slope = np.log10(production.cumulative(100.0, 1.0) / production.cumulative(10.0, 1.0))
    assert slope == pytest.approx(-3.1, abs=0.1)
    # power-law extension below 10 m, continuous at 10 m
    assert production.cumulative(9.999, 1.0) == pytest.approx(production.cumulative(10.0, 1.0), rel=1e-3)


def test_sampled_ages_follow_the_chronology():
    production = craters.ProductionModel()
    ages = production.sample_ages(100_000, 3.9, np.random.default_rng(0))
    assert np.all((ages >= 0) & (ages <= 3.9))
    assert np.mean(ages < 1.0) == pytest.approx(production.n1(1.0) / production.n1(3.9), abs=0.003)


def test_population_is_reproducible_and_visible():
    kwargs = {"size_x": 400.0, "size_y": 300.0, "surface_age_gyr": 3.9, "d_min": 2.0, "d_max": 40.0}
    a = craters.generate_population(rng=np.random.default_rng(3), **kwargs)
    b = craters.generate_population(rng=np.random.default_rng(3), **kwargs)
    assert len(a) > 0
    assert np.array_equal(a.x, b.x) and np.array_equal(a.diameter, b.diameter)
    assert np.all((a.x >= 0) & (a.x <= 400) & (a.y >= 0) & (a.y <= 300))
    assert np.all(a.depth / a.diameter >= craters.DEFAULT_VISIBILITY_DEPTH_RATIO - 1e-6)
    # the sharp rim first rounds off slightly inward, then craters widen
    assert np.all(a.diameter >= 0.99 * a.diameter_initial)
    assert np.all(a.age_myr >= 0)


@pytest.mark.parametrize(("terrain", "low", "high"), [("highland", 0.05, 1.0), ("mare", 0.1, 3.0)])
def test_visible_crater_density_is_realistic(terrain, low, high):
    # Zhang et al. (2026): small craters on old surfaces are at 0.5-5% of geometric saturation (lower in the
    # highlands); with d/D > 0.04 the model gives a fraction of that
    population = craters.generate_population(
        1000.0, 1000.0, 3.9, terrain=terrain, d_min=2.0, d_max=50.0, rng=np.random.default_rng(1)
    )
    n = np.sum(population.diameter_initial > 5.0)
    percent = 100 * n / craters.geometric_saturation(5.0)
    assert low < percent < high


def test_morphology_follows_regolith_thickness():
    rng = np.random.default_rng(0)
    diameters = np.array([10.0, 30.0, 30.0, 30.0, 100.0])
    morphology = craters.select_morphology(diameters, np.full(5, 5.0), rng)
    assert morphology[0] == craters.NORMAL  # D/T = 2
    assert set(morphology[1:4]) <= {craters.CENTRAL_MOUND, craters.FLAT_BOTTOMED}  # D/T = 6
    assert morphology[4] == craters.CONCENTRIC  # D/T = 20


def test_stamping_overlapping_craters_is_exact():
    rng = np.random.default_rng(0)
    n = 500
    rows, cols = rng.uniform(0, 120, n), rng.uniform(0, 120, n)
    diameters = rng.uniform(4.0, 40.0, n)
    morphology = rng.integers(0, 4, n)
    states = rng.uniform(0.0, 0.02, n) * diameters**2

    results = [
        craters.add_craters_to_dem(np.zeros((120, 120)), rows, cols, diameters, morphology, states, 1.0)
        for _ in range(3)
    ]
    assert all(np.array_equal(results[0], result) for result in results[1:])

    # serial reference
    table = craters.profile_table()
    profiles = craters.crater_profiles(table, morphology, diameters, states)
    dr = table.radii[1] - table.radii[0]
    ii, jj = np.mgrid[0:120, 0:120]
    expected = np.zeros((120, 120))
    for c in range(n):
        s = np.hypot(ii - rows[c], jj - cols[c]) / (diameters[c] / 2) / dr - 0.5
        inside = s < profiles.shape[1] - 1
        expected[inside] += np.interp(s[inside], np.arange(profiles.shape[1]), profiles[c]) * diameters[c]
    assert np.allclose(results[0], expected, atol=1e-9)
