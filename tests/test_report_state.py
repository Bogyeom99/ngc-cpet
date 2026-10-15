import datetime as dt

from services.report_state import build_report_state_token


def _base():
    meta = {
        "athlete": {
            "id": 7,
            "name": "테스트",
            "sex": "남",
            "category": "국가대표 후보",
        },
        "test_date": dt.date(2026, 10, 15),
        "load_type": "Speed",
        "load_unit": "km/h",
        "max_load": 20.0,
        "grade_percent": 6.0,
        "stage_duration_min": 5,
        "rest_duration_min": 1,
        "hrmax": 200,
        "vo2max": 70.0,
        "exercise_time": "40분",
    }
    parsed = {"upload_token": "abc123"}
    analysis = {
        "chart_points": [
            {"label": "10", "load": 10.0, "lactate": 2.0},
            {"label": "12", "load": 12.0, "lactate": 3.5},
        ]
    }
    lt1 = {
        "show": True,
        "valid": True,
        "load": 11.74,
        "hr": 144,
        "pct_hrmax": 72.0,
    }
    lt2 = {
        "show": True,
        "valid": True,
        "load": 18.63,
        "hr": 191,
        "pct_hrmax": 95.5,
    }
    return meta, parsed, analysis, lt1, lt2


def test_report_state_token_is_stable_for_same_analysis():
    args = _base()
    assert build_report_state_token(*args) == build_report_state_token(*args)


def test_report_state_token_changes_when_lt_result_changes():
    meta, parsed, analysis, lt1, lt2 = _base()
    first = build_report_state_token(meta, parsed, analysis, lt1, lt2)

    changed_lt1 = dict(lt1)
    changed_lt1["load"] = 7.80
    changed_lt1["hr"] = 132

    second = build_report_state_token(
        meta,
        parsed,
        analysis,
        changed_lt1,
        lt2,
    )
    assert first != second


def test_report_state_token_changes_when_lactate_changes():
    meta, parsed, analysis, lt1, lt2 = _base()
    first = build_report_state_token(meta, parsed, analysis, lt1, lt2)

    changed_analysis = {
        "chart_points": [
            {"label": "10", "load": 10.0, "lactate": 2.0},
            {"label": "12", "load": 12.0, "lactate": 4.2},
        ]
    }
    second = build_report_state_token(
        meta,
        parsed,
        changed_analysis,
        lt1,
        lt2,
    )
    assert first != second
