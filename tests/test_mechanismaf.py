import pytest
from mechanismaf import create_linkage_from_spec

def test_create_linkage_from_spec():
    spec = [
        ["bar", (0, 0), (1, 1), {"style": "ground"}],
        ["bar", (1, 1), (2, 0)],
        ["bar", (2, 0), (1, -1), {"angle_sweep": (0, 0, 1)}],
        ["bar", (1, -1), (0, 0)],
    ]
    mech = create_linkage_from_spec(spec)
    assert mech is not None
