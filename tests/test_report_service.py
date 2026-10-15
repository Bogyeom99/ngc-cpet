from services.report_service import build_report_html


def _report_data():
    return {
        "name": "테스트",
        "sex": "남",
        "category": "국가대표 후보",
        "test_date": "2026.10.15.",
        "height": "180.0",
        "weight": "75.0",
        "bmi": "23.1",
        "vo2max": "60.00",
        "hrmax": 190,
        "exercise_time": "20:00",
        "load_name": "속도",
        "load_unit": "km/h",
        "max_load": "16",
        "grade_percent": "1.0",
        "stages": [],
        "zones": [],
        "lactates": [],
        "lt1": {"show": True},
        "lt2": {"show": True},
        "page1_comment": "1페이지 문구",
        "lactate_comment": "젖산 문구",
        "lt1_comment": "LT1 문구",
        "lt2_comment": "LT2 문구",
    }


def test_editable_report_marks_only_comment_regions():
    html = build_report_html(
        _report_data(),
        b"graph",
        None,
        None,
        editable=True,
    )

    for key in [
        "page1_comment",
        "lactate_comment",
        "lt1_comment",
        "lt2_comment",
    ]:
        assert f'data-edit-key="{key}"' in html

    assert html.count('data-edit-key="') == 4


def test_pdf_report_has_no_editable_attributes():
    html = build_report_html(
        _report_data(),
        b"graph",
        None,
        None,
    )

    assert "data-edit-key=" not in html
    assert 'contenteditable="true"' not in html


def test_colored_text_survives_report_sanitizing():
    data = _report_data()
    data["page1_comment"] = (
        '<span style="color:#D7191C">강조</span> 문구'
    )

    html = build_report_html(
        data,
        b"graph",
        None,
        None,
    )

    assert "color:#D7191C" in html or "color: #D7191C" in html
    assert "강조" in html


def test_report_uses_simplified_typography_scale():
    html = build_report_html(
        _report_data(),
        b"graph",
        None,
        None,
    )

    assert ".main-title {" in html
    assert "font-size: 20pt;" in html
    assert ".section-title {" in html
    assert "font-size: 12pt;" in html
    assert ".section-right {" in html
    assert "font-size: 9pt;" in html
    assert ".stage-table {" in html
    assert ".editable-text {" in html
    assert "line-height: 1.55;" in html
    assert html.count("font-size: 10pt;") >= 6


def test_report_heading_and_measure_table_typography():
    html = build_report_html(
        _report_data(),
        b"graph",
        None,
        None,
    )

    assert ".section-title {" in html
    assert ".hr-title {" in html
    assert ".page2-heading {" in html
    assert ".lt-title {" in html
    assert html.count("font-size: 12pt;") >= 5
    assert ".info-table .info-label {" in html
    assert "font-size: 10pt;" in html
    assert ".info-table td:not(.info-label) {" in html
    assert "font-size: 9pt;" in html
    assert ".measure-table .info-label {" in html
    assert "white-space: nowrap;" in html
    assert '<col style="width:36%">' in html
    assert '<col style="width:32%">' in html
