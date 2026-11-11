import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import Fernet
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("not a usable account password")


def now() -> datetime:
    return datetime.now(UTC)


def random_token() -> str:
    return secrets.token_urlsafe(32)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def canonical_hash(value: Any) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def encrypt_json(value: Any) -> str:
    return (
        Fernet(get_settings().delivery_payload_encryption_key.get_secret_value().encode())
        .encrypt(json.dumps(value).encode())
        .decode()
    )


def decrypt_json(value: str) -> Any:
    return json.loads(
        Fernet(get_settings().delivery_payload_encryption_key.get_secret_value().encode()).decrypt(
            value.encode()
        )
    )
