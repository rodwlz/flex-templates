import uuid


def _str_uuids(d: dict) -> dict:
    """Stringify any uuid.UUID values in *d* so views get plain strings."""
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in d.items()}
