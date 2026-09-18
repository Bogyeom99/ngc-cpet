from services.lt_analysis import LactatePoint, estimate_lt


def test_lt_pipeline_runs():
    pts = [
        LactatePoint("4", 4.0, 1.05),
        LactatePoint("5.5", 5.5, 1.15),
        LactatePoint("7", 7.0, 1.35),
        LactatePoint("8.5", 8.5, 1.85),
        LactatePoint("10", 10.0, 2.50),
        LactatePoint("11.5", 11.5, 3.60),
        LactatePoint("13", 13.0, 4.80),
        LactatePoint("14.5", 14.5, 7.00),
        LactatePoint("AO", 16.0, 9.10),
    ]

    lt1, lt2 = estimate_lt(pts, True, True)

    assert lt1 is not None
    assert lt1.split is not None
    assert lt1.valid
    assert 4.0 <= lt1.threshold_load <= 16.0
    assert lt2 is not None
