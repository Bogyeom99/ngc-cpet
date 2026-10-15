def test_service_import_contract():
    from services import excel_parser
    from services import graph_service
    from services import input_template
    from services import report_editor
    from services import report_service

    for name in [
        "parse_excel",
        "round_half_up",
        "is_rest",
        "is_recovery",
        "is_allout",
        "parse_load",
    ]:
        assert hasattr(excel_parser, name)

    assert hasattr(graph_service, "make_hr_vo2_graph")
    assert hasattr(graph_service, "make_hr_vo2_lactate_graph")
    assert hasattr(input_template, "build_input_template")
    assert hasattr(report_service, "build_report_html")
    assert hasattr(report_editor, "render_report_editor")
