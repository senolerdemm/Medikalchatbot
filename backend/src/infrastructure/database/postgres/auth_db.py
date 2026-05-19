from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from core.config import get_settings
from domain.entities.patient import PatientAccount, UserSession
from domain.ports.repositories.auth_repository import AuthRepository
from infrastructure.database.postgres.base import session_scope
from infrastructure.database.postgres.models import UserModel, UserSessionModel


def _hash_password(raw_password: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        b"medical-chatbot-demo",
        120_000,
    )
    return digest.hex()


def _hash_token(token: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


class PostgresAuthRepository(AuthRepository):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def authenticate(self, email: str, password: str) -> PatientAccount | None:
        with session_scope() as session:
            user = session.scalar(select(UserModel).where(UserModel.username == email))
            if user is None:
                return None
            if not hmac.compare_digest(user.password_hash, _hash_password(password)):
                return None
            return PatientAccount(
                patient_id=user.id,
                email=user.username,
                full_name=user.full_name,
            )

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
    ) -> PatientAccount:
        with session_scope() as session:
            existing = session.scalar(select(UserModel).where(UserModel.username == email))
            if existing is not None:
                raise ValueError("Bu e-posta zaten kayıtlı.")
            user = UserModel(
                username=email,
                password_hash=_hash_password(password),
                full_name=full_name,
            )
            session.add(user)
            session.flush()
            return PatientAccount(
                patient_id=user.id,
                email=user.username,
                full_name=user.full_name,
            )

    async def create_session(self, user: PatientAccount) -> UserSession:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.settings.session_ttl_hours)
        with session_scope() as session:
            session.add(
                UserSessionModel(
                    user_id=user.patient_id,
                    token_hash=_hash_token(token, self.settings.session_secret),
                    expires_at=expires_at,
                )
            )
        return UserSession(token=token, patient=user, expires_at=expires_at)

    async def get_user_by_session_token(self, token: str) -> PatientAccount | None:
        token_hash = _hash_token(token, self.settings.session_secret)
        with session_scope() as session:
            user_session = session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.token_hash == token_hash,
                    UserSessionModel.revoked_at.is_(None),
                    UserSessionModel.expires_at > datetime.now(timezone.utc),
                )
            )
            if user_session is None:
                return None
            user = session.get(UserModel, user_session.user_id)
            if user is None:
                return None
            return PatientAccount(
                patient_id=user.id,
                email=user.username,
                full_name=user.full_name,
            )

    async def revoke_session(self, token: str) -> None:
        token_hash = _hash_token(token, self.settings.session_secret)
        with session_scope() as session:
            user_session = session.scalar(
                select(UserSessionModel).where(UserSessionModel.token_hash == token_hash)
            )
            if user_session is not None:
                user_session.revoked_at = datetime.now(timezone.utc)


def hash_demo_password(password: str) -> str:
    return _hash_password(password)
