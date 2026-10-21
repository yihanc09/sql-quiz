"""Local web frontend for the existing SQL quiz. Run with: python web_server.py."""

import argparse
import json
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from auth import (get_supabase_client, sign_in, sign_up, load_answer_records,
                  save_answer, save_graded_answer, record_query_event)
from database import run_query
from grading import grade_result
from quiz import get_questions, get_total_points
from web_sessions import SESSION_TTL, is_vercel, session_cipher, encode_session, decode_session
from runtime_config import RuntimeConfigError

ROOT = Path(__file__).resolve().parent / "frontend"
QUESTIONS = {q["id"]: q for q in get_questions()}
SESSIONS = {}
SESSION_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Never log submitted SQL, credentials, or URL parameters.
        super().log_message("%s %s", self.command, urlparse(self.path).path)

    def reply(self, status, data, cookie=None):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.headers_common("application/json; charset=utf-8")
        cookie = cookie or getattr(self, "_session_cookie", None)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def headers_common(self, content_type):
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

    def session(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None, None
        sid = cookie.get("quiz_session")
        sid = sid.value if sid else None
        if is_vercel():
            if not sid:
                return None, None
            payload = decode_session(sid)
            if payload is None:
                return None, None
            try:
                # Reconstruct an isolated Supabase client on any function instance.
                # set_session refreshes an expired access token when necessary.
                client = get_supabase_client()
                client.auth.set_session(payload["access_token"], payload["refresh_token"])
                current = client.auth.get_session()
                if not current:
                    return None, None
                self._session_cookie = self.encrypted_cookie(current, payload["expires"])
                return None, {"client": client, "expires": payload["expires"], "lock": threading.Lock()}
            except Exception:
                return None, None
        with SESSION_LOCK:
            expired = [key for key, value in SESSIONS.items() if value["expires"] < time.time()]
            for key in expired:
                SESSIONS.pop(key, None)
            return sid, SESSIONS.get(sid)

    def encrypted_cookie(self, session, expires=None):
        expires = int(time.time()) + SESSION_TTL if expires is None else expires
        token = encode_session(session.access_token, session.refresh_token, expires)
        return f"quiz_session={token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age={max(0, int(expires - time.time()))}"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/questions":
            return self.reply(200, {"questions": [{k: v for k, v in q.items() if k != "expected_sql"} for q in QUESTIONS.values()], "total": get_total_points()})
        if path == "/api/session":
            _, session = self.session()
            if not session:
                return self.reply(200, {"user": None})
            try:
                with session["lock"]:
                    user = session["client"].auth.get_user().user
                    records = load_answer_records(session["client"], user.id)
                return self.reply(200, {"user": {"email": user.email}, "records": records})
            except Exception:
                return self.reply(401, {"error": "Your session could not be verified. Please sign in again."})
        files = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                 "/app.js": ("app.js", "text/javascript; charset=utf-8")}
        if path not in files:
            return self.reply(404, {"error": "Not found."})
        name, content_type = files[path]
        body = (ROOT / name).read_bytes()
        self.send_response(200)
        self.headers_common(content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Trust the deployed HTTPS scheme, not a caller-supplied proxy header.
        origin = self.headers.get("Origin")
        scheme = "https" if is_vercel() else "http"
        if origin and origin != f"{scheme}://{self.headers.get('Host')}":
            return self.reply(403, {"error": "Cross-origin request rejected."})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.reply(415, {"error": "JSON required."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, TypeError):
            return self.reply(400, {"error": "Invalid request."})
        path = urlparse(self.path).path
        if path in ("/api/login", "/api/signup"):
            if is_vercel():
                try:
                    session_cipher()
                except ValueError:
                    return self.reply(503, {"error": "Private server settings are unavailable. Check DATABASE_URL / DATABASE_PASSWORD and run configure_runtime.py --init once from the configured local checkout."})
            email, password = data.get("email", ""), data.get("password", "")
            if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password:
                return self.reply(400, {"error": "Enter your email and password."})
            try:
                if path == "/api/signup":
                    sign_up(email.strip(), password)
                    return self.reply(200, {"message": "Check your email to confirm your account, then sign in."})
                response = sign_in(email.strip(), password)
                if not response.user or not response.session:
                    return self.reply(401, {"error": "Please confirm your email before signing in."})
                client = get_supabase_client()
                client.auth.set_session(response.session.access_token, response.session.refresh_token)
                records = load_answer_records(client, response.user.id)
                if is_vercel():
                    return self.reply(200, {"user": {"email": response.user.email}, "records": records},
                                      self.encrypted_cookie(client.auth.get_session()))
                sid = secrets.token_urlsafe(32)
                old_sid, _ = self.session()
                with SESSION_LOCK:
                    SESSIONS.pop(old_sid, None)
                    SESSIONS[sid] = {"client": client, "expires": time.time() + SESSION_TTL, "lock": threading.Lock()}
                return self.reply(200, {"user": {"email": response.user.email}, "records": records},
                                  f"quiz_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}")
            except RuntimeConfigError as exc:
                return self.reply(503, {"error": str(exc)})
            except Exception:
                return self.reply(400, {"error": "Unable to sign in or create your account. Check your credentials, email confirmation, and Supabase connection."})
        sid, session = self.session()
        if not session:
            return self.reply(401, {"error": "Please sign in to continue."})
        with session["lock"]:
            try:
                client = session["client"]
                user = client.auth.get_user().user
                if not user:
                    raise ValueError()
            except Exception:
                return self.reply(401, {"error": "Your session has expired. Please sign in again."})
            if path == "/api/logout":
                try:
                    client.auth.sign_out()
                except Exception:
                    pass
                with SESSION_LOCK:
                    SESSIONS.pop(sid, None)
                secure = " Secure;" if is_vercel() else ""
                return self.reply(200, {"ok": True}, f"quiz_session=; HttpOnly;{secure} SameSite=Strict; Path=/; Max-Age=0")
            if path not in ("/api/save", "/api/run", "/api/submit"):
                return self.reply(404, {"error": "Not found."})
            qid, sql = data.get("question_id"), data.get("sql", "")
            if type(qid) is not int or qid not in QUESTIONS or not isinstance(sql, str) or not sql.strip():
                return self.reply(400, {"error": "Select a valid question and enter a SQL query."})
            if path == "/api/save":
                try:
                    previous = load_answer_records(client, user.id).get(qid, {})
                    if previous.get("sql_answer") != sql or previous.get("score") is None:
                        save_answer(client, user.id, qid, sql)
                    return self.reply(200, {"message": "Answer saved.", "records": load_answer_records(client, user.id)})
                except Exception:
                    return self.reply(502, {"error": "Could not save your answer. Your text is still in the editor; please retry."})
            query = sql.strip()
            if not query.lower().startswith(("select ", "select\n", "with ", "with\n")) or query.rstrip(";").count(";"):
                return self.reply(400, {"error": "Only a single SELECT or WITH query is allowed."})
            action = "SUBMIT_QUERY" if path == "/api/submit" else "RUN_QUERY"
            warning = None
            try:
                result = run_query(query)
            except Exception as exc:
                audit_warning = None
                try:
                    record_query_event(client, qid, action, False, sql)
                except Exception:
                    audit_warning = "The failed query could not be recorded in the audit log."
                detail = getattr(getattr(exc, "diag", None), "message_primary", None)
                return self.reply(400, {"error": detail or "Query execution failed. Check your SQL and database connection.", "warning": audit_warning})
            try:
                record_query_event(client, qid, action, True, sql)
            except Exception:
                warning = "Query ran, but its audit event could not be recorded."
            payload = {"table": json.loads(result.to_json(orient="split", date_format="iso")), "warning": warning}
            if path == "/api/submit":
                try:
                    correct, feedback = grade_result(qid, result)
                    points = QUESTIONS[qid]["points"] if correct else 0
                    save_graded_answer(client, user.id, qid, sql, points, correct)
                    payload.update(grade={"is_correct": correct, "score": points, "feedback": feedback}, records=load_answer_records(client, user.id))
                except Exception:
                    return self.reply(502, {"error": "Query ran, but the grade could not be saved. Please submit again.", **payload})
            return self.reply(200, payload)


# Explicit module export for Vercel; importing it never starts a local listener.
handler = Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"SQL Quiz frontend: http://localhost:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
