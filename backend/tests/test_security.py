import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip():
    h = hash_password("demo1234")
    assert h != "demo1234"
    assert verify_password("demo1234", h)
    assert not verify_password("wrong", h)


def test_access_token_round_trip():
    uid = uuid.uuid4()
    token = create_access_token(uid, "patient")
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "patient"


def test_expired_token_rejected():
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "patient", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(expired)


def test_tampered_token_rejected():
    token = create_access_token(uuid.uuid4(), "patient")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token[:-2] + "xx")
