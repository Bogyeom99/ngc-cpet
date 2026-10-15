import pandas as pd

from services.excel_parser import Segment
from services.graph_service import (
    LEFT_PAD_SEC,
    _lactate_x_for_stage,
    make_hr_vo2_graph,
    make_hr_vo2_lactate_graph,
)


def _sample_graph_data():
    df = pd.DataFrame(
        {
            "_x": [
                0, 90, 180,
                180, 270, 360,
                360, 390, 420,
                420, 450, 480,
            ],
            "Heart Rate": [
                90, 105, 120,
                120, 135, 150,
                150, 170, 185,
                180, 160, 140,
            ],
            "VO2/kg": [
                15, 20, 25,
                25, 32, 40,
                40, 48, 55,
                50, 35, 25,
            ],
        }
    )

    segments = [
        Segment("100", [0, 1, 2], 0, 180, 90, 180, 100.0, False, False, False),
        Segment("150", [3, 4, 5], 180, 360, 270, 180, 150.0, False, False, False),
        Segment("All-Out", [6, 7, 8], 360, 420, 390, 60, 200.0, False, False, True),
        Segment("Recovery", [9, 10, 11], 420, 480, 450, 60, None, False, True, False),
    ]
    return df, segments


def test_basic_graph_renders_with_lt_lines():
    df, segments = _sample_graph_data()

    png, threshold_hr = make_hr_vo2_graph(
        df,
        segments,
        hrmax=190,
        lt1_load=125,
        lt2_load=175,
    )

    assert png.startswith(b"\x89PNG")
    assert threshold_hr["LT1"] is not None
    assert threshold_hr["LT2"] is not None


def test_combined_graph_renders_recovery_lactate():
    df, segments = _sample_graph_data()

    points = [
        {"label": "100", "load": 100.0, "lactate": 1.2},
        {"label": "150", "load": 150.0, "lactate": 2.1},
        {"label": "AO", "load": 200.0, "lactate": 7.5},
        {"label": "Recovery 1min", "load": None, "lactate": 5.4},
    ]

    png, threshold_hr = make_hr_vo2_lactate_graph(
        df,
        segments,
        hrmax=190,
        lactate_points=points,
        lt1_load=125,
        lt2_load=175,
        lt_label_mode="report",
    )

    assert png.startswith(b"\x89PNG")
    assert threshold_hr["LT1"] is not None
    assert threshold_hr["LT2"] is not None


def test_resting_lactate_stays_before_zero_even_with_stage_rest():
    segments = [
        Segment("4", [0], 0, 180, 90, 180, 4.0, False, False, False),
        Segment("R", [1], 180, 240, 210, 60, None, True, False, False),
        Segment("5.5", [2], 240, 420, 330, 180, 5.5, False, False, True),
    ]

    x = _lactate_x_for_stage(
        segments,
        "Rest",
        None,
    )

    assert x == -LEFT_PAD_SEC / 2
