from lib.security.password import hash_password, verify_password


def test_hash_password_returns_nonempty_strings():
    hashed, salt = hash_password("mysecret")
    assert hashed and salt
    assert hashed != "mysecret"


def test_verify_password_correct():
    hashed, _ = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True


def test_verify_password_wrong():
    hashed, _ = hash_password("mysecret")
    assert verify_password("wrongpassword", hashed) is False


def test_two_hashes_of_same_password_differ():
    h1, _ = hash_password("pw")
    h2, _ = hash_password("pw")
    assert h1 != h2  # bcrypt generates a unique salt each time
