from __future__ import annotations

import base64
from io import BytesIO


def _img_data(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def build_report_html(data: dict, hr_graph: bytes, lactate_graph: bytes | None) -> str:
    stages = data.get("stages", [])
    lactates = data.get("lactates", [])
    zones = data.get("zones", [])

    stage_rows = "".join(
        f"<tr><td>{s['stage']}</td><td>{s['hr_range']}</td><td>{s['hr_mean']}</td><td>{s['zone']}</td></tr>"
        for s in stages
    )

    zone_rows = "".join(
        f"<tr><td>{z['name']}</td><td>{z['pct']}</td><td>{z['range']}</td></tr>"
        for z in zones
    )

    lactate_cells = "".join(
        f"<th>{p['label']}</th>"
        for p in lactates
        if p.get("lactate") is not None
    )

    lactate_values = "".join(
        f"<td>{float(p['lactate']):.2f}</td>"
        for p in lactates
        if p.get("lactate") is not None
    )

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

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4 portrait; margin: 8mm; }}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  font-family: 'Noto Sans CJK KR', 'Noto Sans KR', sans-serif;
  color: #111;
  font-size: 10pt;
}}

.page {{
  width: 194mm;
  height: 281mm;
  page-break-after: always;
  overflow: hidden;
  padding: 1mm 2mm;
  display: flex;
  flex-direction: column;
}}

.page:last-child {{
  page-break-after: auto;
}}

h1 {{
  font-size: 20pt;
  text-align: center;
  margin: 3mm 0 2mm;
  color: #14376b;
}}

h2 {{
  font-size: 12pt;
  margin: 2mm 0 1mm;
  border-bottom: 1.4px solid #111;
  padding-bottom: 1mm;
}}

h3 {{
  font-size: 11pt;
  margin: 1mm 0;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}}

th, td {{
  border: 0.7px solid #555;
  padding: 1.2mm 1mm;
  text-align: center;
  vertical-align: middle;
}}

th {{
  background: #f2f2f2;
  font-weight: 700;
}}

.info td.label {{
  background: #f2f2f2;
  font-weight: 700;
  width: 14%;
}}

.grid-two {{
  display: grid;
  grid-template-columns: 1.55fr 1fr;
  gap: 2mm;
  min-height: 72mm;
}}

.stage-table tbody tr {{
  height: calc(58mm / max(1, var(--stage-count)));
}}

.graph-wrap {{
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  margin-top: 2mm;
}}

.hr-graph {{
  width: 100%;
  max-height: 112mm;
  object-fit: contain;
}}

.lactate-table th,
.lactate-table td {{
  padding: 2mm 1mm;
}}

.lactate-graph {{
  width: 100%;
  max-height: 112mm;
  object-fit: contain;
  margin: 2mm 0;
}}

.lt-block {{
  border-top: 1px solid #555;
  padding-top: 2mm;
  margin-top: 2mm;
}}

.lt-block p {{
  margin: 1mm 0;
  line-height: 1.55;
}}
</style>
</head>
<body>
<section class="page" style="--stage-count:{max(len(stages), 1)}">
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

  <h2>운동 부하 검사</h2>
  <table class="info">
    <tr>
      <td class="label">최대 산소 섭취량</td><td>{data['vo2max']}</td>
      <td class="label">최대 심박수</td><td>{data['hrmax']}</td>
      <td class="label">운동 시간</td><td>{data['exercise_time']}</td>
      <td class="label">최대 {data['load_name']}</td><td>{data['max_load']} {data['load_unit']}</td>
    </tr>
  </table>

  <h2>심박수(beats/min)</h2>
  <div class="grid-two">
    <table class="stage-table">
      <thead>
        <tr><th>Stage</th><th>HR range</th><th>HR mean</th><th>주요 Zone</th></tr>
      </thead>
      <tbody>{stage_rows}</tbody>
    </table>

    <table>
      <thead>
        <tr><th>Zone</th><th>%HRmax</th><th>HR range</th></tr>
      </thead>
      <tbody>{zone_rows}</tbody>
    </table>
  </div>

  <div class="graph-wrap">
    <img class="hr-graph" src="{_img_data(hr_graph)}">
  </div>
</section>

<section class="page">
  <h2>혈중 젖산염(mmol/L)</h2>
  <table class="lactate-table">
    <tr>{lactate_cells}</tr>
    <tr>{lactate_values}</tr>
  </table>

  {lactate_img}
  {lt_blocks}
</section>
</body>
</html>"""


def html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML

    output = BytesIO()
    HTML(string=html).write_pdf(output)
    return output.getvalue()
