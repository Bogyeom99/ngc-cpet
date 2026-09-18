from __future__ import annotations

from io import BytesIO
import math

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

from services.excel_parser import Segment, round_half_up


COLOR_HR = "#E31A1C"
COLOR_VO2 = "#2679D9"
COLOR_LAC = "#00A6E8"
COLOR_LT1 = "#228B22"
COLOR_LT2 = "#006400"


def _set_korean_font() -> None:
    preferred = ["Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", "AppleGothic"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def fmt_time(sec: float) -> str:
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def threshold_x(segments: list[Segment], load_value: float) -> float:
    stages = sorted(
        [seg for seg in segments if not seg.is_rest and seg.load is not None],
        key=lambda s: s.load,
    )

    if len(stages) < 2:
        raise ValueError("LT 위치 계산에 필요한 운동 Stage가 부족합니다.")
    if not stages[0].load <= load_value <= stages[-1].load:
        raise ValueError("LT 값이 측정 부하 범위를 벗어났습니다.")

    for left, right in zip(stages[:-1], stages[1:]):
        if left.load <= load_value <= right.load:
            ratio = (load_value - left.load) / (right.load - left.load)
            if ratio < 0.5:
                return left.center + (left.right - left.center) * (ratio / 0.5)
            return right.left + (right.center - right.left) * ((ratio - 0.5) / 0.5)

    return stages[-1].center


def hr_at_x(df: pd.DataFrame, x_value: float) -> float | None:
    valid = df[["_x", "Heart Rate"]].dropna().sort_values("_x")
    if valid.empty or x_value < valid["_x"].min() or x_value > valid["_x"].max():
        return None

    return float(
        np.interp(
            x_value,
            valid["_x"].to_numpy(float),
            valid["Heart Rate"].to_numpy(float),
        )
    )


def make_hr_vo2_graph(
    df: pd.DataFrame,
    segments: list[Segment],
    hrmax: float,
    lt1_load: float | None = None,
    lt2_load: float | None = None,
) -> tuple[bytes, dict[str, float | None]]:
    _set_korean_font()

    fig, ax = plt.subplots(figsize=(15.8, 8.8), dpi=150)
    fig.subplots_adjust(left=0.08, right=0.82, bottom=0.18, top=0.93)
    ax2 = ax.twinx()

    hr_ymin = 50
    hr_ymax = max(
        225,
        math.ceil(max(hrmax, float(df["Heart Rate"].max(skipna=True))) / 25) * 25,
    )
    vo2_ymin = 0
    vo2_ymax = max(
        100,
        math.ceil(float(df["VO2/kg"].max(skipna=True)) / 10) * 10,
    )

    zones = [
        ("Z1", hrmax * 0.50, hrmax * 0.60, "#F4E7A1"),
        ("Z2", hrmax * 0.60, hrmax * 0.70, "#F4D7A0"),
        ("Z3", hrmax * 0.70, hrmax * 0.80, "#F1BD82"),
        ("Z4", hrmax * 0.80, hrmax * 0.90, "#EC9C77"),
        ("Z5", hrmax * 0.90, hrmax * 1.00, "#E77979"),
    ]

    for _, low, high, color in zones:
        ax.axhspan(low, high, color=color, alpha=0.42, zorder=0)

    for seg in segments:
        if seg.is_rest:
            ax.axvspan(seg.left, seg.right, color="#B8B8B8", alpha=0.20, zorder=0)
        ax.axvline(seg.left, color="#BFBFBF", ls="--", lw=0.8, zorder=1)

    ax.axvline(segments[-1].right, color="#BFBFBF", ls="--", lw=0.8, zorder=1)

    ax.plot(df["_x"], df["Heart Rate"], color=COLOR_HR, lw=1.6, zorder=3)
    ax2.plot(df["_x"], df["VO2/kg"], color=COLOR_VO2, lw=1.15, zorder=3)

    for seg in segments:
        ax.text(
            seg.center,
            hr_ymax - 2.5,
            seg.label,
            ha="center",
            va="top",
            fontsize=8.5,
            color="black",
            zorder=5,
        )

    exercise_segments = [seg for seg in segments if not seg.is_rest]

    for seg in exercise_segments:
        group = df.loc[seg.indices]
        cap = max(seg.duration * 0.08, 5)
        hr = group["Heart Rate"].dropna()
        vo2 = group["VO2/kg"].dropna()

        if not hr.empty:
            low, high = float(hr.min()), float(hr.max())
            y0 = min(high + 2, hr_ymax - 26)
            y1 = y0 + 8
            ax.vlines(seg.center, y0, y1, color="black", lw=1.1, zorder=4)
            ax.hlines(
                [y0, y1],
                seg.center - cap,
                seg.center + cap,
                color="black",
                lw=1.1,
                zorder=4,
            )
            ax.annotate(
                f"{round_half_up(low)}-{round_half_up(high)}",
                (seg.center, y1),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        if not vo2.empty:
            low, high = float(vo2.min()), float(vo2.max())
            y1 = max(low - 2, vo2_ymin + 16)
            y0 = y1 - 10
            ax2.vlines(seg.center, y0, y1, color=COLOR_VO2, lw=1.1, zorder=4)
            ax2.hlines(
                [y0, y1],
                seg.center - cap,
                seg.center + cap,
                color=COLOR_VO2,
                lw=1.1,
                zorder=4,
            )
            ax2.annotate(
                f"{low:.1f}-{high:.1f}",
                (seg.center, y0),
                xytext=(0, -6),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=9,
                color=COLOR_VO2,
                fontstyle="italic",
            )

    threshold_hr: dict[str, float | None] = {"LT1": None, "LT2": None}

    for name, load, color in [
        ("LT1", lt1_load, COLOR_LT1),
        ("LT2", lt2_load, COLOR_LT2),
    ]:
        if load is None:
            continue

        x = threshold_x(segments, load)
        hr = hr_at_x(df, x)
        threshold_hr[name] = hr

        ax.axvline(x, color=color, lw=2.0, ls="--", zorder=4)

        label = f"{name} {load:.2f}"
        if hr is not None:
            label += f"\n{round_half_up(hr)} bpm"

        ax.annotate(
            label,
            xy=(x, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=color,
            fontsize=10,
            fontweight="bold",
            annotation_clip=False,
        )

    total_end = segments[-1].right
    ax.set_xlim(0, total_end)
    ax.set_ylim(hr_ymin, hr_ymax)
    ax2.set_ylim(vo2_ymin, vo2_ymax)

    ax.set_ylabel("Heart Rate (bpm)", color=COLOR_HR, fontsize=14)
    ax2.set_ylabel("VO2/kg (ml/kg/min)", color=COLOR_VO2, fontsize=14)

    ax.tick_params(axis="y", colors=COLOR_HR)
    ax2.tick_params(axis="y", colors=COLOR_VO2)

    ticks = list(dict.fromkeys([0.0] + [seg.right for seg in segments]))
    ax.set_xticks(ticks)
    ax.set_xticklabels([fmt_time(t) for t in ticks], fontsize=7)
    ax.set_xlabel("Time (mm:ss)", fontsize=12)

    ax.grid(axis="y", ls="--", lw=0.7, color="#D2D2D2")
    ax.grid(False, axis="x")

    handles = [
        Line2D([0], [0], color=COLOR_HR, lw=1.6),
        Line2D([0], [0], color=COLOR_VO2, lw=1.15),
    ]
    labels = ["HR (bpm)", "VO2/kg"]

    if lt1_load is not None:
        handles.append(Line2D([0], [0], color=COLOR_LT1, lw=2, ls="--"))
        labels.append(f"LT1 ({lt1_load:.2f})")

    if lt2_load is not None:
        handles.append(Line2D([0], [0], color=COLOR_LT2, lw=2, ls="--"))
        labels.append(f"LT2 ({lt2_load:.2f})")

    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.50, 0.05),
        ncol=len(handles),
        frameon=False,
        fontsize=9.5,
    )

    zone_ax = fig.add_axes([0.89, 0.24, 0.10, 0.54])
    zone_ax.axis("off")

    for i, (name, low, high, color) in enumerate(reversed(zones)):
        y = 0.82 - i * 0.17
        zone_ax.add_patch(
            Rectangle(
                (0.05, y),
                0.20,
                0.12,
                facecolor=color,
                edgecolor="none",
            )
        )
        zone_ax.text(
            0.32,
            y + 0.06,
            f"{name}\n{round_half_up(low)}-{round_half_up(high)} bpm",
            va="center",
            fontsize=9,
        )

    for spine in ax.spines.values():
        spine.set_color("#666666")
        spine.set_linewidth(0.8)

    for spine in ax2.spines.values():
        spine.set_visible(False)

    out = BytesIO()
    fig.savefig(out, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    return out.getvalue(), threshold_hr


def make_lactate_graph(points: list[dict]) -> bytes:
    _set_korean_font()

    visible = [
        p
        for p in points
        if p.get("lactate") is not None and np.isfinite(float(p["lactate"]))
    ]

    if not visible:
        raise ValueError("표시할 혈중 젖산염 데이터가 없습니다.")

    labels = [str(p["label"]) for p in visible]
    values = [float(p["lactate"]) for p in visible]
    x = np.arange(len(values))

    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=150)

    ax.plot(
        x,
        values,
        marker="o",
        markersize=8,
        lw=2.6,
        color=COLOR_LAC,
    )

    for xi, yi in zip(x, values):
        ax.annotate(
            f"{yi:g}",
            (xi, yi),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=12,
            color="#333333",
        )

    ymax = max(values)
    upper = max(2, math.ceil((ymax + 0.5) / 2) * 2)

    ax.set_ylim(0, upper)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_xlabel("Speed (km/h)", fontsize=16, labelpad=16)
    ax.set_ylabel("혈중 젖산염 (mmol/L)", fontsize=16, labelpad=14)

    ax.grid(axis="y", color="#D9D9D9", linewidth=1)
    ax.grid(False, axis="x")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="both", length=0, colors="#555555")

    out = BytesIO()
    fig.savefig(out, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    return out.getvalue()


def _lactate_x_for_stage(segments: list[Segment], stage_label: str, load_value: float | None) -> float | None:
    label = str(stage_label).strip()
    if label.lower() == "rest":
        return None

    exercise = [seg for seg in segments if not seg.is_rest and seg.load is not None]
    if not exercise:
        return None

    if label.upper() == "AO":
        return exercise[-1].right

    if load_value is not None:
        for seg in exercise:
            if abs(float(seg.load) - float(load_value)) < 1e-9:
                return seg.right

    for seg in exercise:
        if str(seg.label).strip() == label:
            return seg.right

    return None


def make_hr_vo2_lactate_graph(
    df: pd.DataFrame,
    segments: list[Segment],
    hrmax: float,
    lactate_points: list[dict],
    lt1_load: float | None = None,
    lt2_load: float | None = None,
) -> tuple[bytes, dict[str, float | None]]:
    _set_korean_font()

    fig, ax = plt.subplots(figsize=(15.8, 8.8), dpi=150)
    fig.subplots_adjust(left=0.08, right=0.82, bottom=0.18, top=0.91)
    ax2 = ax.twinx()
    ax3 = ax.twinx()
    ax3.set_ylim(0, 15)
    ax3.set_yticks([])
    ax3.tick_params(right=False, labelright=False)
    ax3.spines["right"].set_visible(False)
    ax3.patch.set_visible(False)

    hr_ymin = 50
    hr_ymax = max(
        225,
        math.ceil(max(hrmax, float(df["Heart Rate"].max(skipna=True))) / 25) * 25,
    )
    vo2_ymin = 0
    vo2_ymax = max(
        100,
        math.ceil(float(df["VO2/kg"].max(skipna=True)) / 10) * 10,
    )

    zones = [
        ("Z1", hrmax * 0.50, hrmax * 0.60, "#F4E7A1"),
        ("Z2", hrmax * 0.60, hrmax * 0.70, "#F4D7A0"),
        ("Z3", hrmax * 0.70, hrmax * 0.80, "#F1BD82"),
        ("Z4", hrmax * 0.80, hrmax * 0.90, "#EC9C77"),
        ("Z5", hrmax * 0.90, hrmax * 1.00, "#E77979"),
    ]

    for _, low, high, color in zones:
        ax.axhspan(low, high, color=color, alpha=0.42, zorder=0)

    for seg in segments:
        if seg.is_rest:
            ax.axvspan(seg.left, seg.right, color="#B8B8B8", alpha=0.20, zorder=0)
        ax.axvline(seg.left, color="#BFBFBF", ls="--", lw=0.8, zorder=1)

    ax.axvline(segments[-1].right, color="#BFBFBF", ls="--", lw=0.8, zorder=1)

    ax.plot(df["_x"], df["Heart Rate"], color=COLOR_HR, lw=1.6, zorder=3)
    ax2.plot(df["_x"], df["VO2/kg"], color=COLOR_VO2, lw=1.15, zorder=3)

    for seg in segments:
        ax.text(
            seg.center,
            hr_ymax - 2.5,
            seg.label,
            ha="center",
            va="top",
            fontsize=8.5,
            color="black",
            zorder=5,
        )

    exercise_segments = [seg for seg in segments if not seg.is_rest]

    for seg in exercise_segments:
        group = df.loc[seg.indices]
        cap = max(seg.duration * 0.08, 5)
        hr = group["Heart Rate"].dropna()
        vo2 = group["VO2/kg"].dropna()

        if not hr.empty:
            low, high = float(hr.min()), float(hr.max())
            y0 = min(high + 2, hr_ymax - 26)
            y1 = y0 + 8
            ax.vlines(seg.center, y0, y1, color="black", lw=1.1, zorder=4)
            ax.hlines([y0, y1], seg.center - cap, seg.center + cap, color="black", lw=1.1, zorder=4)
            ax.annotate(
                f"{round_half_up(low)}-{round_half_up(high)}",
                (seg.center, y1),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        if not vo2.empty:
            low, high = float(vo2.min()), float(vo2.max())
            y1 = max(low - 2, vo2_ymin + 16)
            y0 = y1 - 10
            ax2.vlines(seg.center, y0, y1, color=COLOR_VO2, lw=1.1, zorder=4)
            ax2.hlines([y0, y1], seg.center - cap, seg.center + cap, color=COLOR_VO2, lw=1.1, zorder=4)
            ax2.annotate(
                f"{low:.1f}-{high:.1f}",
                (seg.center, y0),
                xytext=(0, -6),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=9,
                color=COLOR_VO2,
                fontstyle="italic",
            )

    lac_x = []
    lac_y = []
    for point in lactate_points:
        x = _lactate_x_for_stage(segments, point.get("label", ""), point.get("load"))
        if x is None:
            continue
        value = point.get("lactate")
        if value is None or not np.isfinite(float(value)):
            continue
        lac_x.append(float(x))
        lac_y.append(float(value))

    if lac_x:
        ax3.plot(lac_x, lac_y, color=COLOR_LAC, lw=1.7, marker="o", markersize=4.5, zorder=6)
        for x, y in zip(lac_x, lac_y):
            ax3.annotate(
                f"{y:.2f}",
                (x, y),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=COLOR_LAC,
                fontsize=8,
                fontweight="bold",
                zorder=7,
                bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor="none", alpha=0.65),
            )

    threshold_hr: dict[str, float | None] = {"LT1": None, "LT2": None}
    for name, load, color in [
        ("LT1", lt1_load, COLOR_LT1),
        ("LT2", lt2_load, COLOR_LT2),
    ]:
        if load is None:
            continue

        x = threshold_x(segments, load)
        hr = hr_at_x(df, x)
        threshold_hr[name] = hr
        ax.axvline(x, color=color, lw=2.0, ls="--", zorder=4)

        label = f"{name} {load:.2f}"
        if hr is not None:
            label += f"\n{round_half_up(hr)} bpm"

        ax.annotate(
            label,
            xy=(x, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=color,
            fontsize=10,
            fontweight="bold",
            annotation_clip=False,
        )

    total_end = segments[-1].right
    ax.set_xlim(0, total_end)
    ax.set_ylim(hr_ymin, hr_ymax)
    ax2.set_ylim(vo2_ymin, vo2_ymax)

    ax.set_ylabel("Heart Rate (bpm)", color=COLOR_HR, fontsize=14)
    ax2.set_ylabel("VO2/kg (ml/kg/min)", color=COLOR_VO2, fontsize=14)
    ax.tick_params(axis="y", colors=COLOR_HR)
    ax2.tick_params(axis="y", colors=COLOR_VO2)

    ticks = list(dict.fromkeys([0.0] + [seg.right for seg in segments]))
    ax.set_xticks(ticks)
    ax.set_xticklabels([fmt_time(t) for t in ticks], fontsize=7)
    ax.set_xlabel("Time (mm:ss)", fontsize=12)
    ax.grid(axis="y", ls="--", lw=0.7, color="#D2D2D2")
    ax.grid(False, axis="x")

    handles = [
        Line2D([0], [0], color=COLOR_HR, lw=1.6),
        Line2D([0], [0], color=COLOR_VO2, lw=1.15),
        Line2D([0], [0], color=COLOR_LAC, lw=1.7, marker="o", markersize=4.5),
    ]
    labels = ["HR (bpm)", "VO2/kg", "Blood Lactate (mmol/L)"]

    if lt1_load is not None:
        handles.append(Line2D([0], [0], color=COLOR_LT1, lw=2, ls="--"))
        labels.append(f"LT1 ({lt1_load:.2f})")
    if lt2_load is not None:
        handles.append(Line2D([0], [0], color=COLOR_LT2, lw=2, ls="--"))
        labels.append(f"LT2 ({lt2_load:.2f})")

    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.50, 0.05),
        ncol=len(handles),
        frameon=False,
        fontsize=8.8,
    )

    zone_ax = fig.add_axes([0.89, 0.24, 0.10, 0.54])
    zone_ax.axis("off")
    for i, (name, low, high, color) in enumerate(reversed(zones)):
        y = 0.82 - i * 0.17
        zone_ax.add_patch(Rectangle((0.05, y), 0.20, 0.12, facecolor=color, edgecolor="none"))
        zone_ax.text(
            0.32,
            y + 0.06,
            f"{name}\n{round_half_up(low)}-{round_half_up(high)} bpm",
            va="center",
            fontsize=9,
        )

    for spine in ax.spines.values():
        spine.set_color("#666666")
        spine.set_linewidth(0.8)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    out = BytesIO()
    fig.savefig(out, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out.getvalue(), threshold_hr
