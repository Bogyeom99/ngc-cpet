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



def test_lactate_table_stays_within_page_width():
    data = _report_data()
    data["lactates"] = [
        {"label": "Rest", "lactate": 1.56},
        {"label": "5.4", "lactate": 1.50},
        {"label": "7.2", "lactate": 1.61},
        {"label": "9", "lactate": 1.52},
        {"label": "10.8", "lactate": 1.61},
        {"label": "12.6", "lactate": 2.11},
        {"label": "14.4", "lactate": 3.14},
        {"label": "16.2", "lactate": 6.00},
        {"label": "18", "lactate": 10.09},
        {"label": "AO", "lactate": 10.15},
        {"label": "Recovery 5min", "lactate": 9.34},
    ]

    html = build_report_html(
        data,
        b"graph",
        b"lactate",
        b"combined",
    )

    assert "<th>AO</th>" in html
    assert "<th>Rec 5</th>" in html
    assert "table-layout: fixed;" in html
    assert "width: 100%;" in html
    assert "white-space: nowrap;" in html



def test_report_can_hide_athlete_and_body_sections():
    data = _report_data()
    data["show_athlete_info"] = False
    data["show_body_info"] = False

    html = build_report_html(
        data,
        b"graph",
        None,
        None,
    )

    assert '<span class="title-chip">선수 정보</span>' not in html
    assert '<span class="title-chip">선수 체격 및 신체조성</span>' not in html
    assert '<span class="title-chip">운동 부하 검사 - KISS Protocol</span>' in html


def test_report_info_sections_default_to_visible():
    html = build_report_html(
        _report_data(),
        b"graph",
        None,
        None,
    )

    assert '<span class="title-chip">선수 정보</span>' in html
    assert '<span class="title-chip">선수 체격 및 신체조성</span>' in html



def test_report_can_hide_title_and_header_sections():
    data = _report_data()
    data["show_report_title"] = False
    data["show_athlete_info"] = False
    data["show_body_info"] = False

    html = build_report_html(
        data,
        b"graph",
        None,
        None,
    )

    assert "차세대스포츠과학지원센터 체력측정 결과" not in html
    assert '<span class="title-chip">선수 정보</span>' not in html
    assert '<span class="title-chip">선수 체격 및 신체조성</span>' not in html
    assert '<span class="title-chip">운동 부하 검사 - KISS Protocol</span>' in html


def test_report_title_defaults_to_visible():
    html = build_report_html(
        _report_data(),
        b"graph",
        None,
        None,
    )

    assert "차세대스포츠과학지원센터 체력측정 결과" in html
