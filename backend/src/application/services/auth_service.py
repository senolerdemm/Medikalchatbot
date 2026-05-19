from __future__ import annotations

from domain.entities.patient import PatientAccount, UserSession
from domain.ports.repositories.auth_repository import AuthRepository


class AuthService:
    def __init__(self, auth_repository: AuthRepository):
        self.auth_repository = auth_repository

    async def login(self, email: str, password: str) -> UserSession | None:
        user = await self.auth_repository.authenticate(email, password)
        if user is None:
            return None
        return await self.auth_repository.create_session(user)

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
    ) -> UserSession:
        user = await self.auth_repository.create_user(
            email=email,
            password=password,
            full_name=full_name,
        )
        return await self.auth_repository.create_session(user)

    async def get_current_user(self, token: str) -> PatientAccount | None:
        return await self.auth_repository.get_user_by_session_token(token)

    async def logout(self, token: str) -> None:
        await self.auth_repository.revoke_session(token)
