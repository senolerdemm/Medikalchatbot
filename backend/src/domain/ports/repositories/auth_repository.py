from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.patient import PatientAccount, UserSession


class AuthRepository(ABC):
    @abstractmethod
    async def authenticate(self, email: str, password: str) -> PatientAccount | None:
        raise NotImplementedError

    @abstractmethod
    async def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
    ) -> PatientAccount:
        raise NotImplementedError

    @abstractmethod
    async def create_session(self, user: PatientAccount) -> UserSession:
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_session_token(self, token: str) -> PatientAccount | None:
        raise NotImplementedError

    @abstractmethod
    async def revoke_session(self, token: str) -> None:
        raise NotImplementedError
