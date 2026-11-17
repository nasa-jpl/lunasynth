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
"""Physical model of small lunar impact craters.

The model has four parts:

- **Fresh crater shapes** for four morphologies (normal, central mound, flat-bottomed and concentric),
  from Table 1 of Yang et al. (2021).
- **Degradation** of the shapes by topographic diffusion, with the size-dependent diffusivity of
  Zhang et al. (2026).
- **Morphology selection** from the regolith thickness (Quaide & Oberbeck, 1968).
- **Crater sizes and ages** from the Neukum et al. (2001) production and chronology functions.

Profiles use a normalized radial distance ``r = distance / radius`` (rim at ``r = 1``) and return the
elevation divided by the crater diameter, relative to the surface far from the crater.

References
----------
- Yang, X., Fa, W., Du, J., Xie, M., Liu, T. (2021). Effect of topographic degradation on small lunar
  craters: Implications for regolith thickness estimation. GRL 48, e2021GL095537.
  https://doi.org/10.1029/2021GL095537 (data: https://doi.org/10.5281/zenodo.5163880)
- Zhang, M., Fa, W., Tong, J., Liu, Y. (2026). Degradation rate and lifetime of small impact craters on the
  Moon. AGU Advances 7, e2026AV002542. https://doi.org/10.1029/2026AV002542
- Quaide, W. L., Oberbeck, V. R. (1968). Thickness determinations of the lunar surface layer from lunar
  impact craters. JGR 73(16), 5247-5270. https://doi.org/10.1029/JB073i016p05247
- Neukum, G., Ivanov, B. A., Hartmann, W. K. (2001). Cratering records in the inner solar system in relation
  to the lunar reference system. Space Sci. Rev. 96, 55-86. https://doi.org/10.1023/A:1011989004263
- Yue, Z. et al. (2022). Updated lunar cratering chronology model with the radiometric age of Chang'e-5
  samples. Nature Astronomy 6, 541-545. https://doi.org/10.1038/s41550-022-01604-3
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from numba import njit, prange

# -- Fresh crater shapes (Yang et al., 2021, Table 1) --------------------------------------------------------

NORMAL = 0
CENTRAL_MOUND = 1
FLAT_BOTTOMED = 2
CONCENTRIC = 3
MORPHOLOGIES = ("normal", "central_mound", "flat_bottomed", "concentric")


@dataclass(frozen=True)
class PowerLaw:
    """``coefficient * D**exponent`` with ``D`` the crater diameter in meters."""

    coefficient: float
    exponent: float

    def __call__(self, diameter):
        return self.coefficient * diameter**self.exponent


@dataclass(frozen=True)
class CommonShapeParams:
    """Terms shared by all morphologies (note of Yang et al., 2021, Table 1).

    The fits are valid for craters of 40 to 160 m. For smaller craters the diameter used in the power laws is
    clamped to ``min_diameter``, so small craters keep the shape of a 40 m crater (depth/diameter = 0.113).
    Table 1 gives elevations relative to the rim. As in the profiles published with the paper, the whole
    profile is shifted down by ``hr * ejecta_extent**alpha`` so the ejecta reach the surrounding surface at
    ``ejecta_extent`` crater radii.
    """

    depth: PowerLaw = PowerLaw(0.114, -0.002)  # d0, rim-to-floor depth / D
    rim_height: PowerLaw = PowerLaw(0.02513, -0.0757)  # hr, rim height above the surroundings / D
    ejecta_exponent: float = -3.1906  # alpha
    ejecta_extent: float = 2.5  # crater radii
    min_diameter: float = 40.0  # m, smallest diameter of the fits


@dataclass(frozen=True)
class NormalParams:
    """Bowl-shaped crater, observed for 40 < D < 100 m."""

    a: float = -2.8567
    b: float = 5.8270


@dataclass(frozen=True)
class CentralMoundParams:
    """Crater with a mound on its floor, observed for 40 < D < 150 m."""

    mound_radius: PowerLaw = PowerLaw(0.293, -0.086)  # r_m
    floor_radius: PowerLaw = PowerLaw(0.793, -0.242)  # r_b
    mound_height: PowerLaw = PowerLaw(0.23e-3, 0.64)  # h_m
    a: float = -2.6921
    b: float = 6.1678


@dataclass(frozen=True)
class FlatBottomedParams:
    """Crater with a flat floor, observed for 40 < D < 130 m."""

    floor_radius: PowerLaw = PowerLaw(0.091, 0.208)  # r_b
    a: float = -2.6003
    b: float = 5.8783


@dataclass(frozen=True)
class ConcentricParams:
    """Crater with a bench on its wall, observed for 40 < D < 160 m.

    The wall is computed with the published Table 1 expressions. They differ from the profile published in the
    paper's data set (Figure S9) by up to 3% of the crater depth near the rim; the other morphologies match it
    exactly.
    """

    c1: float = 0.1920
    c2: float = 0.0100
    bench_slope: PowerLaw = PowerLaw(0.0155, 0.343)  # C_3
    inner_radius: PowerLaw = PowerLaw(0.383, 0.053)  # r_i
    outer_radius: PowerLaw = PowerLaw(0.421, 0.102)  # r_o
    a: float = -1.6536
    b: float = 4.7626


COMMON = CommonShapeParams()
NORMAL_PARAMS = NormalParams()
CENTRAL_MOUND_PARAMS = CentralMoundParams()
FLAT_BOTTOMED_PARAMS = FlatBottomedParams()
CONCENTRIC_PARAMS = ConcentricParams()


@njit(cache=True)
def _wall(r0: float, a: float, b: float, amplitude: float) -> float:
    """Logistic crater wall, 0 at the rim (r0 = 1) and -amplitude at r0 = 0."""
    c = amplitude * (np.exp(a) + 1.0) / (np.exp(b) - 1.0)
    return c * (np.exp(b * r0) - np.exp(b)) / (1.0 + np.exp(a + b * r0))


@njit(cache=True)
def _outside(r: float, hr: float, alpha: float, extent: float) -> float:
    """Ejecta profile ``hr * r**alpha``, relative to the surface, which it reaches at ``extent`` radii."""
    if r >= extent:
        return 0.0
    return hr * (r**alpha - extent**alpha)


@njit(cache=True)
def _shift(hr: float, alpha: float, extent: float) -> float:
    """Elevation of the rim above the surface. Table 1 elevations are relative to the rim."""
    return hr * (1.0 - extent**alpha)


@njit(cache=True)
def normal_profile(r: float, d0: float, hr: float, alpha: float, extent: float, a: float, b: float) -> float:
    if r > 1.0:
        return _outside(r, hr, alpha, extent)
    return _wall(r, a, b, d0) + _shift(hr, alpha, extent)


@njit(cache=True)
def central_mound_profile(
    r: float,
    d0: float,
    hr: float,
    alpha: float,
    extent: float,
    mound_radius: float,
    floor_radius: float,
    mound_height: float,
    a: float,
    b: float,
) -> float:
    if r > 1.0:
        return _outside(r, hr, alpha, extent)
    if r <= mound_radius:
        h = (1.0 - r / mound_radius) * mound_height - d0
    elif r <= floor_radius:
        h = -d0
    else:
        h = _wall((r - floor_radius) / (1.0 - floor_radius), a, b, d0)
    return h + _shift(hr, alpha, extent)


@njit(cache=True)
def flat_bottomed_profile(
    r: float, d0: float, hr: float, alpha: float, extent: float, floor_radius: float, a: float, b: float
) -> float:
    if r > 1.0:
        return _outside(r, hr, alpha, extent)
    if r <= floor_radius:
        h = -d0
    else:
        h = _wall((r - floor_radius) / (1.0 - floor_radius), a, b, d0)
    return h + _shift(hr, alpha, extent)


@njit(cache=True)
def concentric_profile(
    r: float,
    d0: float,
    hr: float,
    alpha: float,
    extent: float,
    c1: float,
    c2: float,
    bench_slope: float,
    inner_radius: float,
    outer_radius: float,
    a: float,
    b: float,
) -> float:
    if r > 1.0:
        return _outside(r, hr, alpha, extent)
    h1 = c1 * inner_radius**2 + c2 * inner_radius - d0  # top of the inner bowl
    h2 = bench_slope * (outer_radius - inner_radius) + h1  # outer edge of the bench
    if r <= inner_radius:
        h = c1 * r**2 + c2 * r - d0
    elif r <= outer_radius:
        h = bench_slope * (r - inner_radius) + h1
    else:
        h = _wall((r - outer_radius) / (1.0 - outer_radius), a, b, -h2)
    return h + _shift(hr, alpha, extent)


def fresh_profile(r, diameter: float, morphology: str | int = "normal") -> np.ndarray:
    """Elevation / diameter of a fresh crater at normalized radial distances ``r`` (rim at r = 1).

    Args:
        r: Radial distances divided by the crater radius (scalar or array).
        diameter: Crater diameter in meters.
        morphology: One of :data:`MORPHOLOGIES` or its index.

    Returns:
        Elevation divided by the diameter, relative to the surface far from the crater.

    """
    m = morphology if isinstance(morphology, int | np.integer) else MORPHOLOGIES.index(morphology)
    D = max(float(diameter), COMMON.min_diameter)
    d0, hr = COMMON.depth(D), COMMON.rim_height(D)
    alpha, extent = COMMON.ejecta_exponent, COMMON.ejecta_extent
    r = np.atleast_1d(np.asarray(r, dtype=float))
    out = np.empty_like(r)
    for i, ri in enumerate(r):
        if m == NORMAL:
            p = NORMAL_PARAMS
            out[i] = normal_profile(ri, d0, hr, alpha, extent, p.a, p.b)
        elif m == CENTRAL_MOUND:
            p = CENTRAL_MOUND_PARAMS
            out[i] = central_mound_profile(
                ri, d0, hr, alpha, extent, p.mound_radius(D), p.floor_radius(D), p.mound_height(D), p.a, p.b
            )
        elif m == FLAT_BOTTOMED:
            p = FLAT_BOTTOMED_PARAMS
            out[i] = flat_bottomed_profile(ri, d0, hr, alpha, extent, p.floor_radius(D), p.a, p.b)
        elif m == CONCENTRIC:
            p = CONCENTRIC_PARAMS
            out[i] = concentric_profile(
                ri,
                d0,
                hr,
                alpha,
                extent,
                p.c1,
                p.c2,
                p.bench_slope(D),
                p.inner_radius(D),
                p.outer_radius(D),
                p.a,
                p.b,
            )
        else:
            msg = f"Unknown morphology {morphology}"
            raise ValueError(msg)
    return out


# -- Morphology from regolith thickness (Quaide & Oberbeck, 1968) ----------------------------------------------

# Diameter / regolith thickness ratios separating the morphologies. Central-mound and flat-bottomed craters form
# in the same range and are chosen with equal probability.
NORMAL_MAX_DIAMETER_TO_REGOLITH = 4.0
CONCENTRIC_MIN_DIAMETER_TO_REGOLITH = 9.0


def select_morphology(diameters: np.ndarray, regolith_thickness: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Morphology index of fresh craters from their diameter and the local regolith thickness (both in m)."""
    ratio = np.asarray(diameters) / np.asarray(regolith_thickness)
    morphology = np.full(ratio.shape, NORMAL, dtype=np.int64)
    middle = (ratio >= NORMAL_MAX_DIAMETER_TO_REGOLITH) & (ratio < CONCENTRIC_MIN_DIAMETER_TO_REGOLITH)
    morphology[middle] = np.where(rng.random(middle.sum()) < 0.5, CENTRAL_MOUND, FLAT_BOTTOMED)
    morphology[ratio >= CONCENTRIC_MIN_DIAMETER_TO_REGOLITH] = CONCENTRIC
    return morphology


# -- Degradation by topographic diffusion (Zhang et al., 2026) -------------------------------------------------


@dataclass(frozen=True)
class Diffusivity:
    """Size-dependent topographic diffusivity ``kappa(D) = kappa_800 * (D / 800 m)**phi`` in m^2/Myr.

    Zhang et al. (2026) fit ``kappa_800`` and ``phi`` to craters of 50 to 500 m. Below ``min_diameter`` the
    diffusivity follows ``small_crater_phi`` instead, the value expected when the largest eroding crater scales with
    the eroded crater (phi = 0.8-1, Fassett et al., 2018). Extrapolating the shallow fitted exponents (phi ~ 0.3 in the
    highlands) would make metre-scale craters last only ~0.1 Myr and flatten the size distribution to a cumulative
    slope of ~-1.4, shallower than the ~-2 observed for small lunar craters in equilibrium.
    """

    kappa_800: float
    phi: float
    min_diameter: float = 50.0  # m, smallest diameter of the fit
    small_crater_phi: float = 1.0

    def __call__(self, diameter):
        diameter = np.asarray(diameter, dtype=float)
        fitted = self.kappa_800 * (np.maximum(diameter, self.min_diameter) / 800.0) ** self.phi
        return np.where(
            diameter < self.min_diameter, fitted * (diameter / self.min_diameter) ** self.small_crater_phi, fitted
        )


# Best fits of Zhang et al. (2026), Table 2, for each terrain: the mean of kappa_800 and phi over the study regions
# (highlands: Apollo 14, Apollo 16, Luna 20; maria: Chang'E-5, Chang'E-6, Apollo 11, 12, 15, Luna 16, 24).
DIFFUSIVITY = {
    "highland": Diffusivity(kappa_800=(4.5 + 6.5 + 5.0) / 3, phi=(0.275 + 0.55 + 0.15) / 3),
    "mare": Diffusivity(
        kappa_800=(2.0 + 6.0 + 1.5 + 5.25 + 3.5 + 1.25 + 3.25) / 7,
        phi=(0.4 + 0.925 + 0.2 + 0.975 + 0.775 + 0.1 + 0.6) / 7,
    ),
}
# Typical regolith thickness in meters: Rajšić et al. (2026, PSJ) report medians of 4.0 m for the maria and 5.8 m
# for the highlands, increasing to 7-8 m towards the poles.
REGOLITH_THICKNESS = {"highland": 6.5, "mare": 4.0}

# Crater visibility threshold, depth / current diameter. Zhang et al. (2026) fit observations with
# 0.04 <= d/D <= 0.17; Yang et al. (2021) consider craters invisible below 0.02.
DEFAULT_VISIBILITY_DEPTH_RATIO = 0.04


@njit(cache=True)
def _diffuse(h: np.ndarray, dr: float, steps: np.ndarray) -> np.ndarray:
    """Axisymmetric linear diffusion with a finite-volume Crank-Nicolson scheme.

    Args:
        h: Initial profiles on cell centers ``(i + 0.5) * dr``, shape (n_cells, n_profiles), in units of D0.
        dr: Cell size in crater radii.
        steps: Increments of the normalized degradation state ``K / R0**2`` between the output profiles.

    Returns:
        Profiles after each increment, shape (len(steps), n_cells, n_profiles).

    """
    n = h.shape[0]
    rc = (np.arange(n) + 0.5) * dr
    w_lo = np.arange(n) * dr / (rc * dr * dr)
    w_hi = (np.arange(n) + 1.0) * dr / (rc * dr * dr)
    w_hi[-1] = 0.0  # zero flux far from the crater
    out = np.empty((steps.shape[0], n, h.shape[1]))
    current = h.copy()
    lower = np.empty(n)
    diag = np.empty(n)
    upper = np.empty(n)
    rhs = np.empty(n)
    c_prime = np.empty(n)
    for s in range(steps.shape[0]):
        sub_steps = 8
        dk = steps[s] / sub_steps
        for i in range(n):
            lower[i] = -0.5 * dk * w_lo[i]
            upper[i] = -0.5 * dk * w_hi[i]
            diag[i] = 1.0 + 0.5 * dk * (w_lo[i] + w_hi[i])
        for _ in range(sub_steps):
            for j in range(h.shape[1]):
                for i in range(n):
                    lap = -(w_lo[i] + w_hi[i]) * current[i, j]
                    if i > 0:
                        lap += w_lo[i] * current[i - 1, j]
                    if i < n - 1:
                        lap += w_hi[i] * current[i + 1, j]
                    rhs[i] = current[i, j] + 0.5 * dk * lap
                # Thomas algorithm for the tridiagonal system
                c_prime[0] = upper[0] / diag[0]
                rhs[0] = rhs[0] / diag[0]
                for i in range(1, n):
                    m = diag[i] - lower[i] * c_prime[i - 1]
                    c_prime[i] = upper[i] / m
                    rhs[i] = (rhs[i] - lower[i] * rhs[i - 1]) / m
                current[n - 1, j] = rhs[n - 1]
                for i in range(n - 2, -1, -1):
                    current[i, j] = rhs[i] - c_prime[i] * current[i + 1, j]
        out[s] = current
    return out


def diffuse_profiles(profiles: np.ndarray, dr: float, degradation_states: Sequence[float]) -> np.ndarray:
    """Degrade axisymmetric profiles by linear diffusion.

    Args:
        profiles: Elevations / D0 on cell centers ``(i + 0.5) * dr`` (radii), shape (n_cells,) or (n_cells, n).
        dr: Cell size in crater radii.
        degradation_states: Increasing normalized degradation states ``K / D0**2``.

    Returns:
        Profiles at each degradation state, shape (len(degradation_states), n_cells[, n]).

    """
    h = profiles[:, None] if profiles.ndim == 1 else profiles
    k_r = 4.0 * np.asarray(degradation_states, dtype=float)  # K / R0**2
    steps = np.diff(np.concatenate([[0.0], k_r]))
    out = _diffuse(np.ascontiguousarray(h, dtype=float), dr, steps)
    return out[..., 0] if profiles.ndim == 1 else out


@dataclass
class ProfileTable:
    """Crater profiles for each morphology, fresh diameter and degradation state.

    Profiles are stored in units of the fresh diameter D0 against the radial distance in fresh radii and the
    normalized degradation state ``K / D0**2``. Craters of the same morphology and D0 are self-similar in these
    units, so a small grid of D0 covers all craters.

    Attributes:
        diameters: Fresh diameters of the table, m.
        degradation_states: Normalized degradation states ``K / D0**2`` (first is 0, the fresh crater).
        radii: Radial distances of the samples, in fresh radii.
        elevation: Elevation / D0, shape (morphology, diameter, degradation state, radius).
        depth_ratio: Depth / current rim diameter, shape (morphology, diameter, degradation state).
        rim_radius: Current rim radius / fresh radius, shape (morphology, diameter, degradation state).
        morphology_current: Current morphology index, shape (morphology, diameter, degradation state).

    """

    diameters: np.ndarray
    degradation_states: np.ndarray
    radii: np.ndarray
    elevation: np.ndarray
    depth_ratio: np.ndarray
    rim_radius: np.ndarray
    morphology_current: np.ndarray = field(repr=False)


# Diameter / fresh diameter at which a degraded crater changes morphology (Yang et al., 2021, Figure S10 data,
# median over D0 = 40-180 m). Central-mound craters lose the mound first, then the flat floor.
MORPHOLOGY_TRANSITIONS = {
    CENTRAL_MOUND: ((1.025, FLAT_BOTTOMED), (1.188, NORMAL)),
    FLAT_BOTTOMED: ((1.179, NORMAL),),
    CONCENTRIC: ((1.129, NORMAL),),
    NORMAL: (),
}


def build_profile_table(
    diameters: Sequence[float] = (40.0, 55.0, 75.0, 100.0, 130.0, 160.0),
    max_degradation_state: float = 0.06,
    n_states: int = 121,
    dr: float = 0.005,
    extent: float = 5.0,
) -> ProfileTable:
    """Compute degraded crater profiles for all morphologies.

    The default ``max_degradation_state`` K/D0^2 = 0.06 reaches a depth / diameter of about 0.01, below the
    visibility of any crater.
    """
    diameters = np.asarray(diameters, dtype=float)
    n_cells = int(round(extent / dr))
    radii = (np.arange(n_cells) + 0.5) * dr
    # finer steps where the shape changes fastest, at low degradation
    states = max_degradation_state * np.linspace(0.0, 1.0, n_states) ** 2
    shape = (len(MORPHOLOGIES), len(diameters), n_states)
    elevation = np.empty((*shape, n_cells))
    for m in range(len(MORPHOLOGIES)):
        fresh = np.stack([fresh_profile(radii, d, m) for d in diameters], axis=1)
        elevation[m] = np.moveaxis(diffuse_profiles(fresh, dr, states), 2, 0)
    rim_radius = _crest_radius(elevation, radii)
    depth = elevation.max(axis=-1) - elevation.min(axis=-1)
    depth_ratio = depth / rim_radius  # (depth / D0) / (current diameter / D0)
    morphology_current = np.empty(shape, dtype=np.int64)
    for m in range(len(MORPHOLOGIES)):
        current = np.full(shape[1:], m, dtype=np.int64)
        for ratio, new_morphology in MORPHOLOGY_TRANSITIONS[m]:
            current[rim_radius[m] >= ratio] = new_morphology
        morphology_current[m] = current
    return ProfileTable(diameters, states, radii, elevation, depth_ratio, rim_radius, morphology_current)


def _crest_radius(elevation: np.ndarray, radii: np.ndarray) -> np.ndarray:
    """Radius of the rim crest, refined between samples with a parabola through the highest sample and its neighbors."""
    crest = np.clip(np.argmax(elevation, axis=-1), 1, len(radii) - 2)
    left = np.take_along_axis(elevation, crest[..., None] - 1, axis=-1)[..., 0]
    middle = np.take_along_axis(elevation, crest[..., None], axis=-1)[..., 0]
    right = np.take_along_axis(elevation, crest[..., None] + 1, axis=-1)[..., 0]
    curvature = left - 2 * middle + right
    offset = np.where(curvature < 0, 0.5 * (left - right) / np.where(curvature < 0, curvature, -1.0), 0.0)
    return radii[crest] + np.clip(offset, -0.5, 0.5) * (radii[1] - radii[0])


_TABLE: ProfileTable | None = None


def profile_table() -> ProfileTable:
    """Profile table with the default settings, computed on first use (about a second)."""
    global _TABLE
    if _TABLE is None:
        _TABLE = build_profile_table()
    return _TABLE


@dataclass
class DegradedCraters:
    """Lookup of the degraded state of a set of craters in a :class:`ProfileTable`."""

    morphology: np.ndarray  # fresh morphology index
    diameter_index: np.ndarray  # nearest table diameter
    state_index: np.ndarray  # lower degradation-state index
    state_weight: np.ndarray  # weight of the next state, for linear interpolation
    depth_ratio: np.ndarray  # depth / current diameter
    rim_radius: np.ndarray  # current rim radius / fresh radius
    morphology_current: np.ndarray


def lookup_degradation(
    table: ProfileTable, morphology: np.ndarray, diameters: np.ndarray, degradation_states: np.ndarray
) -> DegradedCraters:
    """Find the degraded profile of each crater. ``degradation_states`` are ``K / D0**2``."""
    log_d = np.log(table.diameters)
    diameter_index = np.abs(np.log(np.asarray(diameters))[:, None] - log_d[None, :]).argmin(axis=1)
    states = np.clip(degradation_states, 0.0, table.degradation_states[-1])
    upper = np.clip(
        np.searchsorted(table.degradation_states, states, side="right"), 1, len(table.degradation_states) - 1
    )
    lower = upper - 1
    span = table.degradation_states[upper] - table.degradation_states[lower]
    weight = (states - table.degradation_states[lower]) / span

    def interp(values):
        a = values[morphology, diameter_index, lower]
        b = values[morphology, diameter_index, upper]
        return a + weight * (b - a)

    morphology_current = np.where(
        weight < 0.5,
        table.morphology_current[morphology, diameter_index, lower],
        table.morphology_current[morphology, diameter_index, upper],
    )
    return DegradedCraters(
        morphology=np.asarray(morphology),
        diameter_index=diameter_index,
        state_index=lower,
        state_weight=weight,
        depth_ratio=interp(table.depth_ratio),
        rim_radius=interp(table.rim_radius),
        morphology_current=morphology_current,
    )


# -- Crater sizes and ages (Neukum et al., 2001) ----------------------------------------------------------------

# Coefficients of log10 N(>D) = sum a_i (log10 D)^i, N per km^2, D in km, for N(>1 km) at 1 Gyr. Values as in
# craterstats (https://github.com/ggmichael/craterstats, config/functions.txt), which uses a0 = -3.0768 instead of
# the published -3.0876, considered a typo.
NEUKUM_2001_PRODUCTION = (
    -3.0768,
    -3.557528,
    0.781027,
    1.021521,
    -0.156012,
    -0.444058,
    0.019977,
    0.086850,
    -0.005874,
    -0.006809,
    8.25e-04,
    5.54e-05,
)
PRODUCTION_MIN_DIAMETER = 10.0  # m, smallest diameter of the Neukum fit

# N(>1 km) per km^2 = p0 * (exp(p1 * T) - 1) + p3 * T, with T in Gyr
CHRONOLOGY = {
    "neukum2001": (5.44e-14, 6.93, 8.38e-4),
    "yue2022": (1.089e-13, 6.757, 7.660e-4),  # calibrated with the Chang'e-5 samples
}


@dataclass(frozen=True)
class ProductionModel:
    """Number and ages of craters formed on a surface.

    The production function of Neukum et al. (2001) is defined for craters larger than 10 m. Below 10 m it is
    extended as a power law with its slope at 10 m (cumulative slope of about -3.2).
    """

    chronology: str = "neukum2001"
    coefficients: tuple = NEUKUM_2001_PRODUCTION

    def n1(self, age_gyr):
        """Cumulative number of craters larger than 1 km per km^2 on a surface of the given age."""
        p0, p1, p3 = CHRONOLOGY[self.chronology]
        age_gyr = np.asarray(age_gyr, dtype=float)
        return p0 * (np.exp(p1 * age_gyr) - 1.0) + p3 * age_gyr

    def n1_rate(self, age_gyr):
        """Rate of formation of craters larger than 1 km, per km^2 per Gyr, ``age_gyr`` ago."""
        p0, p1, p3 = CHRONOLOGY[self.chronology]
        return p0 * p1 * np.exp(p1 * np.asarray(age_gyr, dtype=float)) + p3

    def _log_cumulative(self, diameter_m):
        x = np.log10(np.asarray(diameter_m, dtype=float) / 1000.0)
        return sum(c * x**i for i, c in enumerate(self.coefficients)) - self.coefficients[0]

    def cumulative_shape(self, diameter_m):
        """N(>D) / N(>1 km) for diameters in meters."""
        diameter_m = np.asarray(diameter_m, dtype=float)
        d_min = PRODUCTION_MIN_DIAMETER
        h = 1e-4
        slope = (self._log_cumulative(d_min * 10**h) - self._log_cumulative(d_min * 10**-h)) / (2 * h)
        below = self._log_cumulative(d_min) + slope * np.log10(np.minimum(diameter_m, d_min) / d_min)
        return 10 ** np.where(diameter_m < d_min, below, self._log_cumulative(np.maximum(diameter_m, d_min)))

    def cumulative(self, diameter_m, age_gyr):
        """Cumulative number of craters larger than ``diameter_m`` per km^2 formed in ``age_gyr``."""
        return self.cumulative_shape(diameter_m) * self.n1(age_gyr)

    def sample_diameters(
        self, area_m2: float, d_min: float, d_max: float, age_gyr: float, rng: np.random.Generator
    ) -> np.ndarray:
        """Diameters (m) of all craters between ``d_min`` and ``d_max`` formed on ``area_m2`` in ``age_gyr``."""
        expected = (self.cumulative(d_min, age_gyr) - self.cumulative(d_max, age_gyr)) * area_m2 / 1e6
        n = rng.poisson(expected)
        grid = np.logspace(np.log10(d_min), np.log10(d_max), 2000)
        cdf = 1.0 - (self.cumulative_shape(grid) - self.cumulative_shape(d_max)) / (
            self.cumulative_shape(d_min) - self.cumulative_shape(d_max)
        )
        return np.exp(np.interp(rng.random(n), cdf, np.log(grid)))

    def sample_ages(self, n: int, max_age_gyr, rng: np.random.Generator) -> np.ndarray:
        """Ages (Gyr) of ``n`` craters formed at the rate of the chronology function, younger than ``max_age_gyr``.

        ``max_age_gyr`` can be an array with the oldest age of each crater.
        """
        max_age_gyr = np.broadcast_to(np.asarray(max_age_gyr, dtype=float), (n,))
        return self.invert_n1(rng.random(n) * self.n1(max_age_gyr))

    def invert_n1(self, n1_values):
        """Age (Gyr) at which the chronology function reaches ``n1_values``."""
        n1_values = np.asarray(n1_values, dtype=float)
        lo = np.zeros_like(n1_values)
        hi = np.full_like(n1_values, 4.6)
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            below = self.n1(mid) < n1_values
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        return 0.5 * (lo + hi)


# geometric saturation, N(>D) = 1.54 D^-2 with D in km (Gault, 1970; Melosh, 1989)
def geometric_saturation(diameter_m):
    """Cumulative number of craters per km^2 that would cover the surface completely."""
    return 1.54 * (np.asarray(diameter_m, dtype=float) / 1000.0) ** -2


# -- Crater population ---------------------------------------------------------------------------------------


@dataclass
class CraterPopulation:
    """Visible craters of a surface, with their fresh and current state."""

    x: np.ndarray
    y: np.ndarray
    diameter_initial: np.ndarray  # D0, m
    diameter: np.ndarray  # current rim diameter, m
    age_myr: np.ndarray
    degradation_state: np.ndarray  # K, m^2
    morphology_initial: np.ndarray  # index in MORPHOLOGIES
    morphology: np.ndarray  # current morphology index
    depth: np.ndarray  # current rim-to-floor depth, m
    rim_height: np.ndarray  # current rim height above the far field, m

    def __len__(self) -> int:
        return len(self.x)


def _lifetime_myr(diameters, diffusivity: Diffusivity, visibility_depth_ratio: float, table: ProfileTable):
    """Upper bound of the age (Myr) at which craters become invisible, to skip craters before computing their shape."""
    still_visible = table.depth_ratio >= visibility_depth_ratio
    # last visible degradation state of the longest-lived morphology and diameter of the table
    last = np.max(np.where(still_visible, np.arange(len(table.degradation_states)), 0))
    k_invisible = table.degradation_states[min(last + 1, len(table.degradation_states) - 1)]
    return k_invisible * np.asarray(diameters) ** 2 / diffusivity(diameters)


def generate_population(
    size_x: float,
    size_y: float,
    surface_age_gyr: float,
    terrain: str = "highland",
    d_min: float = 2.0,
    d_max: float = 50.0,
    morphology: str = "auto",
    regolith_thickness: float | None = None,
    regolith_scatter: float = 0.3,
    visibility_depth_ratio: float = DEFAULT_VISIBILITY_DEPTH_RATIO,
    chronology: str = "neukum2001",
    diffusivity: Diffusivity | None = None,
    x_init: float = 0.0,
    y_init: float = 0.0,
    rng: np.random.Generator | None = None,
    table: ProfileTable | None = None,
) -> CraterPopulation:
    """Generate the visible craters of a surface.

    Craters are formed with the production function of Neukum et al. (2001) over the age of the surface, then
    degraded by topographic diffusion. Only craters still deeper than ``visibility_depth_ratio`` are returned.

    Args:
        size_x: Width of the area in meters.
        size_y: Height of the area in meters.
        surface_age_gyr: Age of the surface in Gyr, the oldest a crater can be.
        terrain: "highland" or "mare", selects the diffusivity and regolith thickness.
        d_min: Smallest fresh crater diameter in meters.
        d_max: Largest fresh crater diameter in meters.
        morphology: "auto" to select it from the regolith thickness, or one of :data:`MORPHOLOGIES`.
        regolith_thickness: Median regolith thickness in meters. Defaults to the typical value of the terrain.
        regolith_scatter: Standard deviation of the log of the regolith thickness at each crater.
        visibility_depth_ratio: Craters shallower than this depth / diameter are not visible.
        chronology: Chronology function, "neukum2001" or "yue2022".
        diffusivity: Diffusivity model. Defaults to the values of the terrain from Zhang et al. (2026).
        x_init: Smallest x coordinate of the area.
        y_init: Smallest y coordinate of the area.
        rng: Random number generator.
        table: Profile table, defaults to :func:`profile_table`.

    """
    rng = np.random.default_rng() if rng is None else rng
    table = profile_table() if table is None else table
    if terrain not in DIFFUSIVITY:
        msg = f"Unknown terrain {terrain!r}, expected one of {sorted(DIFFUSIVITY)}"
        raise ValueError(msg)
    diffusivity = DIFFUSIVITY[terrain] if diffusivity is None else diffusivity
    regolith_thickness = REGOLITH_THICKNESS[terrain] if regolith_thickness is None else regolith_thickness
    production = ProductionModel(chronology)

    # sample only craters young enough to still be visible
    lifetime_gyr = _lifetime_myr(np.array([d_min, d_max]), diffusivity, visibility_depth_ratio, table) / 1000.0
    max_age = min(surface_age_gyr, max(lifetime_gyr))
    diameters = production.sample_diameters(size_x * size_y, d_min, d_max, max_age, rng)
    max_age_each = np.minimum(
        surface_age_gyr, _lifetime_myr(diameters, diffusivity, visibility_depth_ratio, table) / 1000.0
    )
    # thin the craters: a crater of diameter D can only be visible if it is younger than its lifetime
    keep = rng.random(len(diameters)) < production.n1(max_age_each) / production.n1(max_age)
    diameters, max_age_each = diameters[keep], max_age_each[keep]
    ages_myr = production.sample_ages(len(diameters), max_age_each, rng) * 1000.0

    if morphology == "auto":
        thickness = regolith_thickness * np.exp(regolith_scatter * rng.standard_normal(len(diameters)))
        morphology_initial = select_morphology(diameters, thickness, rng)
    else:
        morphology_initial = np.full(len(diameters), MORPHOLOGIES.index(morphology), dtype=np.int64)

    degradation_state = diffusivity(diameters) * ages_myr
    degraded = lookup_degradation(table, morphology_initial, diameters, degradation_state / diameters**2)
    visible = degraded.depth_ratio >= visibility_depth_ratio
    diameters, ages_myr, degradation_state = diameters[visible], ages_myr[visible], degradation_state[visible]
    morphology_initial = morphology_initial[visible]
    degraded = lookup_degradation(table, morphology_initial, diameters, degradation_state / diameters**2)

    n = len(diameters)
    rim_offset = _rim_offsets(table, degraded)
    current_diameter = diameters * degraded.rim_radius
    return CraterPopulation(
        x=rng.random(n) * size_x + x_init,
        y=rng.random(n) * size_y + y_init,
        diameter_initial=diameters,
        diameter=current_diameter,
        age_myr=ages_myr,
        degradation_state=degradation_state,
        morphology_initial=morphology_initial,
        morphology=degraded.morphology_current,
        depth=degraded.depth_ratio * current_diameter,
        rim_height=rim_offset * diameters,
    )


def _rim_offsets(table: ProfileTable, degraded: DegradedCraters) -> np.ndarray:
    """Current rim height above the far field / D0."""
    rim = table.elevation.max(axis=-1)
    a = rim[degraded.morphology, degraded.diameter_index, degraded.state_index]
    b = rim[degraded.morphology, degraded.diameter_index, degraded.state_index + 1]
    return a + degraded.state_weight * (b - a)


# -- Adding craters to a DEM ---------------------------------------------------------------------------------


@njit(parallel=True, cache=True)
def _stamp_craters(
    dem: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    radius_px: np.ndarray,
    diameter_m: np.ndarray,
    profiles: np.ndarray,
    profile_dr: float,
    order: np.ndarray,
    row_start: np.ndarray,
) -> None:
    """Add crater profiles to ``dem`` in place.

    Rows are processed in parallel; each thread only writes its own row, so overlapping craters add up exactly.

    Args:
        dem: Elevations, modified in place.
        rows: Crater center rows (pixels).
        cols: Crater center columns (pixels).
        radius_px: Fresh crater radius in pixels.
        diameter_m: Fresh crater diameter in meters (profiles are in units of it).
        profiles: Elevation / D0 of each crater at radii ``(i + 0.5) * profile_dr`` fresh radii.
        profile_dr: Sample spacing of the profiles in fresh radii.
        order: Crater indices sorted by first affected row.
        row_start: For each DEM row, the start in ``order`` of the craters whose first row is not after it.

    """
    n_rows, n_cols = dem.shape
    n_samples = profiles.shape[1]
    extent = n_samples * profile_dr
    for i in prange(n_rows):
        for k in range(row_start[i + 1]):
            c = order[k]
            reach = radius_px[c] * extent
            if abs(i - rows[c]) > reach:
                continue
            j_min = max(int(cols[c] - reach), 0)
            j_max = min(int(cols[c] + reach) + 1, n_cols)
            for j in range(j_min, j_max):
                r = np.sqrt((i - rows[c]) ** 2 + (j - cols[c]) ** 2) / radius_px[c]
                s = r / profile_dr - 0.5
                if s >= n_samples - 1:
                    continue
                if s <= 0.0:
                    h = profiles[c, 0]
                else:
                    s0 = int(s)
                    w = s - s0
                    h = profiles[c, s0] * (1.0 - w) + profiles[c, s0 + 1] * w
                dem[i, j] += h * diameter_m[c]


def crater_profiles(table: ProfileTable, morphology: np.ndarray, diameters: np.ndarray, degradation_states):
    """Profiles (elevation / D0 against fresh radii) of each crater, interpolated in degradation state."""
    degraded = lookup_degradation(table, morphology, diameters, np.asarray(degradation_states) / diameters**2)
    a = table.elevation[degraded.morphology, degraded.diameter_index, degraded.state_index]
    b = table.elevation[degraded.morphology, degraded.diameter_index, degraded.state_index + 1]
    return a + degraded.state_weight[:, None] * (b - a)


def add_craters_to_dem(
    dem: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    diameters: np.ndarray,
    morphology: np.ndarray,
    degradation_states: np.ndarray,
    pixel_size: float,
    table: ProfileTable | None = None,
) -> np.ndarray:
    """Add craters to a DEM in place and return it.

    Args:
        dem: Elevations in meters, rows x columns.
        rows: Crater center rows (pixels, can be fractional).
        cols: Crater center columns (pixels, can be fractional).
        diameters: Fresh crater diameters in meters.
        morphology: Fresh morphology index of each crater.
        degradation_states: Degradation state K of each crater, m^2.
        pixel_size: DEM pixel size in meters.
        table: Profile table, defaults to :func:`profile_table`.

    """
    if len(diameters) == 0:
        return dem
    table = profile_table() if table is None else table
    diameters = np.asarray(diameters, dtype=float)
    profiles = np.ascontiguousarray(crater_profiles(table, np.asarray(morphology), diameters, degradation_states))
    profile_dr = float(table.radii[1] - table.radii[0])
    radius_px = diameters / 2.0 / pixel_size
    rows = np.asarray(rows, dtype=float)
    cols = np.asarray(cols, dtype=float)
    reach = radius_px * profiles.shape[1] * profile_dr
    first_row = np.clip(np.floor(rows - reach), 0, dem.shape[0]).astype(np.int64)
    order = np.argsort(first_row, kind="stable")
    row_start = np.searchsorted(first_row[order], np.arange(dem.shape[0] + 1), side="right")
    dem_float = dem if dem.dtype == np.float64 else dem.astype(np.float64)
    _stamp_craters(dem_float, rows, cols, radius_px, diameters, profiles, profile_dr, order, row_start)
    if dem_float is not dem:
        dem[...] = dem_float
    return dem
