import json
import os
from typing import Optional, Tuple
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()


class CredentialError(Exception):
    """Key missing/invalid, or a stored token cannot be decrypted."""


def _fernet() -> Fernet:
    key = os.getenv("CAMERA_CRED_KEY")
    if not key:
        raise CredentialError("CAMERA_CRED_KEY is not set in .env")
    try:
        return Fernet(key.encode())
    except ValueError:
        raise CredentialError("CAMERA_CRED_KEY is not a valid Fernet key")


def _host_netloc(parts) -> str:
    host = parts.hostname or ""
    if ":" in host:          # IPv6 needs brackets
        host = f"[{host}]"
    return f"{host}:{parts.port}" if parts.port else host


def split_credentials(url: str) -> Tuple[str, Optional[Tuple[str, str]]]:
    """'rtsp://user:p%40ss@host:554/x' -> ('rtsp://host:554/x', ('user', 'p@ss')).
    A URL without credentials is returned unchanged with None."""
    parts = urlsplit(url)
    if parts.username is None and parts.password is None:
        return url, None
    clean = urlunsplit((parts.scheme, _host_netloc(parts), parts.path,
                        parts.query, parts.fragment))
    return clean, (unquote(parts.username or ""), unquote(parts.password or ""))


def encrypt_credentials(username: str, password: str) -> str:
    payload = json.dumps({"u": username, "p": password})
    return _fernet().encrypt(payload.encode()).decode()


def decrypt_credentials(token: str) -> Tuple[str, str]:
    try:
        data = json.loads(_fernet().decrypt(token.encode()))
    except InvalidToken:
        raise CredentialError(
            "Stored credentials cannot be decrypted (was CAMERA_CRED_KEY changed?)"
        )
    return data["u"], data["p"]


def build_stream_url(source_path: str, token: Optional[str]) -> str:
    """Put the credentials back into the URL. Call ONLY at the moment a stream is
    opened; never store, log or return the result."""
    if not token:
        return source_path
    username, password = decrypt_credentials(token)
    parts = urlsplit(source_path)
    netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{_host_netloc(parts)}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))