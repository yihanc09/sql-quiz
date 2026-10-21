"""Encrypted, expiring session cookies shared by Vercel function instances."""

import json
import os
import time

from cryptography.fernet import Fernet, InvalidToken
from runtime_config import get_setting

SESSION_TTL = 12 * 60 * 60


def is_vercel():
    return os.getenv("VERCEL") == "1"


def session_cipher():
    key = get_setting("APP_SESSION_KEY")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("APP_SESSION_KEY must be a valid Fernet key.") from exc


def encode_session(access_token, refresh_token, expires=None):
    expires = int(time.time()) + SESSION_TTL if expires is None else expires
    payload = {"access_token": access_token, "refresh_token": refresh_token, "expires": expires}
    token = session_cipher().encrypt(json.dumps(payload).encode()).decode("ascii")
    if len(token) > 3800:
        raise ValueError("Session is too large for a browser cookie.")
    return token


def decode_session(token):
    try:
        payload = json.loads(session_cipher().decrypt(token.encode("ascii"), ttl=SESSION_TTL))
        if not isinstance(payload, dict):
            return None
        expires = payload.get("expires")
        if type(expires) is not int or not time.time() < expires <= time.time() + SESSION_TTL:
            return None
        if not all(isinstance(payload.get(key), str) and payload[key] for key in ("access_token", "refresh_token")):
            return None
        return payload
    except (InvalidToken, ValueError, TypeError, UnicodeError):
        return None
