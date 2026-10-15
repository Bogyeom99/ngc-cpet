from io import BytesIO

import numpy as np
import pandas as pd

from services.excel_parser import (
    is_allout,
    is_recovery,
    is_rest,
    parse_excel,
)
from services.input_template import (
    build_input_template,
    parse_lactate_sheet,
)


def _excel_bytes(data: pd.DataFrame, lactate: pd.DataFrame | None = None) -> BytesIO:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Data", index=False)
        if lactate is not None:
            lactate.to_excel(writer, sheet_name="Lactate", index=False)
    out.seek(0)
    return out


def test_generic_stage_is_normalized_and_final_numeric_stage_is_allout():
    data = pd.DataFrame(
        {
            "Time": list(range(30)),
            "VO2/kg": np.linspace(10, 30, 30),
            "Heart Rate": np.linspace(90, 150, 30),
            "Stage": [3] * 10 + [4.5] * 10 + [6] * 10,
        }
    )

    _, segments, summary = parse_excel(
        _excel_bytes(data),
        stage_duration_min=5,
    )

    assert len(segments) == 3
    assert segments[0].duration == 300
    assert segments[1].duration == 300
    assert segments[2].is_allout
    assert 9.5 <= segments[2].duration <= 10.5
    assert segments[2].load == 6.0
    assert summary["Stage"].tolist() == ["3", "4.5", "All-Out"]


def test_power_stages_allout_and_recovery_are_supported():
    data = pd.DataFrame(
        {
            "Time": list(range(14)),
            "VO2/kg": np.linspace(10, 35, 14),
            "Heart Rate": np.linspace(90, 180, 14),
            "Stage": (
                [100] * 3
                + [150] * 3
                + ["All-Out"] * 3
                + ["Recovery"] * 5
            ),
        }
    )

    _, segments, summary = parse_excel(
        _excel_bytes(data),
        stage_duration_min=4,
        allout_load=200,
    )

    assert [seg.label for seg in segments] == [
        "100",
        "150",
        "All-Out",
        "Recovery",
    ]
    assert segments[0].duration == 240
    assert segments[1].duration == 240
    assert segments[2].is_allout
    assert segments[2].load == 200
    assert segments[3].is_recovery
    assert summary["Load"].tolist() == [100.0, 150.0, 200.0]


def test_legacy_speed_column_still_works():
    data = pd.DataFrame(
        {
            "Time": list(range(6)),
            "VO2/kg": [10, 11, 12, 13, 14, 15],
            "Heart Rate": [90, 92, 94, 96, 98, 100],
            "Speed": [3, 3, 3, 4.5, 4.5, 4.5],
        }
    )

    _, segments, _ = parse_excel(
        _excel_bytes(data),
        stage_duration_min=3,
    )

    assert [seg.load for seg in segments] == [3.0, 4.5]


def test_elapsed_seconds_starting_at_zero_are_not_excel_day_fractions():
    data = pd.DataFrame(
        {
            "Time": [0, 1, 2, 3, 4, 5],
            "VO2/kg": [10, 11, 12, 13, 14, 15],
            "Heart Rate": [90, 92, 94, 96, 98, 100],
            "Stage": ["All-Out"] * 6,
        }
    )

    df, segments, _ = parse_excel(
        _excel_bytes(data),
        allout_load=12,
    )

    assert df["_raw_time"].tolist() == [0, 1, 2, 3, 4, 5]
    assert 5.5 <= segments[0].duration <= 6.5


def test_lactate_sheet_uses_numeric_final_stage_for_allout():
    data = pd.DataFrame(
        {
            "Time": [0, 1, 2, 3, 4, 5],
            "VO2/kg": [10, 11, 12, 13, 14, 15],
            "Heart Rate": [90, 95, 100, 105, 110, 115],
            "Stage": [14, 14, 14, 16, 16, 16],
        }
    )
    lactate = pd.DataFrame(
        {
            "Stage": [14, 16, "Recovery 1min", "Recovery 5min"],
            "Lactate": [3.5, 7.8, 6.2, 3.1],
        }
    )

    rows = parse_lactate_sheet(
        _excel_bytes(data, lactate)
    )

    assert rows[1]["stage"] == "16"
    assert rows[1]["lactate"] == 7.8


def test_lactate_sheet_reads_rest_allout_and_recovery():
    data = pd.DataFrame(
        {
            "Time": [0, 1, 2, 3],
            "VO2/kg": [10, 11, 12, 13],
            "Heart Rate": [90, 95, 100, 105],
            "Stage": [3, 3, 4.5, 4.5],
        }
    )
    lactate = pd.DataFrame(
        {
            "Stage": ["Rest", "3", "4.5", "All-Out", "Recovery 1min"],
            "Lactate": [0.9, 1.1, 1.4, 7.2, 5.1],
        }
    )

    rows = parse_lactate_sheet(
        _excel_bytes(data, lactate)
    )

    assert len(rows) == 5
    assert rows[-1]["stage"] == "Recovery 1min"
    assert rows[-1]["lactate"] == 5.1


def test_label_helpers():
    assert is_rest("R")
    assert is_rest("rest")
    assert is_allout("All-Out")
    assert is_recovery("Recovery 5min")


def test_download_template_uses_stage_column():
    template = BytesIO(build_input_template())
    df = pd.read_excel(
        template,
        sheet_name="Data",
        engine="openpyxl",
    )
    assert df.columns.tolist() == [
        "Time",
        "VO2/kg",
        "Heart Rate",
        "Stage",
    ]


def test_rest_is_normalized_to_configured_duration():
    data = pd.DataFrame(
        {
            "Time": list(range(24)),
            "VO2/kg": np.linspace(10, 30, 24),
            "Heart Rate": np.linspace(90, 150, 24),
            "Stage": [4] * 8 + ["R"] * 5 + [5.5] * 8 + [7] * 3,
        }
    )

    _, segments, _ = parse_excel(
        _excel_bytes(data),
        stage_duration_min=3,
        rest_duration_min=1.5,
    )

    rest = next(seg for seg in segments if seg.is_rest)
    assert rest.duration == 90.0
    assert segments[0].duration == 180.0
    assert segments[-1].is_allout


def test_rest_duration_can_be_shorter_than_recorded_rest():
    data = pd.DataFrame(
        {
            "Time": list(range(18)),
            "VO2/kg": np.linspace(10, 25, 18),
            "Heart Rate": np.linspace(90, 145, 18),
            "Stage": [4] * 6 + ["Rest"] * 6 + [5.5] * 6,
        }
    )

    _, segments, _ = parse_excel(
        _excel_bytes(data),
        stage_duration_min=3,
        rest_duration_min=0.5,
    )

    rest = next(seg for seg in segments if seg.is_rest)
    assert rest.duration == 30.0
