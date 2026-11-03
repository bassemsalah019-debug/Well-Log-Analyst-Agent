"""Find the wells on disk and read their LAS files."""

import re
from functools import lru_cache
from pathlib import Path

import lasio
import pandas as pd

from config import INPUT_CURVES, INPUT_FILE, OUTPUT_CURVES, OUTPUT_FILE, WELLS_DIR


def well_key(text: str) -> str:
    """'15/9-F-1 B', 'f-1_b' and 'F-1B' all become 'F1B'."""
    text = re.sub(r"^\s*15\s*[/_]\s*9\s*[-_ ]?", "", text.upper())
    return re.sub(r"[^A-Z0-9]", "", text)


def available_wells() -> list[str]:
    """Well folders that have both the raw-log file and Equinor's output file."""
    return sorted(
        folder.name.upper()
        for folder in WELLS_DIR.iterdir()
        if folder.is_dir() and (folder / INPUT_FILE).exists() and (folder / OUTPUT_FILE).exists()
    )


def find_well(name: str) -> str | None:
    """Match what the user typed to a well folder name, or None."""
    lookup = {well_key(w): w for w in available_wells()}
    return lookup.get(well_key(name))


def read_las(path: Path, curves: dict) -> tuple[pd.DataFrame, dict]:
    """Read a LAS file and keep only the wanted curves, renamed to standard names."""
    df = lasio.read(str(path), encoding="latin-1").df()
    df.columns = [str(c).upper().split(":")[0] for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    found = {}
    for standard, names in curves.items():
        match = next((n for n in names if n in df.columns), None)
        if match:
            found[standard] = match

    df = df[list(found.values())].rename(columns={name: std for std, name in found.items()})
    df.index = df.index.astype(float)
    return df.sort_index(), found


@lru_cache(maxsize=16)
def load_input(well: str) -> tuple[pd.DataFrame, dict, list[str]]:
    """Raw logs of one well, cached because the files are large. Fixes NPHI in % and RHOB in kg/m3."""
    df, found = read_las(WELLS_DIR / well / INPUT_FILE, INPUT_CURVES)
    notes = []
    if "NPHI" in df and df["NPHI"].median() > 1:
        df["NPHI"] = df["NPHI"] / 100
        notes.append("NPHI was in percent and was converted to a fraction")
    if "RHOB" in df and df["RHOB"].median() > 100:
        df["RHOB"] = df["RHOB"] / 1000
        notes.append("RHOB was in kg/m3 and was converted to g/cm3")
    return df, found, notes


@lru_cache(maxsize=16)
def load_output(well: str) -> tuple[pd.DataFrame, dict]:
    """Equinor's interpretation of one well. Only the comparison tool uses it."""
    return read_las(WELLS_DIR / well / OUTPUT_FILE, OUTPUT_CURVES)
