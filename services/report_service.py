from __future__ import annotations

import base64
import html
from io import BytesIO

import bleach
from bleach.css_sanitizer import CSSSanitizer
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "assets" / "center_logo.png"


def _img_data(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def _logo_data() -> str:
    if not LOGO_PATH.exists():
        return ""
    return _img_data(LOGO_PATH.read_bytes())


def _text_html(value: str) -> str:
    value = value or ""
    if "<" not in value:
        return html.escape(value).replace("\n", "<br>")

    css_sanitizer = CSSSanitizer(
        allowed_css_properties=[
            "color",
            "background-color",
            "font-weight",
            "font-style",
            "text-decoration",
        ]
    )
    return bleach.clean(
        value,
        tags=[
            "p",
            "div",
            "br",
            "span",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "s",
            "font",
        ],
        attributes={
            "span": ["style"],
            "font": ["color"],
        },
        css_sanitizer=css_sanitizer,
        strip=True,
    )


def build_report_html(
    data: dict,
    basic_graph: bytes,
    lactate_graph: bytes | None,
    combined_graph: bytes | None,
    *,
    editable: bool = False,
) -> str:
    stages = data.get("stages", [])
    zones = data.get("zones", [])
    lactates = [p for p in data.get("lactates", []) if p.get("lactate") is not None]

    stage_count = max(len(stages), 1)
    body_height_mm = 80.0
    stage_row_height_mm = body_height_mm / stage_count
    zone_row_height_mm = body_height_mm / 5.0

    zone_colors = {
        "Z1": "#B9E7B6",
        "Z2": "#FFE08A",
        "Z3": "#FFBE45",
        "Z4": "#FF634D",
        "Z5": "#C20F1A",
    }

    stage_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(s['stage']))}</td>"
            f"<td>{html.escape(str(s['hr_range']))}</td>"
            f"<td>{html.escape(str(s['hr_mean']))}</td>"
            "<td class='zone-main'>"
            f"<span class='zone-chip' style='background:{zone_colors.get(s['zone'], '#D9D9D9')}'></span>"
            f"{html.escape(str(s['zone']))}</td>"
            "</tr>"
        )
        for s in stages
    )

    zone_rows = "".join(
        (
            "<tr>"
            "<td class='zone-main'>"
            f"<span class='zone-chip' style='background:{zone_colors.get('Z' + str(i), '#D9D9D9')}'></span>"
            f"{html.escape(str(z['name']))}</td>"
            f"<td>{html.escape(str(z['pct']))}</td>"
            f"<td>{html.escape(str(z['range']))}</td>"
            "</tr>"
        )
        for i, z in enumerate(zones, start=1)
    )

    lactate_headers = "".join(f"<th>{html.escape('All-Out' if str(p['label']) == 'AO' else str(p['label']))}</th>" for p in lactates)
    lactate_values = "".join(f"<td>{float(p['lactate']):.2f}</td>" for p in lactates)

    logo_src = _logo_data()
    logo_html = f"<img class='page-logo' src='{logo_src}'>" if logo_src else ""

    lactate_img = (
        f"<img class='lactate-only-graph' src='{_img_data(lactate_graph)}'>"
        if lactate_graph
        else ""
    )
    combined_img = (
        f"<img class='combined-graph' src='{_img_data(combined_graph)}'>"
        if combined_graph
        else ""
    )

    grade_note = ""
    if str(data.get("load_name", "")) == "속도":
        grade_note = (
            "<strong>* 경사도 "
            + html.escape(str(data.get("grade_percent", "")))
            + "% 고정</strong>"
        )

    def edit_attrs(key: str) -> str:
        if not editable:
            return ""
        return (
            ' contenteditable="true"'
            f' data-edit-key="{html.escape(key)}"'
            ' spellcheck="true"'
        )

    editor_css = ""
    if editable:
        editor_css = """
[data-edit-key][contenteditable="true"] {
  outline: 1.5px dashed #8FB9DF;
  outline-offset: 1.5px;
}
"""

    lt1_block = ""
    if data.get("lt1", {}).get("show"):
        lt1_block = f"""
        <div class="lt-section">
          <div class="lt-title">LT1 분석 결과 (제1젖산역치; 유산소 대사)</div>
          <div class="editable-text"{edit_attrs("lt1_comment")}>{_text_html(data.get("lt1_comment", ""))}</div>
        </div>
        """

    lt2_block = ""
    if data.get("lt2", {}).get("show"):
        lt2_block = f"""
        <div class="lt-section lt2-section">
          <div class="lt-title">LT2 분석 결과 (제2젖산역치; 무산소 대사)</div>
          <div class="editable-text"{edit_attrs("lt2_comment")}>{_text_html(data.get("lt2_comment", ""))}</div>
        </div>
        """

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4 portrait; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
body {{
  font-family: 'Noto Sans CJK KR', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  color: #111;
  font-size: 10pt;
}}
.page {{
  width: 210mm;
  height: 297mm;
  padding: 10mm 24mm 9mm 26mm;
  overflow: hidden;
  page-break-after: always;
  background: #fff;
}}
.page:last-child {{ page-break-after: auto; }}
.page2 {{ padding-top: 8mm; }}
.page-logo {{
  display: block;
  width: 75mm;
  max-height: 9mm;
  object-fit: contain;
  object-position: right center;
}}
.page1-logo {{
  display: flex;
  justify-content: flex-end;
  margin-bottom: 2.2mm;
}}
.main-title {{
  color: #123A79;
  font-size: 20pt;
  font-weight: 800;
  text-align: center;
  line-height: 1.0;
  margin: 0 0 3.0mm 0;
}}
.section-line {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 6mm;
  margin-top: 1.5mm;
  margin-bottom: 1.0mm;
}}
.section-title {{
  font-size: 12pt;
  font-weight: 800;
  line-height: 1;
}}
.section-right {{
  font-size: 9pt;
  line-height: 1;
}}
.data-table {{
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 0;
}}
.data-table th,
.data-table td {{
  border-top: 0.55px solid #4F4F4F;
  border-bottom: 0.55px solid #4F4F4F;
  border-left: 0.45px solid #777;
  border-right: 0.45px solid #777;
  text-align: center;
  vertical-align: middle;
  padding: 0.75mm 0.8mm;
  line-height: 1.10;
}}
.data-table th {{
  background: #F2F2F2;
  font-weight: 700;
}}
.info-table td {{
  height: 6.2mm;
}}
.info-label {{
  background: #F2F2F2;
  font-weight: 700;
}}
.info-table .info-label {{
  font-size: 9pt;
}}
.measure-table {{
  font-size: 10pt;
}}
.measure-table td {{
  height: 7.2mm;
  padding-left: 0.45mm;
  padding-right: 0.45mm;
}}
.measure-table .info-label {{
  white-space: nowrap;
  font-size: 10pt;
}}
.hr-title {{
  font-size: 12pt;
  font-weight: 800;
  margin: 2.6mm 0 1.2mm 0;
  line-height: 1;
}}
.hr-grid {{
  width: 100%;
  height: 92mm;
  display: grid;
  grid-template-columns: 62% 38%;
  gap: 0;
}}
.hr-grid table {{
  width: 100%;
  height: 92mm;
  border-collapse: collapse;
  table-layout: fixed;
}}
.hr-grid th,
.hr-grid td {{
  border: 0.5px solid #555;
  text-align: center;
  vertical-align: middle;
  padding: 0.55mm 0.45mm;
  line-height: 1.05;
}}
.hr-grid th {{
  background: #F2F2F2;
  font-weight: 500;
}}
.hr-grid .group-head {{
  height: 6mm;
  font-size: 10pt;
}}
.hr-grid .col-head {{
  height: 6mm;
  font-size: 10pt;
}}
.stage-table {{
  font-size: 10pt;
}}
.stage-table tbody tr {{
  height: {stage_row_height_mm:.3f}mm;
}}
.zone-table {{
  border-left: 0;
  font-size: 10pt;
}}
.zone-table tbody tr {{
  height: {zone_row_height_mm:.3f}mm;
}}
.zone-main {{
  white-space: nowrap;
}}
.zone-chip {{
  display: inline-block;
  width: 3.2mm;
  height: 3.2mm;
  border-radius: 0.5mm;
  margin-right: 1.6mm;
  vertical-align: -0.45mm;
}}
.basic-graph-box {{
  height: 70mm;
  margin: 4.0mm 0 2.5mm 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}}
.basic-graph {{
  width: 100%;
  height: 100%;
  object-fit: contain;
}}
.page1-comment {{
  height: 24mm;
  padding-top: 1.0mm;
  font-size: 10pt;
  line-height: 1.42;
  overflow: hidden;
}}
.page2-top {{
  height: 10mm;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}}
.page2-heading {{
  font-size: 12pt;
  font-weight: 800;
  line-height: 1;
}}
.page2-logo {{
  margin-left: auto;
}}
.lactate-table {{
  margin-top: 1.5mm;
}}
.lactate-table th,
.lactate-table td {{
  height: 5.2mm;
  font-size: 10pt;
  padding: 0.3mm;
}}
.lactate-graph-box {{
  height: 52mm;
  margin: 6.0mm 0 3.0mm 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}}
.lactate-only-graph {{
  width: 100%;
  height: 100%;
  object-fit: contain;
}}
.lactate-comment {{
  min-height: 25mm;
  max-height: 31mm;
  overflow: hidden;
  border-top: 0.55px solid #555;
  border-bottom: 0.55px solid #555;
  padding: 2.0mm 1.2mm;
  font-size: 10pt;
  line-height: 1.42;
}}
.total-title {{
  height: 6.5mm;
  margin-top: 4.5mm;
  display: flex;
  align-items: center;
  font-size: 12pt;
  font-weight: 800;
  border-bottom: 0.55px solid #555;
}}
.combined-graph-box {{
  height: 73mm;
  margin: 3.0mm 0 2.5mm 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}}
.combined-graph {{
  width: 100%;
  height: 100%;
  object-fit: contain;
}}
.lt-section {{
  border-top: 0.55px solid #555;
  padding-top: 2.0mm;
  margin-top: 2.0mm;
}}
.lt2-section {{
  border-top: none;
  margin-top: 3.0mm;
  padding-top: 0;
}}
.lt-title {{
  font-size: 12pt;
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 0.8mm;
}}
.editable-text {{
  font-size: 10pt;
  line-height: 1.45;
}}
.page1-comment p,
.page1-comment div,
.lactate-comment p,
.lactate-comment div,
.editable-text p,
.editable-text div {{
  margin: 0;
  padding: 0;
}}
.page1-comment span,
.lactate-comment span,
.editable-text span {{
  line-height: inherit;
}}
.page2-bottom-line {{
  margin-top: 1.5mm;
  border-bottom: 0.55px solid #555;
}}
.title-chip {{
  display: inline-block;
  background: #EAF6FF;
  padding: 0.9mm 2.2mm 0.8mm 2.2mm;
  border-radius: 1.2mm;
  line-height: 1;
}}
{editor_css}
</style>
</head>
<body>

<section class="page page1">
  <div class="page1-logo">{logo_html}</div>
  <div class="main-title">차세대스포츠과학지원센터 체력측정 결과</div>

  <div class="section-line">
    <div class="section-title"><span class="title-chip">선수 정보</span></div>
    <div class="section-right"><strong>측정날짜:</strong>&nbsp; {html.escape(str(data['test_date']))}</div>
  </div>
  <table class="data-table info-table">
    <tr>
      <td class="info-label">이름</td><td>{html.escape(str(data['name']))}</td>
      <td class="info-label">성별</td><td>{html.escape(str(data['sex']))}</td>
      <td class="info-label">구분</td><td>{html.escape(str(data['category']))}</td>
    </tr>
  </table>

  <div class="section-line">
    <div class="section-title"><span class="title-chip">선수 체격 및 신체조성</span></div>
  </div>
  <table class="data-table info-table">
    <tr>
      <td class="info-label">신장(cm)</td><td>{html.escape(str(data['height']))}</td>
      <td class="info-label">체중(kg)</td><td>{html.escape(str(data['weight']))}</td>
      <td class="info-label">BMI(kg/m²)</td><td>{html.escape(str(data['bmi']))}</td>
    </tr>
  </table>

  <div class="section-line">
    <div class="section-title"><span class="title-chip">운동 부하 검사 - KISS Protocol</span></div>
    <div class="section-right">{grade_note}</div>
  </div>
  <table class="data-table measure-table">
    <colgroup>
      <col style="width:36%">
      <col style="width:14%">
      <col style="width:32%">
      <col style="width:18%">
    </colgroup>
    <tr>
      <td class="info-label">최대 산소 섭취량(ml/kg/min)</td><td>{html.escape(str(data['vo2max']))}</td>
      <td class="info-label">최대 심박수(beats/min)</td><td>{html.escape(str(data['hrmax']))}</td>
    </tr>
    <tr>
      <td class="info-label">운동 시간</td><td>{html.escape(str(data['exercise_time']))}</td>
      <td class="info-label">최대 {html.escape(str(data['load_name']))}({html.escape(str(data['load_unit']))})</td><td>{html.escape(str(data['max_load']))}</td>
    </tr>
  </table>

  <div class="hr-title"><span class="title-chip">심박수(beats/min)</span></div>
  <div class="hr-grid">
    <table class="stage-table">
      <thead>
        <tr><th class="group-head" colspan="4">스테이지별 HR 범위</th></tr>
        <tr>
          <th class="col-head">{html.escape(str(data.get('load_name', 'Load')))}</th>
          <th class="col-head">HR range</th>
          <th class="col-head">HR mean</th>
          <th class="col-head">주요 Zone</th>
        </tr>
      </thead>
      <tbody>{stage_rows}</tbody>
    </table>
    <table class="zone-table">
      <thead>
        <tr><th class="group-head" colspan="3">Training zone</th></tr>
        <tr>
          <th class="col-head">Zone</th>
          <th class="col-head">%HRmax</th>
          <th class="col-head">HR range</th>
        </tr>
      </thead>
      <tbody>{zone_rows}</tbody>
    </table>
  </div>

  <div class="basic-graph-box">
    <img class="basic-graph" src="{_img_data(basic_graph)}">
  </div>

  <div class="page1-comment"{edit_attrs("page1_comment")}>{_text_html(data.get("page1_comment", ""))}</div>
</section>

<section class="page page2">
  <div class="page2-top">
    <div class="page2-heading"><span class="title-chip">혈중 젖산염(mmol/L)</span></div>
    <div class="page2-logo">{logo_html}</div>
  </div>

  <table class="data-table lactate-table">
    <tr>{lactate_headers}</tr>
    <tr>{lactate_values}</tr>
  </table>

  <div class="lactate-graph-box">{lactate_img}</div>

  <div class="lactate-comment"{edit_attrs("lactate_comment")}>{_text_html(data.get("lactate_comment", ""))}</div>

  <div class="total-title"><span class="title-chip">총평</span></div>

  <div class="combined-graph-box">{combined_img}</div>

  {lt1_block}
  {lt2_block}
  <div class="page2-bottom-line"></div>
</section>

</body>
</html>"""


def html_to_pdf(html_text: str) -> bytes:
    from weasyprint import HTML

    output = BytesIO()
    HTML(string=html_text, base_url=str(ROOT)).write_pdf(output)
    return output.getvalue()
