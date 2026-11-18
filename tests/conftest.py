import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pfd.data import Hist, Opp, generate  # noqa: E402


@pytest.fixture(scope="session")
def synth():
    return generate()


def mk(oid, stage, amount, planned, created=date(2025, 1, 1), closed=None, cat="Pipeline", seg="SMB"):
    return Opp(oid, "Account 0001", "Rep 01", seg, amount, created, planned, stage, closed, cat)
