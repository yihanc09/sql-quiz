"""API contract tests without external accounts or database writes."""
import io
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

import web_server as web


@pytest.fixture
def api_request(monkeypatch):
    monkeypatch.setattr(web, "SESSIONS", {})
    client = Mock()
    client.auth.get_user.return_value.user = SimpleNamespace(id="student", email="student@example.com")
    web.SESSIONS["test"] = {"client": client, "expires": time.time() + 60, "lock": threading.Lock()}
    monkeypatch.setattr(web, "load_answer_records", Mock(return_value={}))
    monkeypatch.setattr(web, "record_query_event", Mock())
    monkeypatch.setattr(web, "save_answer", Mock())
    monkeypatch.setattr(web, "save_graded_answer", Mock())

    def send(path, data=None, authenticated=True, origin="http://localhost:8000"):
        handler = web.Handler.__new__(web.Handler)
        body = json.dumps(data or {}).encode()
        handler.path = path
        handler.headers = {"Content-Type": "application/json", "Content-Length": str(len(body)),
                           "Host": "localhost:8000", "Origin": origin,
                           "Cookie": "quiz_session=test" if authenticated else ""}
        handler.rfile = io.BytesIO(body)
        handler.reply = Mock()
        if data is None:
            handler.do_GET()
        else:
            handler.do_POST()
        return handler.reply.call_args.args
    return send


def test_questions_do_not_expose_reference_sql(api_request):
    status, payload = api_request("/api/questions")
    assert status == 200 and len(payload["questions"]) == 5
    assert all("expected_sql" not in q for q in payload["questions"])


@pytest.mark.parametrize("action", ["run", "save", "submit"])
def test_authentication_required(api_request, action):
    assert api_request(f"/api/{action}", {"question_id": 1, "sql": "SELECT 1"}, False)[0] == 401


def test_cross_origin_rejected(api_request):
    assert api_request("/api/run", {"sql": "SELECT 1"}, origin="https://example.com")[0] == 403


@pytest.mark.parametrize("sql", ["DELETE FROM chinook.artist", "SELECT 1; SELECT 2"])
def test_unsafe_statements_rejected(api_request, monkeypatch, sql):
    execute = Mock()
    monkeypatch.setattr(web, "run_query", execute)
    assert api_request("/api/run", {"question_id": 1, "sql": sql})[0] == 400
    execute.assert_not_called()


def test_submission_grades_and_persists(api_request, monkeypatch):
    monkeypatch.setattr(web, "run_query", Mock(return_value=pd.DataFrame({"total_artists": [275]})))
    status, payload = api_request("/api/submit", {"question_id": 1, "sql": "SELECT COUNT(*) AS total_artists FROM chinook.artist"})
    assert status == 200 and payload["grade"]["score"] == 4
    assert payload["table"]["data"] == [[275]]
    web.save_graded_answer.assert_called_once()
    assert web.record_query_event.call_args.args[2:4] == ("SUBMIT_QUERY", True)
    assert web.record_query_event.call_args.args[4] == "SELECT COUNT(*) AS total_artists FROM chinook.artist"


def test_save_preserves_unchanged_grade(api_request):
    web.load_answer_records.return_value = {1: {"sql_answer": "SELECT 1", "score": 4}}
    assert api_request("/api/save", {"question_id": 1, "sql": "SELECT 1"})[0] == 200
    web.save_answer.assert_not_called()


def test_save_changed_answer_clears_grade(api_request):
    web.load_answer_records.return_value = {1: {"sql_answer": "SELECT 1", "score": 4}}
    assert api_request("/api/save", {"question_id": 1, "sql": "SELECT 2"})[0] == 200
    web.save_answer.assert_called_once()


def test_failed_execution_audited(api_request, monkeypatch):
    monkeypatch.setattr(web, "run_query", Mock(side_effect=RuntimeError("private connection information")))
    status, payload = api_request("/api/run", {"question_id": 1, "sql": "SELECT 1"})
    assert status == 400 and "private connection" not in payload["error"]
    assert web.record_query_event.call_args.args[2:4] == ("RUN_QUERY", False)
    assert web.record_query_event.call_args.args[4] == "SELECT 1"


def test_logout_clears_local_session(api_request):
    status, _, cookie = api_request("/api/logout", {})
    assert status == 200 and "Max-Age=0" in cookie
    assert not web.SESSIONS
