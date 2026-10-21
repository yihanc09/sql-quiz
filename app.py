"""Streamlit launcher. Run: python -m streamlit run app.py."""

import runpy

runpy.run_module("sql_quiz.streamlit_app", run_name="__main__")
