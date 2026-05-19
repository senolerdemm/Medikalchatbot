from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PatientHistoryEntry:
    entry_type: str
    summary: str
    metadata: dict[str, str] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=utc_now)
    entry_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class PatientAccount:
    patient_id: str
    email: str
    full_name: str


@dataclass(slots=True)
class UserSession:
    token: str
    patient: PatientAccount
    expires_at: datetime


@dataclass(slots=True)
class ConversationMessage:
    role: str
    content: str
    created_at: datetime = field(default_factory=utc_now)
    message_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class PatientProfile:
    patient_id: str
    full_name: str | None = None
    age: int | None = None
    chronic_conditions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    notes: str | None = None
    city: str | None = None
    updated_at: datetime = field(default_factory=utc_now)

    def summary(self) -> str:
        parts: list[str] = []
        if self.age is not None:
            parts.append(f"Yaş: {self.age}")
        if self.chronic_conditions:
            parts.append(
                "Kronik durumlar: " + ", ".join(self.chronic_conditions)
            )
        if self.medications:
            parts.append("İlaçlar: " + ", ".join(self.medications))
        if self.city:
            parts.append(f"Şehir: {self.city}")
        if self.notes:
            parts.append(f"Notlar: {self.notes}")
        return " | ".join(parts) if parts else "Hasta profili henüz oluşturulmadı."

    def add_history_notes(self, notes: Iterable[str]) -> None:
        new_notes = [note.strip() for note in notes if note and note.strip()]
        if not new_notes:
            return
        suffix = "; ".join(new_notes)
        self.notes = f"{self.notes}; {suffix}" if self.notes else suffix
        self.updated_at = utc_now()
