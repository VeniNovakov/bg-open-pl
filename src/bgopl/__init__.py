

from __future__ import annotations

__version__ = "0.1.0"


def read_results(path, sheet=None, *, validate: bool = True):
    from .parse_standard import parse_standard
    from .validate_standard import validate_standard

    meet = parse_standard(path, sheet)
    if validate:
        meet.issues.extend(validate_standard(meet))
    return meet