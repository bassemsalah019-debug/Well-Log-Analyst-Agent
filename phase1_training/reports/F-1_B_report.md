# Petrophysical Evaluation Report: Well F-1_B (Hugin Formation)

## Summary
The Hugin Formation in well F-1_B exhibits excellent reservoir quality with a net-to-gross ratio of 0.985 and high average porosity of 19.8%. Water saturation averages 39.2% in the net sand, indicating favorable hydrocarbon accumulation.

## Data
- **Curves used**: GR, RHOB, NPHI, RT (none missing)
- **Hugin intervals (m MD)**: 3245.4-3304.2
- **Parameters from memory**: 
  - GRmin: 5
  - GRmax: 180
  - A: 0.4
  - B: 0.01
  - Matrix density ($\rho_{ma}$): 2.65 g/cm³
  - Fluid density ($\rho_{fl}$): 0.9 g/cm³
  - Archie $a$: 1
  - Archie $n$: 2.45
  - Archie $m$ coefficient: 1.865
  - Archie $m$ exponent: -0.0083
  - $R_w$ at 20°C: 0.07 ohmm ($R_w$ at 111°C = 0.0219 ohmm)
  - Reservoir temperature: 111°C
  - Net sand cutoffs: PHIF > 0.10, VSH < 0.50

## Results
| Parameter | Value |
|---|---|
| Hugin interval length (MD) | 58.9 m |
| Net sand length (MD) | 58.0 m |
| Net-to-Gross (N/G) | 0.985 |
| Average VSH (all Hugin) | 0.154 |
| Average PHIF (all Hugin) | 0.197 |
| Average PHIF (net sand) | 0.198 |
| Average SW (net sand) | 0.392 |
| Hydrocarbon saturation ($1 - S_W$) | 0.608 |
| KLOGH arithmetic mean (net sand) | 795 mD |
| KLOGH geometric mean (net sand) | 169 mD |

## Comparison with Equinor
| Curve / Metric | Comparison Result |
|---|---|
| **VSH** | 589 depths, mean absolute difference = 0.000, bias = -0.000, correlation = 1.00 |
| **PHIF** | 589 depths, mean absolute difference = 0.008, bias = +0.008, correlation = 0.95 |
| **SW** | 589 depths, mean absolute difference = 0.025, bias = -0.014, correlation = 0.97 |
| **KLOGH** | Mean absolute difference in log10 = 0.07 (factor of ~1.2) |
| **Net sand** | Same decision as Equinor's SAND_FLAG at 92% of depths; N/G ours = 0.985, Equinor = 0.905 |
| **N/G breakdown** | Equinor's own PHIF and VSH with same cutoffs give N/G = 0.905. Difference ours - Equinor = +0.080 (+0.080 from curves vs Equinor's curves, +0.000 from Equinor's hand edits) |

**Difference analysis**: Differences in PHIF, SW, and permeability stem from neutron correction terms ($A$ and $B$) and Equinor's unpublished hand edits on curves such as $R_T$ and `SAND_FLAG`.

## Limitations
- RT used as delivered (Equinor edited RT by hand).
- Constant reservoir temperature assumed (111°C) because files lack TVD.
- Depths and thicknesses are measured depth (MD), not true vertical thickness.
- SW assumes Hugin formation water (no flooding case).
