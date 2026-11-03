"""Read the field and well parameters from the memory file (memories/AGENTS.md)."""

import re

from config import FIELD_LABELS, MEMORY_FILE


def read_number(text: str, label: str) -> float:
    """Find a line like '- Matrix density: 2.65' and return 2.65."""
    pattern = rf"^-\s*{re.escape(label)}\s*:\s*(-?[0-9.]+)\s*$"
    found = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not found:
        raise ValueError(f"'{label}' is missing from AGENTS.md")
    return float(found.group(1))


def read_well_row(cells: list[str]) -> dict | None:
    """Turn one table row into the well's parameters (None if the well has no Hugin)."""
    _, intervals, grmin, grmax, a, b = cells
    if intervals.lower() == "none":
        return None
    pairs = []
    for part in intervals.split(";"):
        top, base = part.strip().split("-")
        pairs.append((float(top), float(base)))
    return {"intervals": pairs, "grmin": float(grmin), "grmax": float(grmax), "A": float(a), "B": float(b)}


def memory_settings() -> dict:
    """Read AGENTS.md on every call, so an edit takes effect at once."""
    if not MEMORY_FILE.exists():
        raise FileNotFoundError(f"Memory file not found: {MEMORY_FILE}")
    text = MEMORY_FILE.read_text(encoding="utf-8")

    field = {key: read_number(text, label) for label, key in FIELD_LABELS.items()}

    wells = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].upper().startswith("F-"):
            wells[cells[0].upper()] = read_well_row(cells)

    return {"field": field, "wells": wells}
