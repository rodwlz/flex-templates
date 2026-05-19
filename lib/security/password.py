import bcrypt


def hash_password(plain: str) -> tuple[str, str]:
    """Hash a plain-text password with bcrypt. Returns (hash, salt) as str."""
    raw_salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), raw_salt)
    return hashed.decode("utf-8"), raw_salt.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
