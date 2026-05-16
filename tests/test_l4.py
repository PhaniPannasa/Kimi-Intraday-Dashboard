import pytest
from layers.l4_sector import compute_rs_ratio, rank_sectors


def test_compute_rs_ratio():
    assert compute_rs_ratio(0.02, 0.01, 0.005) == 400.0


def test_rank_sectors():
    sectors = {"Bank": 0.05, "IT": 0.01}
    histories = {"Bank": [1.0, 1.02, 1.04], "IT": [1.0, 1.01, 1.01]}
    result = rank_sectors(sectors, 0.015, histories)
    assert result[0]["sector"] == "Bank"
    assert result[0]["rank"] == 1
