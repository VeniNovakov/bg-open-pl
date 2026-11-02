from __future__ import annotations

import math
from decimal import Decimal

_WILKS = {
    "F": (
        594.31747775582,
        -27.23842536447,
        0.82112226871,
        -0.00930733913,
        0.00004731582,
        -0.00000009054,
    ),
    "M": (
        -216.0475144,
        16.2606339,
        -0.002388645,
        -0.00113732,
        0.00000701863,
        -0.00000001291,
    ),
}
_WILKS_RANGE = {"F": (26.51, 154.53), "M": (40.0, 201.9)}


def wilks_factor(bodyweight_kg: Decimal, sex: str) -> Decimal | None:
    x = float(bodyweight_kg)
    lo, hi = _WILKS_RANGE[sex]
    if not lo <= x <= hi:
        return None
    denominator = sum(c * x**i for i, c in enumerate(_WILKS[sex]))
    return Decimal(str(round(500 / denominator, 6)))


def wilks_factor_female(bodyweight_kg: Decimal) -> Decimal | None:
    return wilks_factor(bodyweight_kg, "F")

_IPF_GL = {
    ("F", "classic"): (610.32796, 1045.59282, 0.03048),
    ("F", "equipped"): (758.63878, 949.31382, 0.02435),
    ("M", "classic"): (1199.72839, 1025.18162, 0.00921),
    ("M", "equipped"): (1236.25115, 1449.21864, 0.01644),
}


def ipf_gl_points(sex: str, equipment: str, bodyweight_kg: Decimal, total_kg: Decimal) -> Decimal | None:
    coeffs = _IPF_GL.get((sex, equipment))
    if coeffs is None:
        return None
    a, b, c = coeffs
    denominator = a - b * math.exp(-c * float(bodyweight_kg))
    return Decimal(str(round(float(total_kg) * 100 / denominator, 4)))