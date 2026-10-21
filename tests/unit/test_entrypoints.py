"""Launchers must still locate assets and rerun the UI after packaging."""

import subprocess
import sys

import pytest

from sql_quiz.paths import PROJECT_ROOT


def test_http_launcher_resolves_project_from_another_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'web_server.py'), '--help'],
        cwd=tmp_path, capture_output=True, text=True, timeout=20, check=True,
    )
    assert '--port' in result.stdout


def test_streamlit_launcher_renders_on_each_rerun():
    testing = pytest.importorskip('streamlit.testing.v1')
    app = testing.AppTest.from_file(str(PROJECT_ROOT / 'app.py')).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == 'IDS706 SQL Quiz'
    app.run(timeout=15)
    assert not app.exception
    assert app.title[0].value == 'IDS706 SQL Quiz'
    assert len(app.text_input) == 4
