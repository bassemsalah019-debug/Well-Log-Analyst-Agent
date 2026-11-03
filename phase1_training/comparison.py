"""Compare this agent's curves with Equinor's interpretation, depth by depth."""

import numpy as np
import pandas as pd

from las_io import load_output
from petrophysics import evaluate_well


def match_depths(well: str) -> pd.DataFrame:
    """Put each of our depths next to the nearest Equinor depth (within 6 cm)."""
    ours, _, _, _ = evaluate_well(well)
    ref, _ = load_output(well)
    left = ours[["VSH", "PHIF", "SW", "KLOGH", "NET"]].reset_index(names="DEPTH").sort_values("DEPTH")
    right = ref.add_prefix("EQ_").reset_index(names="DEPTH").sort_values("DEPTH")
    return pd.merge_asof(left, right, on="DEPTH", direction="nearest", tolerance=0.06)


def curve_difference(both: pd.DataFrame, curve: str) -> dict | None:
    """Mean absolute difference, bias and correlation for one curve."""
    if f"EQ_{curve}" not in both:
        return None
    pair = both[[curve, f"EQ_{curve}"]].dropna()
    if pair.empty:
        return None
    diff = pair[curve] - pair[f"EQ_{curve}"]
    return {"n": len(pair), "mae": diff.abs().mean(), "bias": diff.mean(),
            "corr": pair[curve].corr(pair[f"EQ_{curve}"])}


def permeability_difference(both: pd.DataFrame) -> float | None:
    """Mean absolute difference of log10(KLOGH): permeability is compared as ratios."""
    if "EQ_KLOGH" not in both:
        return None
    pair = both[["KLOGH", "EQ_KLOGH"]].dropna()
    pair = pair[pair["EQ_KLOGH"] > 0]
    if pair.empty:
        return None
    return (np.log10(pair["KLOGH"]) - np.log10(pair["EQ_KLOGH"])).abs().mean()


def net_sand_agreement(both: pd.DataFrame) -> dict | None:
    """How often our net-sand decision equals Equinor's SAND_FLAG, and both N/G values."""
    if "EQ_SAND_FLAG" not in both:
        return None
    pair = both[["NET", "EQ_SAND_FLAG"]].dropna()
    if pair.empty:
        return None
    ours, theirs = pair["NET"] == 1, pair["EQ_SAND_FLAG"] == 1
    return {"agree": (ours == theirs).mean(), "ng_ours": ours.mean(), "ng_equinor": theirs.mean()}


def ng_breakdown(both: pd.DataFrame, phi_cut: float, vsh_cut: float) -> dict | None:
    """Split the N/G difference into: our curves vs Equinor's, and Equinor's hand edits of SAND_FLAG.

    ours - flag = (ours - Equinor's curves through the same cutoffs) + (Equinor's curves - flag)
    """
    needed = ["NET", "EQ_PHIF", "EQ_VSH", "EQ_SAND_FLAG"]
    if not set(needed) <= set(both):
        return None
    rows = both[needed].dropna()
    if rows.empty:
        return None
    ng_ours = (rows["NET"] == 1).mean()
    ng_curves = ((rows["EQ_PHIF"] > phi_cut) & (rows["EQ_VSH"] < vsh_cut)).mean()
    ng_flag = (rows["EQ_SAND_FLAG"] == 1).mean()
    return {"ng_curves": ng_curves, "total": ng_ours - ng_flag,
            "from_curves": ng_ours - ng_curves, "from_edits": ng_curves - ng_flag}
