"""Known-answer tests for the equations: inputs chosen by hand, answers worked out by hand.

Run (from the well_log_agent_standalone folder):
    uv run python phase1_training/test_petrophysics.py
"""

import numpy as np
import pandas as pd

from petrophysics import (in_intervals, net_sand, permeability, porosity, rw_at_temperature, shale_volume,
                          water_saturation)

S = pd.Series


def close(a, b, tol=0.001) -> bool:
    return abs(a - b) <= tol


def test_shale_volume():
    # GRmin 5, GRmax 110: GR 47 -> (47 - 5) / 105 = 0.40; below and above the range are clipped
    vsh = shale_volume(S([5.0, 47.0, 150.0, 0.0]), 5, 110)
    assert list(vsh.round(3)) == [0.0, 0.4, 1.0, 0.0]


def test_porosity():
    # RHOB 2.30 -> PHID = (2.65 - 2.30) / (2.65 - 0.9) = 0.20; NPHI 0.20 -> correction term is 0
    assert close(porosity(S([2.30]), S([0.20]), 2.65, 0.9, 0.4, 0.01)[0], 0.21)
    assert close(porosity(S([2.30]), S([0.20]), 2.65, 0.9, 0.0, 0.0)[0], 0.20)
    # NPHI 0.25: 0.20 + 0.4 x 0.05 + 0.01 = 0.23
    assert close(porosity(S([2.30]), S([0.25]), 2.65, 0.9, 0.4, 0.01)[0], 0.23)


def test_permeability():
    # 10^(2 + 8 x 0.21 - 9 x 0.10) = 10^2.78 = 602.6 mD
    assert close(permeability(S([0.21]), S([0.10]), 2, 8, -9)[0], 602.56, tol=0.1)


def test_rw_at_temperature():
    # 0.07 x 41.5 / 132.5 = 0.02192
    assert close(rw_at_temperature(0.07, 111), 0.02192, tol=0.00001)


def test_water_saturation():
    # Same depth, RT 10 vs 100 ohmm: SW must fall when RT rises, and PHIF does not take part in that change
    k = permeability(S([0.21, 0.21]), S([0.10, 0.10]), 2, 8, -9)
    rw = rw_at_temperature(0.07, 111)
    sw = water_saturation(S([0.21, 0.21]), S([10.0, 100.0]), k, rw, 1, 2.45, 1.865, -0.0083)
    assert close(sw[0], 0.253, tol=0.005) and close(sw[1], 0.099, tol=0.005)
    # No pore space -> SW = 1; no RT -> no SW
    sw = water_saturation(S([0.0, 0.2]), S([10.0, np.nan]), S([1.0, 100.0]), rw, 1, 2.45, 1.865, -0.0083)
    assert sw[0] == 1.0 and np.isnan(sw[1])


def test_net_sand():
    # pass both / porosity too low / too shaly / missing data
    net = net_sand(S([0.21, 0.08, 0.21, np.nan]), S([0.10, 0.10, 0.60, 0.10]), 0.10, 0.50)
    assert list(net[:3]) == [1.0, 0.0, 0.0] and np.isnan(net[3])


def test_in_intervals():
    depth = pd.Index([3000.0, 3100.0, 3200.0, 3300.0])
    assert list(in_intervals(depth, [(3050, 3150), (3250, 3350)])) == [False, True, False, True]


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS ✅ {test.__name__}")
    print(f"\n -> {len(tests)}/{len(tests)} equation tests passed")
