from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from services.excel_export import build_excel_export
from services.excel_parser import parse_excel, round_half_up
from services.graph_service import make_hr_vo2_graph, make_hr_vo2_lactate_graph, make_lactate_graph
from services.lt_analysis import LactatePoint, estimate_lt
from services.report_service import build_report_html, html_to_pdf


st.set_page_config(page_title="NGC CPET", layout="wide")
st.title("NGC CPET 피드백지 제작")
st.caption("운동부하검사 Excel 자료와 혈중 젖산염 값을 이용해 결과지를 생성합니다.")
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: #ffffff !important;
        color: #111111 !important;
    }
    [data-testid="stAppViewContainer"] * {
        color-scheme: light !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "athletes" not in st.session_state:
    st.session_state.athletes = []

if "parsed" not in st.session_state:
    st.session_state.parsed = None


def zone_for_hr(hr: float, hrmax: float) -> str:
    ratio = hr / hrmax if hrmax else 0

    if ratio < 0.60:
        return "Z1"
    if ratio < 0.70:
        return "Z2"
    if ratio < 0.80:
        return "Z3"
    if ratio < 0.90:
        return "Z4"
    return "Z5"


def format_duration(sec: float) -> str:
    sec = int(round(sec))
    minutes, seconds = divmod(sec, 60)
    return f"{minutes:02d}:{seconds:02d}"


tab1, tab2, tab3, tab4 = st.tabs(
    ["1 선수 등록", "2 검사 입력", "3 분석", "4 결과지"]
)


with tab1:
    with st.form("athlete_form"):
        c1, c2, c3 = st.columns(3)

        name = c1.text_input("선수 이름")
        sex = c2.selectbox("성별", ["남", "여"])
        category = c3.selectbox(
            "구분",
            ["국가대표 후보", "청소년 대표", "꿈나무"],
        )

        submitted = st.form_submit_button(
            "선수 등록",
            use_container_width=True,
        )

        if submitted:
            if not name.strip():
                st.error("선수 이름을 입력하세요.")
            else:
                st.session_state.athletes.append(
                    {
                        "name": name.strip(),
                        "sex": sex,
                        "category": category,
                    }
                )
                st.success(f"{name.strip()} 선수를 등록했습니다.")

    if st.session_state.athletes:
        st.dataframe(
            pd.DataFrame(st.session_state.athletes),
            use_container_width=True,
            hide_index=True,
        )


with tab2:
    if not st.session_state.athletes:
        st.info("먼저 선수 등록 탭에서 선수를 등록하세요.")
    else:
        athlete_names = [a["name"] for a in st.session_state.athletes]
        selected_name = st.selectbox("선수 선택", athlete_names)
        athlete = next(
            a
            for a in st.session_state.athletes
            if a["name"] == selected_name
        )

        c1, c2, c3, c4 = st.columns(4)

        test_date = c1.date_input(
            "측정 날짜",
            dt.date.today(),
        )
        height = c2.number_input(
            "신장(cm)",
            min_value=0.0,
            step=0.1,
        )
        weight = c3.number_input(
            "체중(kg)",
            min_value=0.0,
            step=0.1,
        )
        bmi = c4.number_input(
            "BMI(kg/m²)",
            min_value=0.0,
            step=0.1,
        )

        c1, c2, c3, c4 = st.columns(4)

        vo2max = c1.number_input(
            "최대 산소 섭취량(ml/kg/min)",
            min_value=0.0,
            step=0.01,
        )
        hrmax = c2.number_input(
            "최대 심박수(beats/min)",
            min_value=0,
            step=1,
        )
        exercise_time = c3.text_input(
            "운동 시간",
            placeholder="예: 30분",
        )
        load_type = c4.radio(
            "부하 단위",
            ["Speed", "Power"],
            horizontal=True,
        )

        load_unit = "km/h" if load_type == "Speed" else "watt"

        c1, c2 = st.columns(2)
        max_load = c1.number_input(
            f"최대 {load_type}({load_unit})",
            min_value=0.0,
            step=0.1,
        )
        grade_percent = c2.number_input(
            "경사도(%)",
            min_value=0.0,
            step=0.1,
            format="%.1f",
        )

        c1, c2 = st.columns(2)

        show_lt1 = c1.checkbox(
            "LT1 계산 및 표시",
            value=True,
        )
        show_lt2 = c2.checkbox(
            "LT2 계산 및 표시",
            value=True,
        )

        uploaded = st.file_uploader(
            "Excel 파일 업로드",
            type=["xlsx", "xlsm"],
        )

        if uploaded is not None:
            try:
                df, segments, summary = parse_excel(uploaded)

                st.session_state.parsed = {
                    "df": df,
                    "segments": segments,
                    "summary": summary,
                }

                st.success("Data 시트를 읽었습니다.")

                display_summary = summary.copy()
                display_summary["Duration"] = display_summary[
                    "Duration_sec"
                ].map(format_duration)

                st.dataframe(
                    display_summary[
                        [
                            "Stage",
                            "Duration",
                            "HR_min",
                            "HR_max",
                            "HR_mean",
                            "VO2_min",
                            "VO2_max",
                            "VO2_mean",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            except Exception as exc:
                st.session_state.parsed = None
                st.error(str(exc))

        st.session_state.test_meta = {
            "athlete": athlete,
            "test_date": test_date,
            "height": height,
            "weight": weight,
            "bmi": bmi,
            "vo2max": vo2max,
            "hrmax": hrmax,
            "exercise_time": exercise_time,
            "load_type": load_type,
            "load_unit": load_unit,
            "max_load": max_load,
            "grade_percent": grade_percent,
            "show_lt1": show_lt1,
            "show_lt2": show_lt2,
        }


with tab3:
    parsed = st.session_state.parsed
    meta = st.session_state.get("test_meta")

    if parsed is None or meta is None:
        st.info("검사 입력 탭에서 Excel 파일을 먼저 업로드하세요.")

    else:
        exercise_segments = [
            segment
            for segment in parsed["segments"]
            if not segment.is_rest
        ]

        stage_rows = []

        for i, segment in enumerate(exercise_segments):
            label = (
                "AO"
                if i == len(exercise_segments) - 1
                else segment.label
            )

            stage_rows.append(
                {
                    "Stage": label,
                    "Load": segment.load,
                    "Lactate": None,
                }
            )

        rest_default = pd.DataFrame(
            [
                {
                    "Stage": "rest",
                    "Load": np.nan,
                    "Lactate": None,
                }
            ]
            + stage_rows
        )

        st.subheader("혈중 젖산염 입력")
        st.info("아래 표의 혈중 젖산염 열에 측정된 수치를 입력하세요. 미측정 구간은 비워두면 됩니다.")

        edited = st.data_editor(
            rest_default,
            hide_index=True,
            use_container_width=True,
            disabled=["Stage", "Load"],
            column_config={
                "Lactate": st.column_config.NumberColumn(
                    "혈중 젖산염(mmol/L)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                )
            },
            key="lactate_editor",
        )

        chart_points = []
        lt_points = []

        for _, row in edited.iterrows():
            lactate = row["Lactate"]

            if pd.isna(lactate):
                continue

            chart_points.append(
                {
                    "label": row["Stage"],
                    "load": (
                        None
                        if pd.isna(row["Load"])
                        else float(row["Load"])
                    ),
                    "lactate": float(lactate),
                }
            )

            if (
                row["Stage"] != "rest"
                and not pd.isna(row["Load"])
            ):
                lt_points.append(
                    LactatePoint(
                        label=str(row["Stage"]),
                        load=float(row["Load"]),
                        lactate=float(lactate),
                    )
                )

        lt1, lt2 = estimate_lt(
            lt_points,
            meta["show_lt1"],
            meta["show_lt2"],
        )

        if chart_points:
            lactate_png = make_lactate_graph(chart_points)
            st.image(
                lactate_png,
                use_container_width=True,
            )
        else:
            lactate_png = None
            st.info(
                "혈중 젖산염 값을 하나 이상 입력하면 "
                "그래프가 표시됩니다."
            )

        lt1_load = (
            lt1.threshold_load
            if lt1 and lt1.valid
            else None
        )
        lt2_load = (
            lt2.threshold_load
            if lt2 and lt2.valid
            else None
        )

        if meta["hrmax"] > 0:
            basic_png, _ = make_hr_vo2_graph(
                parsed["df"],
                parsed["segments"],
                meta["hrmax"],
                None,
                None,
            )

            combined_analysis_png, threshold_hr = make_hr_vo2_lactate_graph(
                parsed["df"],
                parsed["segments"],
                meta["hrmax"],
                chart_points,
                lt1_load,
                lt2_load,
                lt_label_mode="analysis",
            )

            combined_report_png, _ = make_hr_vo2_lactate_graph(
                parsed["df"],
                parsed["segments"],
                meta["hrmax"],
                chart_points,
                lt1_load,
                lt2_load,
                lt_label_mode="report",
            )

            if meta["show_lt1"]:
                if lt1 and lt1.valid:
                    hr = threshold_hr.get("LT1")
                    hr_text = f" | {round_half_up(hr)} bpm" if hr is not None else ""
                    st.success(
                        f"LT1 = {lt1.threshold_load:.2f} "
                        f"{meta['load_unit']}{hr_text}"
                    )
                else:
                    st.warning(
                        "LT1 산출 불가: "
                        f"{lt1.reason if lt1 else '계산 결과 없음'}"
                    )

            if meta["show_lt2"]:
                if lt2 and lt2.valid:
                    hr = threshold_hr.get("LT2")
                    hr_text = f" | {round_half_up(hr)} bpm" if hr is not None else ""
                    st.success(
                        f"LT2 = {lt2.threshold_load:.2f} "
                        f"{meta['load_unit']}{hr_text}"
                    )
                else:
                    st.warning(
                        "LT2 산출 불가: "
                        f"{lt2.reason if lt2 else '계산 결과 없음'}"
                    )

            st.markdown("#### 1페이지용 HR 및 VO2 그래프")
            st.image(
                basic_png,
                use_container_width=True,
            )

            st.markdown("#### 2페이지용 HR, VO2 및 Lactate 그래프")
            st.image(
                combined_analysis_png,
                use_container_width=True,
            )

        else:
            basic_png = None
            combined_analysis_png = None
            combined_report_png = None
            threshold_hr = {
                "LT1": None,
                "LT2": None,
            }
            st.warning(
                "최대 심박수를 입력하면 "
                "HR 및 VO2 그래프를 생성할 수 있습니다."
            )

        st.session_state.analysis = {
            "lt1": lt1,
            "lt2": lt2,
            "chart_points": chart_points,
            "basic_png": basic_png,
            "combined_analysis_png": combined_analysis_png,
            "combined_report_png": combined_report_png,
            "lactate_png": lactate_png,
            "threshold_hr": threshold_hr,
        }


with tab4:
    parsed = st.session_state.parsed
    meta = st.session_state.get("test_meta")
    analysis = st.session_state.get("analysis")

    if (
        parsed is None
        or meta is None
        or analysis is None
        or analysis.get("basic_png") is None
        or analysis.get("combined_report_png") is None
    ):
        st.info(
            "분석 탭에서 그래프와 LT 결과를 "
            "먼저 생성하세요."
        )

    else:
        summary = parsed["summary"]
        stages = []

        for _, row in summary.iterrows():
            hr_mean = float(row["HR_mean"])

            stages.append(
                {
                    "stage": row["Stage"],
                    "hr_range": (
                        f"{round_half_up(row['HR_min'])}-"
                        f"{round_half_up(row['HR_max'])}"
                    ),
                    "hr_mean": round_half_up(hr_mean),
                    "zone": zone_for_hr(
                        hr_mean,
                        meta["hrmax"],
                    ),
                }
            )

        zones = []

        for idx, (low, high) in enumerate(
            [
                (0.50, 0.60),
                (0.60, 0.70),
                (0.70, 0.80),
                (0.80, 0.90),
                (0.90, 1.00),
            ],
            start=1,
        ):
            zones.append(
                {
                    "name": f"Zone {idx}",
                    "pct": (
                        f"{int(low * 100)}-"
                        f"{int(high * 100)}"
                    ),
                    "range": (
                        f"{round_half_up(meta['hrmax'] * low)}-"
                        f"{round_half_up(meta['hrmax'] * high)}"
                    ),
                }
            )

        def lt_report_item(result, key):
            if not result:
                return {
                    "name": key,
                    "show": False,
                }

            hr = analysis["threshold_hr"].get(key)

            if result.valid and hr is not None:
                return {
                    "name": key,
                    "show": True,
                    "valid": True,
                    "load": result.threshold_load,
                    "hr": round_half_up(hr),
                    "pct_hrmax": (
                        hr / meta["hrmax"] * 100
                    ),
                }

            return {
                "name": key,
                "show": True,
                "valid": False,
                "reason": (
                    result.reason
                    or "산출 불가"
                ),
            }

        report_data = {
            "name": meta["athlete"]["name"],
            "sex": meta["athlete"]["sex"],
            "category": meta["athlete"]["category"],
            "test_date": meta["test_date"].isoformat(),
            "height": f"{meta['height']:.1f}",
            "weight": f"{meta['weight']:.1f}",
            "bmi": f"{meta['bmi']:.1f}",
            "vo2max": f"{meta['vo2max']:.2f}",
            "hrmax": meta["hrmax"],
            "exercise_time": meta["exercise_time"],
            "load_name": (
                "속도"
                if meta["load_type"] == "Speed"
                else "파워"
            ),
            "load_unit": meta["load_unit"],
            "max_load": f"{meta['max_load']:g}",
            "grade_percent": f"{meta['grade_percent']:.1f}",
            "stages": stages,
            "zones": zones,
            "lactates": analysis["chart_points"],
            "lt1": lt_report_item(
                analysis["lt1"],
                "LT1",
            ),
            "lt2": lt_report_item(
                analysis["lt2"],
                "LT2",
            ),
        }

        html = build_report_html(
            report_data,
            analysis["basic_png"],
            analysis["lactate_png"],
            analysis["combined_report_png"],
        )

        components.html(
            html,
            height=1500,
            scrolling=True,
        )

        st.download_button(
            "HTML 결과지 받기",
            html.encode("utf-8"),
            file_name=(
                f"{meta['test_date']}_"
                f"{meta['athlete']['name']}_피드백.html"
            ),
            mime="text/html",
            use_container_width=True,
        )

        try:
            pdf = html_to_pdf(html)

            st.download_button(
                "PDF 결과지 받기",
                pdf,
                file_name=(
                    f"{meta['test_date']}_"
                    f"{meta['athlete']['name']}_피드백.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
            )

        except Exception as exc:
            st.warning(
                "PDF 생성 환경을 확인해야 합니다: "
                f"{exc}"
            )
