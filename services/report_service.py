from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "assets" / "center_logo.png"


def _img_data(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def _logo_data() -> str:
    if not LOGO_PATH.exists():
        return ""
    return _img_data(LOGO_PATH.read_bytes())


def build_report_html(data: dict, basic_graph: bytes, lactate_graph: bytes | None, combined_graph: bytes | None) -> str:
    stages = data.get("stages", [])
    lactates = data.get("lactates", [])
    zones = data.get("zones", [])

    stage_count = max(len(stages), 1)
    table_body_height_mm = 64.0
    stage_row_height_mm = table_body_height_mm / stage_count
    zone_row_height_mm = table_body_height_mm / 5.0
    stage_font_pt = max(7.4, min(9.5, 9.8 - max(stage_count - 7, 0) * 0.28))

    stage_rows = "".join(
        f"<tr><td>{s['stage']}</td><td>{s['hr_range']}</td><td>{s['hr_mean']}</td><td>{s['zone']}</td></tr>"
        for s in stages
    )
    zone_rows = "".join(
        f"<tr><td>{z['name']}</td><td>{z['pct']}</td><td>{z['range']}</td></tr>"
        for z in zones
    )

    visible_lactates = [p for p in lactates if p.get("lactate") is not None]
    lactate_cells = "".join(f"<th>{p['label']}</th>" for p in visible_lactates)
    lactate_values = "".join(f"<td>{float(p['lactate']):.2f}</td>" for p in visible_lactates)

    lt_blocks = ""
    for key in ("lt1", "lt2"):
        item = data.get(key)
        if not item or not item.get("show"):
            continue

        if item.get("valid"):
            lt_blocks += f"""
            <section class="lt-block">
              <h3>{item['name']} 분석 결과</h3>
              <p>{item['name']} 지점은 <strong>{item['load']:.2f} {data['load_unit']}</strong>로 산출되었습니다.
              HR 그래프와 역치선의 교차 지점은 약 <strong>{item['hr']} bpm</strong>이며,
              최대심박수 대비 약 <strong>{item['pct_hrmax']:.0f}%</strong>입니다.</p>
            </section>
            """
        else:
            lt_blocks += (
                f"<section class='lt-block'><h3>{item['name']} 분석 결과</h3>"
                f"<p>산출 불가: {item['reason']}</p></section>"
            )

    lactate_img = (
        f"<img class='lactate-graph' src='{_img_data(lactate_graph)}'>"
        if lactate_graph
        else ""
    )
    combined_img = (
        f"<img class='combined-graph' src='{_img_data(combined_graph)}'>"
        if combined_graph
        else ""
    )

    logo_src = _logo_data()
    logo_html = f"<img class='page-logo' src='{logo_src}'>" if logo_src else ""

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4 portrait; margin: 8mm; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: 'Noto Sans CJK KR', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  color: #111;
  font-size: 9.6pt;
}}
.page {{
  width: 194mm;
  height: 281mm;
  page-break-after: always;
  overflow: hidden;
  padding: 0 2mm 1mm;
  display: flex;
  flex-direction: column;
}}
.page:last-child {{ page-break-after: auto; }}
.brand-row {{
  height: 9mm;
  flex: 0 0 9mm;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}}
.page-logo {{
  width: 94mm;
  max-height: 7.2mm;
  object-fit: contain;
  object-position: right center;
}}
h1 {{
  font-size: 19pt;
  text-align: center;
  margin: 0 0 1.5mm;
  line-height: 1.15;
  color: #14376b;
}}
h2 {{
  font-size: 11.3pt;
  margin: 1.5mm 0 0.7mm;
  border-bottom: 1.2px solid #111;
  padding-bottom: 0.6mm;
  line-height: 1.1;
}}
h3 {{ font-size: 10.5pt; margin: 1mm 0; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
th, td {{
  border: 0.7px solid #555;
  padding: 0.8mm 0.8mm;
  text-align: center;
  vertical-align: middle;
  line-height: 1.12;
}}
th {{ background: #f2f2f2; font-weight: 700; }}
.info {{ flex: 0 0 auto; }}
.info td {{ height: 7.2mm; }}
.info td.label {{ background: #f2f2f2; font-weight: 700; width: 14%; }}
.hr-table-area {{
  height: 72mm;
  flex: 0 0 72mm;
  display: grid;
  grid-template-columns: 1.55fr 1fr;
  gap: 2mm;
  align-items: stretch;
}}
.hr-table-area table {{ height: 72mm; }}
.hr-table-area thead tr {{ height: 8mm; }}
.stage-table {{ font-size: {stage_font_pt:.2f}pt; }}
.stage-table tbody tr {{ height: {stage_row_height_mm:.3f}mm; }}
.zone-table tbody tr {{ height: {zone_row_height_mm:.3f}mm; }}
.graph-wrap {{
  flex: 1 1 auto;
  min-height: 0;
  margin-top: 1.3mm;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
}}
.hr-graph {{
  width: 100%;
  height: 100%;
  max-height: 106mm;
  object-fit: contain;
  object-position: center bottom;
}}
.page-2 h2 {{ margin-top: 1.2mm; }}
.lactate-table th, .lactate-table td {{
  padding: 1.8mm 0.7mm;
  font-size: 8.8pt;
}}
.lactate-graph {{
  width: 100%;
  height: 68mm;
  object-fit: contain;
  margin: 1.2mm 0 0.5mm;
}}
.combined-graph {{
  width: 100%;
  height: 82mm;
  object-fit: contain;
  margin: 0.8mm 0 0.5mm;
}}
.lt-block {{ border-top: 1px solid #555; padding-top: 1.5mm; margin-top: 1.5mm; }}
.lt-block p {{ margin: 0.7mm 0; line-height: 1.48; }}
</style>
</head>
<body>
<section class="page page-1">
  <div class="brand-row">{logo_html}</div>
  <h1>차세대스포츠과학지원센터 체력측정 결과</h1>

  <h2>선수 정보</h2>
  <table class="info">
    <tr>
      <td class="label">이름</td><td>{data['name']}</td>
      <td class="label">성별</td><td>{data['sex']}</td>
      <td class="label">구분</td><td>{data['category']}</td>
      <td class="label">측정날짜</td><td>{data['test_date']}</td>
    </tr>
  </table>

  <h2>선수 체격 및 신체조성</h2>
  <table class="info">
    <tr>
      <td class="label">신장(cm)</td><td>{data['height']}</td>
      <td class="label">체중(kg)</td><td>{data['weight']}</td>
      <td class="label">BMI(kg/m²)</td><td>{data['bmi']}</td>
    </tr>
  </table>

  <h2 style="display:flex; justify-content:space-between; align-items:flex-end;">
    <span>운동 부하 검사 – KISS Protocol</span>
    <span style="font-size:8.8pt; font-weight:400;">* 경사도 {data['grade_percent']}% 고정</span>
  </h2>
  <table class="info">
    <tr>
      <td class="label">최대 산소 섭취량</td><td>{data['vo2max']}</td>
      <td class="label">최대 심박수</td><td>{data['hrmax']}</td>
      <td class="label">운동 시간</td><td>{data['exercise_time']}</td>
      <td class="label">최대 {data['load_name']}</td><td>{data['max_load']} {data['load_unit']}</td>
    </tr>
  </table>

  <h2>심박수(beats/min)</h2>
  <div class="hr-table-area">
    <table class="stage-table">
      <thead><tr><th>Stage</th><th>HR range</th><th>HR mean</th><th>주요 Zone</th></tr></thead>
      <tbody>{stage_rows}</tbody>
    </table>
    <table class="zone-table">
      <thead><tr><th>Zone</th><th>%HRmax</th><th>HR range</th></tr></thead>
      <tbody>{zone_rows}</tbody>
    </table>
  </div>

  <div class="graph-wrap"><img class="hr-graph" src="{_img_data(basic_graph)}"></div>
</section>

<section class="page page-2">
  <div class="brand-row">{logo_html}</div>
  <h2>혈중 젖산염(mmol/L)</h2>
  <table class="lactate-table">
    <tr>{lactate_cells}</tr>
    <tr>{lactate_values}</tr>
  </table>
  {lactate_img}
  {combined_img}
  {lt_blocks}
</section>
</body>
</html>"""


def html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML

    output = BytesIO()
    HTML(string=html, base_url=str(ROOT)).write_pdf(output)
    return output.getvalue()
