from streamlit.testing.v1 import AppTest


def test_streamlit_app_starts_without_uncaught_exception():
    app = AppTest.from_file("streamlit_app.py")
    app.run(timeout=60)
    assert not app.exception
