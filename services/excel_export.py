from __future__ import annotations

from io import BytesIO
import html
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill("solid", fgColor="D9E2F3")
SECTION_FILL = PatternFill("solid", fgColor="EAF0F8")


def _plain_text(value: str) -> str:
    value = value or ""
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</p>\s*<p[^>]*>", "\n", value)
    value = re.sub(r"(?s)<[^>]+>", "", value)
    return html.unescape(value).strip()


def _section(sheet, row: int, title: str, end_col: int = 2) -> None:
    sheet.merge_cells(
        start_row=row,
        start_column=1,
        end_row=row,
        end_column=end_col,
    )
    cell = sheet.cell(row=row, column=1, value=title)
    cell.font = Font(bold=True)
    cell.fill = SECTION_FILL
    cell.alignment = Alignment(vertical="center")
    sheet.row_dimensions[row].height = 22


def _pair(sheet, row: int, label: str, value) -> None:
    sheet.cell(row=row, column=1, value=label)
    sheet.cell(row=row, column=2, value=value)


def _header(sheet, row: int, values: list[str]) -> None:
    for col, value in enumerate(values, start=1):
        cell = sheet.cell(row=row, column=col, value=value)
        cell.font = Font(bold=True)
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )


def _finish_sheet(sheet) -> None:
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    for col_idx in range(1, sheet.max_column + 1):
        max_len = 0
        for cell in sheet[get_column_letter(col_idx)]:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))
        sheet.column_dimensions[get_column_letter(col_idx)].width = min(
            max(max_len + 2, 11),
            45,
        )


def build_excel_export(
    report_data: dict,
    stage_summary,
    lactate_points: list[dict],
    lt1,
    lt2,
) -> bytes:
    wb = Workbook()

    # 1. 선수 정보와 체격
    ws = wb.active
    ws.title = "선수정보"

    _section(ws, 1, "선수 정보")
    _pair(ws, 2, "측정날짜", report_data.get("test_date", ""))
    _pair(ws, 3, "이름", report_data.get("name", ""))
    _pair(ws, 4, "성별", report_data.get("sex", ""))
    _pair(ws, 5, "구분", report_data.get("category", ""))

    _section(ws, 7, "선수 체격 및 신체조성")
    _pair(ws, 8, "신장(cm)", report_data.get("height", ""))
    _pair(ws, 9, "체중(kg)", report_data.get("weight", ""))
    _pair(ws, 10, "BMI(kg/m²)", report_data.get("bmi", ""))

    # 2. 운동 부하 검사
    ws2 = wb.create_sheet("운동부하검사")

    _section(ws2, 1, "운동 부하 검사", 3)
    _pair(ws2, 2, "최대 산소 섭취량(ml/kg/min)", report_data.get("vo2max", ""))
    _pair(ws2, 3, "최대 심박수(beats/min)", report_data.get("hrmax", ""))
    _pair(ws2, 4, "운동 시간", report_data.get("exercise_time", ""))
    _pair(
        ws2,
        5,
        f"최대 {report_data.get('load_name', '')}({report_data.get('load_unit', '')})",
        report_data.get("max_load", ""),
    )
    _pair(ws2, 6, "경사도(%)", report_data.get("grade_percent", ""))
    _pair(ws2, 7, "부하 단위", report_data.get("load_unit", ""))

    _section(ws2, 9, "스테이지별 결과", 9)
    stage_headers = [
        "Stage",
        f"Load({report_data.get('load_unit', '')})",
        "운동시간(초)",
        "HR 최소",
        "HR 최대",
        "HR 평균",
        "VO2 최소",
        "VO2 최대",
        "VO2 평균",
    ]
    _header(ws2, 10, stage_headers)

    source_cols = [
        "Stage",
        "Load",
        "Duration_sec",
        "HR_min",
        "HR_max",
        "HR_mean",
        "VO2_min",
        "VO2_max",
        "VO2_mean",
    ]
    for out_row, (_, row) in enumerate(stage_summary.iterrows(), start=11):
        for col, source in enumerate(source_cols, start=1):
            ws2.cell(row=out_row, column=col, value=row.get(source, ""))

    # 3. 혈중 젖산염과 LT
    ws3 = wb.create_sheet("젖산_LT")

    _section(ws3, 1, "혈중 젖산염", 4)
    _header(ws3, 2, ["Stage", f"Load({report_data.get('load_unit', '')})", "Lactate(mmol/L)", "비고"])

    row_no = 3
    for point in lactate_points:
        ws3.cell(row=row_no, column=1, value=point.get("label", ""))
        ws3.cell(row=row_no, column=2, value=point.get("load", ""))
        ws3.cell(row=row_no, column=3, value=point.get("lactate", ""))
        row_no += 1

    row_no += 1
    _section(ws3, row_no, "LT 결과", 5)
    row_no += 1
    _header(ws3, row_no, ["구분", "산출 여부", f"부하({report_data.get('load_unit', '')})", "심박수(bpm)", "%HRmax"])
    row_no += 1

    report_lt = {
        "LT1": report_data.get("lt1", {}),
        "LT2": report_data.get("lt2", {}),
    }

    for name, result in [("LT1", lt1), ("LT2", lt2)]:
        display = report_lt.get(name, {})
        if result is None:
            values = [name, "미선택", "", "", ""]
        elif result.valid:
            values = [
                name,
                "산출",
                result.threshold_load,
                display.get("hr", ""),
                display.get("pct_hrmax", ""),
            ]
        else:
            values = [name, "산출 불가", "", "", result.reason or ""]

        for col, value in enumerate(values, start=1):
            ws3.cell(row=row_no, column=col, value=value)
        row_no += 1

    # 4. 결과지에서 직접 편집한 문구
    ws4 = wb.create_sheet("평가문구")
    _section(ws4, 1, "결과지 평가 문구")
    text_rows = [
        ("1페이지 평가 문구", _plain_text(report_data.get("page1_comment", ""))),
        ("젖산 평가 문구", _plain_text(report_data.get("lactate_comment", ""))),
        ("LT1 분석 문구", _plain_text(report_data.get("lt1_comment", ""))),
        ("LT2 분석 문구", _plain_text(report_data.get("lt2_comment", ""))),
    ]
    for row_idx, item in enumerate(text_rows, start=2):
        _pair(ws4, row_idx, item[0], item[1])

    for sheet in wb.worksheets:
        _finish_sheet(sheet)

    ws.freeze_panes = "A2"
    ws2.freeze_panes = "A10"
    ws3.freeze_panes = "A2"
    ws4.column_dimensions["B"].width = 100

    output = BytesIO()
    wb.save(output)
    return output.getvalue()
