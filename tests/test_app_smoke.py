from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_streamlit_app_starts_without_uncaught_exception():
    app = AppTest.from_file(APP_PATH)
    app.run(timeout=60)
    assert not app.exception
