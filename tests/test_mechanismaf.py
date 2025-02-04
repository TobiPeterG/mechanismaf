import pytest
from mechanismaf import create_linkage_from_spec

def test_create_linkage_from_spec():
    spec = [
        ["bar", (0, 0), (0, 1), {"style": "ground"}],
        ["bar", (0, 1), (1, 1), {"angle_sweep": (20, -20, 20)}],
        ["bar", (1, 1), (1, 0)],
        ["bar", (1, 0), (0, 0)],
    ]
    mech = create_linkage_from_spec(spec)
    assert mech is not None
