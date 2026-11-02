"""BG Open Powerlifting: importers for Bulgarian powerlifting results."""

from __future__ import annotations

__version__ = "0.1.0"


def read_results(path, sheet=None, *, validate: bool = True):
    """Parse a standard-layout .xlsx into a StandardMeet.

    The meet holds Lifter objects (``meet.lifters``, or just iterate the meet) and the findings
    (``meet.issues``). With validate=True the data-quality checks run too and their findings are
    added to ``meet.issues``.
    """
    from .parse_standard import parse_standard
    from .validate_standard import validate_standard

    meet = parse_standard(path, sheet)
    if validate:
        meet.issues.extend(validate_standard(meet))
    return meet