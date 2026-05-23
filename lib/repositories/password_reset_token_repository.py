import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import and_

from lib.models.password_reset_token import PasswordResetToken
from lib.repositories.base import AbstractRepository


class PasswordResetTokenRepository(AbstractRepository[PasswordResetToken]):
    model = PasswordResetToken

    def create_for_user(self, user_id: uuid.UUID, ttl_seconds: int = 900) -> str:
        """Generate a reset token, store its hash, return the raw token."""
        raw = secrets.token_hex(32)
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        with self._factory.session() as s:
            s.add(PasswordResetToken(
                user_id=user_id,
                token_hash=PasswordResetToken.hash_token(raw),
                expires_at=expires,
            ))
        return raw

    def find_valid(self, token: str) -> dict | None:
        """Return token row as dict if valid (not used, not expired). None otherwise."""
        now = datetime.now(timezone.utc)
        token_hash = PasswordResetToken.hash_token(token)
        with self._factory.session() as s:
            row = (
                s.query(PasswordResetToken)
                .filter(
                    and_(
                        PasswordResetToken.token_hash == token_hash,
                        PasswordResetToken.used_at.is_(None),
                        PasswordResetToken.expires_at > now,
                    )
                )
                .first()
            )
            if row is None:
                return None
            return {
                "id": str(row.id),
                "user_id": str(row.user_id),
                "token": token,   # return raw token (only caller has it)
            }

    def mark_used(self, token_id: uuid.UUID) -> bool:
        """Set used_at = now. Returns True if the row existed, False otherwise."""
        with self._factory.session() as s:
            row = s.get(PasswordResetToken, token_id)
            if row is None:
                return False
            row.used_at = datetime.now(timezone.utc)
            return True
