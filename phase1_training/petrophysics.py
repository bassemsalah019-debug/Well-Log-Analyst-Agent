"""Equinor's petrophysical equations (Volve field model), one small function each.

The equations know nothing about the agent: they take numbers and return numbers.
"""

import numpy as np
import pandas as pd

from las_io import load_input
from memory import memory_settings


# ── The equations ────────────────────────────────────────────────
def shale_volume(gr, grmin, grmax):
    """Linear GR index: 0 = clean sand, 1 = shale."""
    return ((gr - grmin) / (grmax - grmin)).clip(0, 1)


def porosity(rhob, nphi, rho_ma, rho_fl, a, b):
    """Density porosity, corrected with the neutron log: PHIF = PHID + A x (NPHI - PHID) + B."""
    phid = (rho_ma - rhob) / (rho_ma - rho_fl)
    return (phid + a * (nphi - phid) + b).clip(lower=0)


def permeability(phif, vsh, k0, k1, k2):
    """Equinor's regression on core data: KLOGH = 10^(k0 + k1 x PHIF + k2 x VSH), in mD."""
    return 10 ** (k0 + k1 * phif + k2 * vsh)


def rw_at_temperature(rw20, temp):
    """Arps: formation-water resistivity at the reservoir temperature (degrees C)."""
    return rw20 * (20 + 21.5) / (temp + 21.5)


def water_saturation(phif, rt, klogh, rw, a, n, m_coef, m_exp):
    """Archie, with the cementation exponent m taken from KLOGH (Equinor's model)."""
    m = m_coef * klogh ** m_exp
    phi = phif.where(phif > 0)
    sw = ((a * rw) / (phi ** m * rt)) ** (1 / n)
    return sw.clip(upper=1).where(phi.notna(), 1.0).where(rt.notna())


def net_sand(phif, vsh, phi_cut, vsh_cut):
    """1 where the rock passes both cutoffs, 0 where not, empty where data is missing."""
    net = ((phif > phi_cut) & (vsh < vsh_cut)).astype(float)
    net[phif.isna() | vsh.isna()] = np.nan
    return net


# ── Applying them to one well ────────────────────────────────────
def in_intervals(depth: pd.Index, intervals: list[tuple[float, float]]) -> np.ndarray:
    """True for every depth inside one of the Hugin intervals."""
    mask = np.zeros(len(depth), dtype=bool)
    for top, base in intervals:
        mask |= (depth >= top) & (depth <= base)
    return mask


def depth_step(index: pd.Index) -> float:
    """Distance between two depth samples, e.g. 0.1 m."""
    return float(np.median(np.diff(index))) if len(index) > 1 else 0.0


def evaluate_well(well: str) -> tuple[pd.DataFrame, dict, dict, list[str]]:
    """All equations on every Hugin depth of one well. Uses the raw logs and memory only."""
    settings = memory_settings()
    f, p = settings["field"], settings["wells"][well]
    raw, _, notes = load_input(well)
    df = raw.loc[in_intervals(raw.index, p["intervals"])].copy()

    rw = rw_at_temperature(f["rw20"], f["temp"])
    df["VSH"] = shale_volume(df["GR"], p["grmin"], p["grmax"])
    df["PHIF"] = porosity(df["RHOB"], df["NPHI"], f["rho_ma"], f["rho_fl"], p["A"], p["B"])
    df["KLOGH"] = permeability(df["PHIF"], df["VSH"], f["k0"], f["k1"], f["k2"])
    df["SW"] = water_saturation(df["PHIF"], df["RT"], df["KLOGH"], rw, f["a"], f["n"], f["m_coef"], f["m_exp"])
    df["NET"] = net_sand(df["PHIF"], df["VSH"], f["phi_cut"], f["vsh_cut"])

    return df, f, p, notes + [f"Rw at {f['temp']:.0f} C = {rw:.4f} ohmm"]


def summarize(df: pd.DataFrame) -> dict | None:
    """Hugin averages like Equinor's tables: N/G, and PHIF, SW and KLOGH in net sand."""
    valid = df.dropna(subset=["VSH", "PHIF"])
    if valid.empty:
        return None
    step = depth_step(df.index)
    net = valid[valid["NET"] == 1]
    sw_net = net.dropna(subset=["SW"])
    sw = (sw_net["SW"] * sw_net["PHIF"]).sum() / sw_net["PHIF"].sum() if len(sw_net) else float("nan")
    return {
        "gross_m": len(valid) * step,
        "net_m": len(net) * step,
        "ng": len(net) / len(valid),
        "phif_net": net["PHIF"].mean(),
        "sw_net": sw,                                   # pore-volume weighted
        "k_arith": net["KLOGH"].mean(),
        "k_geo": np.exp(np.log(net["KLOGH"]).mean()),
        "vsh_all": valid["VSH"].mean(),
        "phif_all": valid["PHIF"].mean(),
        "net_without_rt": len(net) - len(sw_net),
    }
