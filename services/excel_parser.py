from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass
from io import BytesIO

import numpy as np
import pandas as pd


BASE_COLUMNS = ["Time", "VO2/kg", "Heart Rate"]
STAGE_COLUMNS = ["Stage", "Speed"]
REST_LABELS = {"R", "REST"}
RECOVERY_LABELS = {"REC", "RECOVERY"}
ALLOUT_LABELS = {"AO", "ALL-OUT", "ALL OUT", "ALLOUT"}


@dataclass
class Segment:
    label: str
    indices: list[int]
    left: float
    right: float
    center: float
    duration: float
    load: float | None
    is_rest: bool
    is_recovery: bool
    is_allout: bool


def round_half_up(value: float) -> int:
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("반올림할 값이 유효한 숫자가 아닙니다.")
    return int(math.floor(value + 0.5))


def _normalized_label(label: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(label).strip().upper().replace("_", " "),
    )


def is_rest(label: object) -> bool:
    return _normalized_label(label) in REST_LABELS


def is_recovery(label: object) -> bool:
    text = _normalized_label(label)
    return (
        text in RECOVERY_LABELS
        or text.startswith("RECOVERY ")
        or text.startswith("REC ")
    )


def is_allout(label: object) -> bool:
    return _normalized_label(label) in ALLOUT_LABELS


def parse_load(label: object) -> float | None:
    if is_rest(label) or is_recovery(label) or is_allout(label):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(label))
    return float(match.group(1)) if match else None


def time_to_seconds(value: object) -> float:
    """Convert one time-like value to seconds.

    Numeric values are handled by _time_series_to_seconds so that elapsed
    seconds starting at 0, 1, 2 are not mistaken for Excel day fractions.
    """
    if pd.isna(value):
        return np.nan
    if isinstance(value, (pd.Timedelta, dt.timedelta)):
        return value.total_seconds()
    if isinstance(value, (dt.datetime, dt.time)):
        return (
            value.hour * 3600
            + value.minute * 60
            + value.second
            + value.microsecond / 1e6
        )
    if isinstance(value, (int, float, np.number)):
        return float(value)

    td = pd.to_timedelta(str(value), errors="coerce")
    return np.nan if pd.isna(td) else td.total_seconds()


def _time_series_to_seconds(series: pd.Series) -> pd.Series:
    """Convert a Time column while distinguishing seconds from Excel fractions."""
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().all():
        values = numeric.astype(float)

        # Typical elapsed-second data quickly exceeds 2. Treat the whole
        # column consistently as seconds, including the initial 0/1 rows.
        if float(values.max()) > 2.0:
            return values

        # A fully numeric column confined to one day and containing fractions
        # is most likely an Excel time serial.
        non_integer = np.abs(values - np.round(values)) > 1e-9
        if (
            float(values.min()) >= 0
            and float(values.max()) <= 1.0
            and bool(non_integer.any())
        ):
            return values * 86400.0

        return values

    return series.map(time_to_seconds)


def _stage_column(columns) -> str | None:
    normalized = {
        str(col).strip().lower(): col
        for col in columns
    }
    for name in STAGE_COLUMNS:
        key = name.lower()
        if key in normalized:
            return normalized[key]
    return None


def _find_data_sheet(
    xls: pd.ExcelFile,
    file_obj: BytesIO,
) -> str | None:
    for sheet in xls.sheet_names:
        preview = pd.read_excel(
            file_obj,
            sheet_name=sheet,
            engine="openpyxl",
            nrows=5,
        )
        file_obj.seek(0)
        if (
            all(col in preview.columns for col in BASE_COLUMNS)
            and _stage_column(preview.columns)
        ):
            return sheet
    return None


def _actual_duration(raw: np.ndarray) -> float:
    if len(raw) <= 1:
        return 1.0

    diffs = np.diff(raw.astype(float))
    positive = diffs[diffs > 0]

    if len(positive) == 0:
        return 0.0

    # Add one typical sampling interval so 0..299 s at 1 Hz represents
    # approximately 300 seconds rather than 299.
    sample_interval = float(np.median(positive))
    return float(raw[-1] - raw[0] + sample_interval)


def parse_excel(
    uploaded_file,
    stage_duration_min: float = 3.0,
    rest_duration_min: float = 1.0,
    allout_load: float | None = None,
) -> tuple[pd.DataFrame, list[Segment], pd.DataFrame]:
    if not np.isfinite(float(stage_duration_min)) or stage_duration_min <= 0:
        raise ValueError("일반 운동 Stage 시간은 0보다 커야 합니다.")
    if not np.isfinite(float(rest_duration_min)) or rest_duration_min <= 0:
        raise ValueError("Rest 시간은 0보다 커야 합니다.")

    stage_duration_sec = float(stage_duration_min) * 60.0
    rest_duration_sec = float(rest_duration_min) * 60.0
    raw_bytes = (
        uploaded_file.getvalue()
        if hasattr(uploaded_file, "getvalue")
        else uploaded_file.read()
    )
    if not raw_bytes:
        raise ValueError("Excel 파일이 비어 있습니다.")

    file_obj = BytesIO(raw_bytes)
    try:
        xls = pd.ExcelFile(file_obj, engine="openpyxl")
    except Exception as exc:
        raise ValueError(
            "Excel 파일을 열 수 없습니다. xlsx 또는 xlsm 파일인지 확인하세요."
        ) from exc

    file_obj.seek(0)
    sheet = (
        "Data"
        if "Data" in xls.sheet_names
        else _find_data_sheet(xls, file_obj)
    )
    if sheet is None:
        raise ValueError(
            "Time, VO2/kg, Heart Rate와 Stage 열을 가진 시트를 찾지 못했습니다."
        )

    file_obj.seek(0)
    raw_df = pd.read_excel(
        file_obj,
        sheet_name=sheet,
        engine="openpyxl",
    )

    missing = [
        c
        for c in BASE_COLUMNS
        if c not in raw_df.columns
    ]
    stage_col = _stage_column(raw_df.columns)

    if missing:
        raise ValueError(
            "필수 열이 없습니다: "
            + ", ".join(missing)
        )
    if stage_col is None:
        raise ValueError("필수 열이 없습니다: Stage")

    df = raw_df[BASE_COLUMNS + [stage_col]].copy()
    df = df.rename(columns={stage_col: "Stage"})
    df = (
        df.replace(r"^\s*$", np.nan, regex=True)
        .dropna(how="all")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError("Data 시트에 측정 데이터가 없습니다.")

    df["VO2/kg"] = pd.to_numeric(
        df["VO2/kg"],
        errors="coerce",
    )
    df["Heart Rate"] = pd.to_numeric(
        df["Heart Rate"],
        errors="coerce",
    )
    df["_raw_time"] = _time_series_to_seconds(df["Time"])

    if df["_raw_time"].isna().any():
        bad_rows = [
            i + 2
            for i in df.index[
                df["_raw_time"].isna()
            ].tolist()[:10]
        ]
        raise ValueError(
            "Time 값을 읽을 수 없는 Excel 행이 있습니다: "
            + ", ".join(map(str, bad_rows))
        )

    df["_segment_key"] = (
        df["Stage"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "__BLANK__")
    )
    changes = (
        df["_segment_key"]
        .ne(df["_segment_key"].shift())
        .fillna(True)
        .to_numpy(dtype=np.int64)
    )
    df["_segment"] = np.cumsum(changes)
    df["_x"] = np.nan

    raw_segments: list[
        tuple[str, list[int], np.ndarray]
    ] = []

    for _, group in df.groupby(
        "_segment",
        sort=False,
    ):
        label = group["_segment_key"].iloc[0]
        if label == "__BLANK__":
            continue

        idx = group.index.to_list()
        raw = df.loc[
            idx,
            "_raw_time",
        ].to_numpy(dtype=float)

        raw_segments.append(
            (str(label), idx, raw)
        )

    if not raw_segments:
        raise ValueError("Stage 값이 있는 구간이 없습니다.")

    segments: list[Segment] = []
    current = 0.0

    explicit_allout_present = any(
        is_allout(label)
        for label, _, _ in raw_segments
    )
    numeric_segment_indexes = [
        i
        for i, (label, _, _) in enumerate(raw_segments)
        if (
            parse_load(label) is not None
            and not is_rest(label)
            and not is_recovery(label)
            and not is_allout(label)
        )
    ]
    last_numeric_segment_index = (
        numeric_segment_indexes[-1]
        if numeric_segment_indexes
        else None
    )

    for segment_index, (label, idx, raw) in enumerate(raw_segments):
        actual_duration = _actual_duration(raw)

        if actual_duration <= 0:
            raise ValueError(
                f"{label} 구간의 Time 값이 올바르지 않습니다."
            )

        rest = is_rest(label)
        recovery = is_recovery(label)
        explicit_allout = is_allout(label)
        allout = (
            explicit_allout
            or (
                not explicit_allout_present
                and last_numeric_segment_index is not None
                and segment_index == last_numeric_segment_index
            )
        )

        load = parse_load(label)
        if (
            explicit_allout
            and allout_load is not None
            and np.isfinite(float(allout_load))
            and float(allout_load) > 0
        ):
            load = float(allout_load)

        display_label = (
            f"{load:g}"
            if load is not None and not explicit_allout
            else label
        )

        standard_stage = (
            load is not None
            and not rest
            and not recovery
            and not allout
        )

        if standard_stage or rest:
            duration = (
                stage_duration_sec
                if standard_stage
                else rest_duration_sec
            )
            if len(raw) == 1:
                xvals = np.array(
                    [current + duration / 2.0]
                )
            else:
                raw_span = float(raw[-1] - raw[0])
                if raw_span <= 0:
                    xvals = np.linspace(
                        current,
                        current + duration,
                        num=len(raw),
                        endpoint=False,
                    )
                else:
                    xvals = (
                        current
                        + ((raw - raw[0]) / raw_span)
                        * duration
                    )
        else:
            duration = actual_duration
            if len(raw) == 1:
                xvals = np.array(
                    [current + duration / 2.0]
                )
            else:
                raw_span = float(raw[-1] - raw[0])
                if raw_span <= 0:
                    xvals = np.linspace(
                        current,
                        current + duration,
                        num=len(raw),
                        endpoint=False,
                    )
                else:
                    scale = duration / raw_span
                    xvals = (
                        current
                        + (raw - raw[0]) * scale
                    )

        left = current
        right = current + duration
        center = (left + right) / 2.0

        df.loc[idx, "_x"] = xvals

        segments.append(
            Segment(
                label=display_label,
                indices=idx,
                left=left,
                right=right,
                center=center,
                duration=duration,
                load=load,
                is_rest=rest,
                is_recovery=recovery,
                is_allout=allout,
            )
        )
        current = right

    rows = []

    for seg in segments:
        if (
            seg.load is None
            or seg.is_rest
            or seg.is_recovery
        ):
            continue

        group = df.loc[seg.indices]
        hr = group["Heart Rate"].dropna()
        vo2 = group["VO2/kg"].dropna()

        rows.append(
            {
                "Stage": (
                    "All-Out"
                    if seg.is_allout
                    else seg.label
                ),
                "Load": seg.load,
                "Duration_sec": seg.duration,
                "HR_min": (
                    float(hr.min())
                    if not hr.empty
                    else np.nan
                ),
                "HR_max": (
                    float(hr.max())
                    if not hr.empty
                    else np.nan
                ),
                "HR_mean": (
                    float(hr.mean())
                    if not hr.empty
                    else np.nan
                ),
                "VO2_min": (
                    float(vo2.min())
                    if not vo2.empty
                    else np.nan
                ),
                "VO2_max": (
                    float(vo2.max())
                    if not vo2.empty
                    else np.nan
                ),
                "VO2_mean": (
                    float(vo2.mean())
                    if not vo2.empty
                    else np.nan
                ),
            }
        )

    summary = pd.DataFrame(
        rows,
        columns=[
            "Stage",
            "Load",
            "Duration_sec",
            "HR_min",
            "HR_max",
            "HR_mean",
            "VO2_min",
            "VO2_max",
            "VO2_mean",
        ],
    )

    return df, segments, summary
