from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass
from io import BytesIO

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ["Time", "VO2/kg", "Heart Rate", "Speed"]
REST_LABELS = {"R", "REST"}
STAGE_SEC = 180.0
REST_SEC = 60.0


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


def round_half_up(value: float) -> int:
    return int(math.floor(float(value) + 0.5))


def is_rest(label: object) -> bool:
    return str(label).strip().upper() in REST_LABELS


def parse_load(label: object) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", str(label))
    return float(match.group(1)) if match else None


def time_to_seconds(value: object) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (pd.Timedelta, dt.timedelta)):
        return value.total_seconds()
    if isinstance(value, (dt.datetime, dt.time)):
        return value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1e6
    if isinstance(value, (int, float, np.number)):
        value = float(value)
        return value * 86400 if 0 <= value < 2 else value
    td = pd.to_timedelta(str(value), errors="coerce")
    return np.nan if pd.isna(td) else td.total_seconds()


def _find_data_sheet(xls: pd.ExcelFile, file_obj: BytesIO) -> str | None:
    for sheet in xls.sheet_names:
        preview = pd.read_excel(file_obj, sheet_name=sheet, engine="openpyxl", nrows=5)
        file_obj.seek(0)
        if all(col in preview.columns for col in REQUIRED_COLUMNS):
            return sheet
    return None


def parse_excel(uploaded_file) -> tuple[pd.DataFrame, list[Segment], pd.DataFrame]:
    raw_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    file_obj = BytesIO(raw_bytes)
    xls = pd.ExcelFile(file_obj, engine="openpyxl")
    file_obj.seek(0)

    sheet = "Data" if "Data" in xls.sheet_names else _find_data_sheet(xls, file_obj)
    if sheet is None:
        raise ValueError("Time, VO2/kg, Heart Rate, Speed 열을 가진 시트를 찾지 못했습니다.")

    file_obj.seek(0)
    df = pd.read_excel(file_obj, sheet_name=sheet, engine="openpyxl")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 열이 없습니다: {missing}")

    df = df[REQUIRED_COLUMNS].replace(r"^\s*$", np.nan, regex=True).dropna(how="all").reset_index(drop=True)
    df["VO2/kg"] = pd.to_numeric(df["VO2/kg"], errors="coerce")
    df["Heart Rate"] = pd.to_numeric(df["Heart Rate"], errors="coerce")
    df["_raw_time"] = df["Time"].map(time_to_seconds)

    if df["_raw_time"].isna().any():
        bad_rows = [i + 2 for i in df.index[df["_raw_time"].isna()].tolist()[:10]]
        raise ValueError(f"Time 값을 읽을 수 없는 Excel 행이 있습니다: {bad_rows}")

    df["_segment_key"] = df["Speed"].fillna("").astype(str).str.strip().replace("", "__BLANK__")
    changes = df["_segment_key"].ne(df["_segment_key"].shift()).fillna(True).to_numpy(dtype=np.int64)
    df["_segment"] = np.cumsum(changes)
    df["_x"] = np.nan

    raw_segments: list[tuple[str, list[int], np.ndarray]] = []
    for _, group in df.groupby("_segment", sort=False):
        label = group["_segment_key"].iloc[0]
        if label == "__BLANK__":
            continue
        idx = group.index.to_list()
        raw = df.loc[idx, "_raw_time"].to_numpy(dtype=float)
        raw_segments.append((str(label), idx, raw))

    segments: list[Segment] = []
    current = 0.0

    for i, (label, idx, raw) in enumerate(raw_segments):
        n = len(raw)
        actual_duration = float(raw[-1] - raw[0]) if n > 1 else 0.0

        if n > 1 and actual_duration <= 0:
            raise ValueError(f"{label} 구간의 Time 값이 올바르지 않습니다.")

        last_segment = i == len(raw_segments) - 1
        rest = is_rest(label)

        if last_segment:
            if n < 2:
                raise ValueError("마지막 운동 Stage의 Time 데이터가 부족합니다.")
            duration = actual_duration
            xvals = current + (raw - raw[0])
        else:
            duration = REST_SEC if rest else STAGE_SEC
            if n == 1:
                xvals = np.array([current + duration / 2])
            else:
                xvals = current + ((raw - raw[0]) / actual_duration) * duration

        left = current
        right = current + duration
        center = (left + right) / 2
        df.loc[idx, "_x"] = xvals

        segments.append(
            Segment(
                label=label,
                indices=idx,
                left=left,
                right=right,
                center=center,
                duration=duration,
                load=parse_load(label),
                is_rest=rest,
            )
        )
        current = right

    if not segments:
        raise ValueError("Speed 값이 있는 구간이 없습니다.")
    if segments[-1].is_rest:
        raise ValueError("마지막 유효 구간은 운동 Stage여야 합니다.")

    rows = []
    for seg in segments:
        if seg.is_rest:
            continue
        group = df.loc[seg.indices]
        hr = group["Heart Rate"].dropna()
        vo2 = group["VO2/kg"].dropna()
        rows.append(
            {
                "Stage": seg.label,
                "Load": seg.load,
                "Duration_sec": seg.duration,
                "HR_min": float(hr.min()) if not hr.empty else np.nan,
                "HR_max": float(hr.max()) if not hr.empty else np.nan,
                "HR_mean": float(hr.mean()) if not hr.empty else np.nan,
                "VO2_min": float(vo2.min()) if not vo2.empty else np.nan,
                "VO2_max": float(vo2.max()) if not vo2.empty else np.nan,
                "VO2_mean": float(vo2.mean()) if not vo2.empty else np.nan,
            }
        )

    summary = pd.DataFrame(rows)
    return df, segments, summary
