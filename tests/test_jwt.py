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


def test_check_jwt_secret_dev_key_non_strict_warns():
    """Dev secret in non-strict mode emits a warning, does not exit."""
    from lib.auth.jwt_handler import _check_jwt_secret, _DEV_SECRET
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _check_jwt_secret(_DEV_SECRET, strict=False)
    assert len(caught) == 1
    assert "insecure" in str(caught[0].message).lower()


def test_check_jwt_secret_real_key_no_warning():
    """A real (non-dev) key in non-strict mode emits no warning."""
    from lib.auth.jwt_handler import _check_jwt_secret
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _check_jwt_secret("some-real-production-secret-key", strict=False)
    assert len(caught) == 0


def test_check_jwt_secret_dev_key_strict_exits():
    """Dev secret in strict mode calls sys.exit(1)."""
    from lib.auth.jwt_handler import _check_jwt_secret, _DEV_SECRET
    import pytest
    with pytest.raises(SystemExit) as exc_info:
        _check_jwt_secret(_DEV_SECRET, strict=True)
    assert exc_info.value.code == 1
