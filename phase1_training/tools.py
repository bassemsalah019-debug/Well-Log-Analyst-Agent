"""The four tools the model can call. Each one calls the domain code and returns short text."""

from langchain_core.tools import tool

from comparison import (curve_difference, match_depths, permeability_difference, net_sand_agreement,
                        ng_breakdown)
from config import INPUT_CURVES
from las_io import available_wells, find_well, load_input
from memory import memory_settings
from petrophysics import depth_step, evaluate_well, summarize


def no_such_well(name: str) -> str:
    return f"No data for '{name}'. Available wells: {', '.join(available_wells())}"


def format_intervals(intervals: list[tuple[float, float]]) -> str:
    return "; ".join(f"{top:.1f}-{base:.1f}" for top, base in intervals)


def known_causes(p: dict) -> dict:
    """What each result depends on, so the cause of a difference is stated by code, not guessed."""
    if p["A"] == 0 and p["B"] == 0:
        phif_note = "With A = 0 and B = 0 the match should be exact."
    else:
        phif_note = ("Equinor's PHIF is reproduced exactly only in wells with A = 0 and B = 0, so in wells with a "
                     "neutron correction Equinor likely applied a step that is not described in its report.")
    return {
        "VSH": "uses only GR, with the same equation and GRmin/GRmax as Equinor's report.",
        "PHIF": (f"uses only RHOB and NPHI (not RT). This agent applies the SAME equation as Equinor's report, "
                 f"including the neutron correction with A = {p['A']:g} and B = {p['B']:g}. " + phif_note),
        "SW": ("uses PHIF and RT, so it follows the PHIF difference (higher PHIF gives lower SW) and "
               "Equinor's hand-edited RT (RT_EDIT), which is not in the files."),
        "KLOGH": "uses PHIF and VSH, so it follows the PHIF difference.",
        "NET": ("depends on PHIF > cutoff and VSH < cutoff, so a small PHIF difference near the cutoff changes N/G; "
                "the N/G breakdown line shows how much comes from the curves and how much from Equinor's hand edits."),
    }


@tool
def list_wells() -> str:
    """List the Volve wells that have raw logs and Equinor's interpretation."""
    return "Available wells: " + ", ".join(available_wells())


@tool
def describe_well(well_name: str) -> str:
    """Show which raw-log curves a well has, which are missing, and its Hugin intervals.
    Call this before analyzing a well.

    well_name: the well name, e.g. "F-15 D" or "15/9-F-1 B".
    """
    well = find_well(well_name)
    if not well:
        return no_such_well(well_name)

    raw, found, notes = load_input(well)
    missing = [c for c in INPUT_CURVES if c not in found]
    wells = memory_settings()["wells"]
    if well not in wells:
        zone = "no parameters in memory for this well"
    elif wells[well] is None:
        zone = "none: this well has no Hugin Fm., so it is outside the evaluated zone"
    else:
        zone = format_intervals(wells[well]["intervals"]) + " m MD"

    lines = [
        f"Well {well}: raw logs {raw.index.min():.1f} - {raw.index.max():.1f} m MD, step {depth_step(raw.index):.2f} m",
        f"Curves found: {', '.join(f'{s} (as {a})' for s, a in found.items())}",
        f"Curves missing: {', '.join(missing) or 'none'}",
        f"Hugin Fm. intervals (from memory): {zone}",
    ]
    return "\n".join(lines + notes)


@tool
def analyze_well(well_name: str) -> str:
    """Evaluate the Hugin reservoir of a well with Equinor's equations and the parameters in memory:
    VSH from GR, PHIF from density and neutron, SW with Archie, KLOGH, net sand and N/G.
    It uses only the raw logs; it does not look at Equinor's results.

    well_name: the well name, e.g. "F-15 D".
    """
    well = find_well(well_name)
    if not well:
        return no_such_well(well_name)
    wells = memory_settings()["wells"]
    if well not in wells:
        return f"Well {well} has no parameters in memory (AGENTS.md), so it cannot be evaluated."
    if wells[well] is None:
        return f"Well {well} has no Hugin Fm. (see memory), so there is nothing to evaluate in the Hugin zone."
    _, found, _ = load_input(well)
    missing = [c for c in INPUT_CURVES if c not in found]
    if missing:
        return f"Well {well} is missing {', '.join(missing)}, which the evaluation needs."

    df, f, p, notes = evaluate_well(well)
    s = summarize(df)
    if s is None:
        return f"Well {well}: no Hugin depths with GR, RHOB and NPHI."

    lines = [
        f"Well {well}, Hugin Fm.: {format_intervals(p['intervals'])} m MD",
        f"Parameters from memory: GRmin {p['grmin']:g}, GRmax {p['grmax']:g}, A {p['A']:g}, B {p['B']:g}, "
        f"rho_ma {f['rho_ma']:g}, rho_fl {f['rho_fl']:g}, n {f['n']:g}; {notes[-1]}",
        f"Hugin length along the well path with logs = {s['gross_m']:.1f} m MD; net sand length "
        f"(PHIF > {f['phi_cut']:g} and VSH < {f['vsh_cut']:g}) = {s['net_m']:.1f} m MD, N/G = {s['ng']:.3f}",
        "Note: these lengths are measured along the well path (MD). In a deviated or horizontal well "
        "they are NOT the thickness of the Hugin Fm.",
        f"Net sand averages: PHIF = {s['phif_net']:.3f}, SW (pore-volume weighted) = {s['sw_net']:.3f}, "
        f"hydrocarbon saturation (1 - SW) = {1 - s['sw_net']:.3f}",
        f"Net sand KLOGH: arithmetic = {s['k_arith']:.0f} mD, geometric = {s['k_geo']:.0f} mD",
        f"All Hugin depths: average VSH = {s['vsh_all']:.3f}, average PHIF = {s['phif_all']:.3f}",
    ]
    if s["net_without_rt"]:
        lines.append(f"Note: {s['net_without_rt']} net-sand depths have no RT, so no SW there")
    return "\n".join(lines + notes[:-1])


@tool
def compare_with_equinor(well_name: str) -> str:
    """Compare this agent's Hugin results, depth by depth, with Equinor's interpretation
    (the well's OUTPUT file: VSH, PHIF, SW, KLOGH and SAND_FLAG). Call it after analyze_well
    when the user asks how reliable the result is, or for a report.

    well_name: the well name, e.g. "F-15 D".
    """
    well = find_well(well_name)
    if not well:
        return no_such_well(well_name)
    settings = memory_settings()
    p, f = settings["wells"].get(well), settings["field"]
    if p is None:
        return f"Well {well} has no Hugin Fm. evaluation to compare."

    both = match_depths(well)
    causes = known_causes(p)
    lines = [f"Well {well}: this agent vs Equinor's interpretation, Hugin Fm."]

    for curve in ["VSH", "PHIF", "SW"]:
        d = curve_difference(both, curve)
        if d is None:
            lines.append(f"{curve}: no matching Equinor curve")
            continue
        lines.append(f"{curve}: {d['n']} depths, mean absolute difference = {d['mae']:.3f}, "
                     f"bias (ours - Equinor) = {d['bias']:+.3f}, correlation = {d['corr']:.2f}. "
                     f"Known cause: {curve} {causes[curve]}")

    dlog = permeability_difference(both)
    if dlog is not None:
        lines.append(f"KLOGH: mean absolute difference in log10 = {dlog:.2f} (a factor of about {10 ** dlog:.1f}). "
                     f"Known cause: KLOGH {causes['KLOGH']}")

    if "EQ_SAND_FLAG" not in both:
        lines.append("Net sand: Equinor's file has no SAND_FLAG curve, so net sand is not compared.")
        return "\n".join(lines)

    agree = net_sand_agreement(both)
    if agree:
        lines.append(f"Net sand: same decision as Equinor's SAND_FLAG at {agree['agree']:.0%} of depths; "
                     f"N/G ours = {agree['ng_ours']:.3f}, Equinor = {agree['ng_equinor']:.3f}. "
                     f"Known cause: net sand {causes['NET']}")
    split = ng_breakdown(both, f["phi_cut"], f["vsh_cut"])
    if split:
        lines.append(f"N/G breakdown: Equinor's own PHIF and VSH with the same cutoffs give N/G = {split['ng_curves']:.3f}. "
                     f"Of the difference ours - Equinor = {split['total']:+.3f}, "
                     f"{split['from_curves']:+.3f} comes from our curves vs Equinor's curves, and "
                     f"{split['from_edits']:+.3f} comes from Equinor's SAND_FLAG not following its own cutoffs "
                     f"(the report says the flag may have been edited by hand).")
    return "\n".join(lines)


TOOLS = [list_wells, describe_well, analyze_well, compare_with_equinor]
