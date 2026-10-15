from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any


def _date_text(value: Any) -> str:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return str(value)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_report_state_token(
    meta: dict[str, Any],
    parsed: dict[str, Any],
    analysis: dict[str, Any],
    lt1_item: dict[str, Any],
    lt2_item: dict[str, Any],
) -> str:
    """
    Build a stable key for one exact report-analysis state.

    The key changes when the athlete, measurement settings, uploaded data,
    lactate values, or calculated LT results change. This prevents editable
    report text from a previous analysis from leaking into a new result while
    still preserving edits during reruns of the same analysis.
    """
    athlete = meta.get("athlete") or {}

    chart_points = []
    for point in analysis.get("chart_points") or []:
        chart_points.append(
            {
                "label": str(point.get("label", "")),
                "load": _float_or_none(point.get("load")),
                "lactate": _float_or_none(point.get("lactate")),
            }
        )

    payload = {
        "athlete": {
            "id": athlete.get("id"),
            "name": athlete.get("name"),
            "sex": athlete.get("sex"),
            "category": athlete.get("category"),
        },
        "test_date": _date_text(meta.get("test_date", "")),
        "measurement": {
            "load_type": meta.get("load_type"),
            "load_unit": meta.get("load_unit"),
            "max_load": _float_or_none(meta.get("max_load")),
            "grade_percent": _float_or_none(meta.get("grade_percent")),
            "stage_duration_min": _float_or_none(
                meta.get("stage_duration_min")
            ),
            "rest_duration_min": _float_or_none(
                meta.get("rest_duration_min")
            ),
            "hrmax": _float_or_none(meta.get("hrmax")),
            "vo2max": _float_or_none(meta.get("vo2max")),
            "exercise_time": str(meta.get("exercise_time", "")),
        },
        "upload_token": parsed.get("upload_token"),
        "chart_points": chart_points,
        "lt1": {
            "show": lt1_item.get("show"),
            "valid": lt1_item.get("valid"),
            "load": _float_or_none(lt1_item.get("load")),
            "hr": _float_or_none(lt1_item.get("hr")),
            "pct_hrmax": _float_or_none(lt1_item.get("pct_hrmax")),
            "reason": lt1_item.get("reason"),
        },
        "lt2": {
            "show": lt2_item.get("show"),
            "valid": lt2_item.get("valid"),
            "load": _float_or_none(lt2_item.get("load")),
            "hr": _float_or_none(lt2_item.get("hr")),
            "pct_hrmax": _float_or_none(lt2_item.get("pct_hrmax")),
            "reason": lt2_item.get("reason"),
        },
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha1(
        serialized.encode("utf-8")
    ).hexdigest()[:16]

    athlete_key = (
        athlete.get("id")
        if athlete.get("id") is not None
        else athlete.get("name", "athlete")
    )
    return (
        f"{athlete_key}_"
        f"{_date_text(meta.get('test_date', ''))}_"
        f"{digest}"
    )
