# Well Log Agent memory (Volve field, Hugin Fm.)

## Field settings (Hugin Fm., same in every Equinor report)
- Matrix density: 2.65
- Fluid density: 0.9
- Archie a: 1
- Archie n: 2.45
- Archie m coefficient: 1.865
- Archie m exponent: -0.0083
- Rw at 20 C: 0.07
- Reservoir temperature C: 111
- KLOGH intercept: 2
- KLOGH PHIF coefficient: 8
- KLOGH VSH coefficient: -9
- Net sand porosity cutoff: 0.10
- Net sand Vsh cutoff: 0.50

## Well parameters (Hugin Fm.)
| Well | Hugin intervals (m MD) | GRmin | GRmax | A | B |
|---|---|---|---|---|---|
| F-1 | none | - | - | - | - |
| F-1_A | 3435.0-3500.2 | 9 | 135 | 0 | 0 |
| F-1_B | 3245.4-3304.2 | 5 | 180 | 0.4 | 0.01 |
| F-1_C | 3230.0-4004.0 | 7 | 120 | 0.4 | 0.01 |
| F-11_A | 3594.6-3702.0 | 7 | 150 | 0.4 | 0.01 |
| F-11_B | 3467.5-3812.0; 3894.0-3934.0; 3952.0-4374.0; 4483.5-4732.0 | 5 | 127 | 0.4 | 0.01 |
| F-11_T2 | 4393.0-4497.4 | 4 | 184 | 0 | 0 |
| F-12 | 3126.0-3280.0 | 16 | 120 | 0.4 | 0.01 |
| F-15_D | 3484.0-4564.0; 4580.3-4597.6 | 5 | 110 | 0.4 | 0.01 |

## Field notes
- Source: Equinor's petrophysical reports in each well folder (PETROPHYSICAL_REPORT_*.PDF), which follow the Volve field model 2006.
- Equations (Equinor): VSH = (GR - GRmin) / (GRmax - GRmin); PHID = (2.65 - RHOB) / (2.65 - 0.9); PHIF = PHID + A x (NPHI - PHID) + B; KLOGH = 10^(2 + 8 x PHIF - 9 x VSH); m = 1.865 x KLOGH^(-0.0083); SW = (a x Rw / (PHIF^m x RT))^(1/n).
- Rw is corrected to reservoir temperature with Arps: Rw(T) = Rw20 x (20 + 21.5) / (T + 21.5).
- Net sand = PHIF > 0.10 and VSH < 0.50 (Equinor's cutoffs, about 0.5 mD core permeability).
- F-1 has no Hugin Fm. (only Heather, Skagerak and Smith Bank), so it is outside the evaluated zone.
- What each result depends on: VSH uses only GR; PHIF uses only RHOB and NPHI (never RT); KLOGH uses PHIF and VSH; SW uses PHIF and RT.
- Equinor edited RT by hand in some intervals (curve RT_EDIT, not in the files); the agent uses RT as delivered.
- Equinor reports SW as if the whole Hugin had Hugin formation water (no flooding case); the agent makes the same assumption.
- Reservoir temperature is held constant at 111 C because the files have no TVD.
- Depths and thicknesses are measured depth (MD), not true vertical thickness.
- F-12 Hugin interval is read from the CPI plot in its 2007 report (about 1 m uncertainty).
