from app.services.reliability.anomaly_detection import (
    is_flatline, mad, population_std, robust_z, spike_score)


def test_mad_and_z():
    assert mad([1, 2, 3, 4, 100]) == 1
    assert robust_z(95, [40, 41, 39, 42], scale_floor=1) > 10
    assert robust_z(41, [40, 41, 39, 42], scale_floor=1) < 1
    assert population_std([2, 2, 2]) == 0


def test_spike_score_curve():
    assert spike_score(2.0) == 1.0
    assert spike_score(3.5) == 1.0
    assert 0 < spike_score(7.0) < 1
    assert spike_score(10.0) == 0.0


def test_flatline():
    assert is_flatline([5.0] * 10, 5.0, 10)
    assert not is_flatline([5.0] * 10, 5.5, 10)
    assert not is_flatline([5.0] * 3, 5.0, 10)
