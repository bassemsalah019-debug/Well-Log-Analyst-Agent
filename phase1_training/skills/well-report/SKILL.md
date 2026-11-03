---
name: well-report
description: Use when the user asks for a report on a well.
---

# Well report

1. Call describe_well to see which curves the file has and whether it has Hugin Fm.
2. Call analyze_well.
3. Call compare_with_equinor.
4. Write the report with write_file to /reports/<WELL>_report.md (for example /reports/F-15_D_report.md), with exactly these sections:
   - Summary: two or three sentences on Hugin reservoir quality and hydrocarbon saturation.
   - Data: the curves used, the Hugin intervals and the parameters from memory.
   - Results: a table with every number analyze_well returned, copied exactly.
   - Comparison with Equinor: a table with every number compare_with_equinor returned, copied exactly, and one sentence on what the differences mean.
   - Limitations: RT used as delivered (Equinor edited RT by hand), constant reservoir temperature, thickness in MD, SW assumes Hugin formation water.
5. Use only numbers from the tools. Do not add interpretation the numbers do not support.
