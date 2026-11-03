"""Paths, file names and curve names used across the project."""

from pathlib import Path

BASE_DIR = Path(__file__).parent
WELLS_DIR = BASE_DIR / "wells"
REPORTS_DIR = BASE_DIR / "reports"
MEMORY_DIR = BASE_DIR / "memories"
SKILLS_DIR = BASE_DIR / "skills"
MEMORY_FILE = MEMORY_DIR / "AGENTS.md"

INPUT_FILE = "WLC_PETRO_COMPUTED_INPUT_1.LAS"     # raw logs: what the agent calculates from
OUTPUT_FILE = "WLC_PETRO_COMPUTED_OUTPUT_1.LAS"   # Equinor's interpretation: the reference

# The same curve can have different names in different LAS files.
INPUT_CURVES = {
    "GR": ["GR", "GRD", "GRC", "SGR"],
    "RHOB": ["RHOB", "DEN", "RHOZ"],
    "NPHI": ["NPHI", "TNPH", "NPOR", "CNC"],
    "RT": ["RT", "RPCEHM", "RD", "RDEP", "LLD", "ILD"],
}
OUTPUT_CURVES = {
    "VSH": ["VSH"],
    "PHIF": ["PHIF"],
    "SW": ["SW"],
    "KLOGH": ["KLOGH"],
    "SAND_FLAG": ["SAND_FLAG"],
}

# Line labels in AGENTS.md -> short names used in the code
FIELD_LABELS = {
    "Matrix density": "rho_ma",
    "Fluid density": "rho_fl",
    "Archie a": "a",
    "Archie n": "n",
    "Archie m coefficient": "m_coef",
    "Archie m exponent": "m_exp",
    "Rw at 20 C": "rw20",
    "Reservoir temperature C": "temp",
    "KLOGH intercept": "k0",
    "KLOGH PHIF coefficient": "k1",
    "KLOGH VSH coefficient": "k2",
    "Net sand porosity cutoff": "phi_cut",
    "Net sand Vsh cutoff": "vsh_cut",
}
