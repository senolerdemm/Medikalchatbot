from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    UNAVAILABLE = "unavailable"


@dataclass(slots=True)
class AppointmentSlot:
    slot_id: str
    hospital_name: str
    physician_name: str
    specialty: str
    start_at: datetime
    is_available: bool = True

    def matches(self, *, specialty: str | None, preferred_date: date | None) -> bool:
        specialty_match = not specialty or specialty.lower() in self.specialty.lower()
        date_match = not preferred_date or self.start_at.date() == preferred_date
        return self.is_available and specialty_match and date_match

    def as_text(self) -> str:
        local_time = self.start_at.astimezone(timezone.utc)
        return (
            f"{self.hospital_name} - {self.specialty} - {self.physician_name} - "
            f"{local_time.strftime('%d.%m.%Y %H:%M UTC')}"
        )


@dataclass(slots=True)
class AppointmentBooking:
    patient_id: str
    slot: AppointmentSlot
    status: AppointmentStatus = AppointmentStatus.PENDING
    booking_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    def confirm(self) -> None:
        self.status = AppointmentStatus.CONFIRMED
        self.slot.is_available = False

    def confirmation_message(self) -> str:
        return (
            f"Randevu olusturuldu: {self.slot.hospital_name} / "
            f"{self.slot.specialty} / {self.slot.physician_name} / "
            f"{self.slot.start_at.strftime('%d.%m.%Y %H:%M')}"
        )
