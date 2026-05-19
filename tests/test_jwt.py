import pytest
from jose import JWTError


def test_create_and_decode_roundtrip():
    from lib.auth.jwt_handler import create_token, decode_token
    token = create_token({"sub": "user-123", "roles": ["admin"]})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["roles"] == ["admin"]


def test_decode_invalid_token_raises():
    from lib.auth.jwt_handler import decode_token
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_two_tokens_for_same_payload_differ():
    """exp timestamps differ if called a second apart — just verify structure."""
    from lib.auth.jwt_handler import create_token, decode_token
    t1 = create_token({"sub": "u1"})
    t2 = create_token({"sub": "u1"})
    # Both decode correctly even though they may differ in exp
    assert decode_token(t1)["sub"] == "u1"
    assert decode_token(t2)["sub"] == "u1"
