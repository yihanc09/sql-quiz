"""Vercel entrypoint, HTTPS, and stateless-session regressions; no network needed."""

import io
import json
import threading
import time
import tomllib
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from cryptography.fernet import Fernet

import sql_quiz.web as web
import sql_quiz.web_sessions as sessions
@pytest.fixture
def vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("APP_SESSION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(web, "SESSIONS", {})
    return monkeypatch


def request(path, data=None, cookie="", origin="https://quiz.example.com"):
    instance = web.Handler.__new__(web.Handler)
    instance.path = path
    body = json.dumps(data or {}).encode()
    instance.headers = {"Host": "quiz.example.com", "Origin": origin,
                        "Content-Type": "application/json", "Content-Length": str(len(body)),
                        "Cookie": cookie}
    instance.rfile = io.BytesIO(body)
    instance.reply = Mock()
    return instance


def test_configured_entrypoint_is_an_http_handler():
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    assert config["tool"]["vercel"]["entrypoint"] == "web_server:handler"
    assert issubclass(web.handler, BaseHTTPRequestHandler)
    import web_server
    assert web_server.handler is web.handler
    assert (root / "frontend/index.html").is_file()
    assert (root / "data/schema.json").is_file()


@pytest.mark.parametrize("storage_failure", [False, True])
def test_login_cookie_restores_on_another_instance_and_refreshes_tokens(vercel, storage_failure):
    user = SimpleNamespace(id="student", email="student@example.com")
    initial = SimpleNamespace(access_token="first-access", refresh_token="first-refresh")
    current = SimpleNamespace(access_token="refreshed-access", refresh_token="refreshed-refresh")
    client = Mock()
    client.auth.get_user.return_value.user = user
    client.auth.get_session.return_value = initial
    vercel.setattr(web, "sign_in", Mock(return_value=SimpleNamespace(user=user, session=initial)))
    vercel.setattr(web, "get_supabase_client", Mock(return_value=client))
    vercel.setattr(web, "load_answer_records", Mock(return_value={}, side_effect=RuntimeError("storage unavailable") if storage_failure else None))
    login = request("/api/login", {"email": user.email, "password": "test-password"})
    login.do_POST()
    status, body, cookie = login.reply.call_args.args
    assert status == 200 and body["user"] == {"email": user.email} and body["records"] == {}
    assert ("warning" in body) == storage_failure
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=Strict" in cookie
    assert "first-access" not in cookie and "first-refresh" not in cookie
    assert not web.SESSIONS

    # A new request has no local session memory and uses a new Supabase client.
    other_client = Mock()
    other_client.auth.get_session.return_value = current
    other_client.auth.get_user.return_value.user = user
    vercel.setattr(web, "get_supabase_client", Mock(return_value=other_client))
    restored = request("/api/session", cookie=cookie.split(";", 1)[0])
    restored.do_GET()
    assert restored.reply.call_args.args[0] == 200
    other_client.auth.set_session.assert_called_once_with("first-access", "first-refresh")
    refreshed = sessions.decode_session(restored._session_cookie.split(";", 1)[0].split("=", 1)[1])
    original = sessions.decode_session(cookie.split(";", 1)[0].split("=", 1)[1])
    assert refreshed["access_token"] == "refreshed-access"
    assert refreshed["expires"] == original["expires"]
    assert not web.SESSIONS


@pytest.mark.parametrize("origin,expected", [
    ("https://quiz.example.com", 401),
    ("http://quiz.example.com", 403),
    ("https://attacker.example.com", 403),
])
def test_deployed_https_origin_validation(vercel, origin, expected):
    instance = request("/api/run", {"question_id": 1, "sql": "SELECT 1"}, origin=origin)
    instance.do_POST()
    assert instance.reply.call_args.args[0] == expected


def test_missing_session_key_returns_actionable_configuration_error(vercel):
    vercel.delenv("APP_SESSION_KEY")
    vercel.setattr(sessions, "get_setting", Mock(side_effect=ValueError("Private settings unavailable")))
    login = Mock()
    vercel.setattr(web, "sign_in", login)
    instance = request("/api/login", {"email": "student@example.com", "password": "test"})
    instance.do_POST()
    assert instance.reply.call_args.args[0] == 503
    assert "-m scripts.configure_runtime --init" in instance.reply.call_args.args[1]["error"]
    login.assert_not_called()


def test_tampered_and_wrong_key_cookies_are_rejected(vercel):
    token = sessions.encode_session("access", "refresh")
    index = len(token) // 2
    tampered = token[:index] + ("A" if token[index] != "A" else "B") + token[index+1:]
    assert sessions.decode_session(tampered) is None
    vercel.setenv("APP_SESSION_KEY", Fernet.generate_key().decode())
    assert sessions.decode_session(token) is None


def test_expired_cookie_and_expired_encryption_timestamp_are_rejected(vercel):
    token = sessions.encode_session("access", "refresh", expires=int(time.time())-1)
    assert sessions.decode_session(token) is None
    payload = {"access_token": "access", "refresh_token": "refresh", "expires": int(time.time())+100}
    old = sessions.session_cipher().encrypt_at_time(
        json.dumps(payload).encode(), int(time.time()) - sessions.SESSION_TTL - 10
    ).decode()
    assert sessions.decode_session(old) is None


def test_refreshed_cookie_is_sent_with_normal_api_responses(vercel):
    instance = request("/api/session")
    instance._session_cookie = "quiz_session=encrypted; Secure; HttpOnly"
    instance.send_response = Mock()
    instance.send_header = Mock()
    instance.end_headers = Mock()
    instance.wfile = io.BytesIO()
    web.Handler.reply(instance, 200, {"user": {"email": "student@example.com"}})
    instance.send_header.assert_any_call("Set-Cookie", instance._session_cookie)


def test_vercel_logout_clears_secure_cookie(vercel):
    client = Mock()
    client.auth.get_user.return_value.user = SimpleNamespace(id="student")
    instance = request("/api/logout", {})
    instance.session = Mock(return_value=(None, {"client": client, "lock": threading.Lock()}))
    instance.do_POST()
    assert instance.reply.call_args.args[0] == 200
    cookie = instance.reply.call_args.args[2]
    assert "Max-Age=0" in cookie and "Secure" in cookie
    client.auth.sign_out.assert_called_once()
