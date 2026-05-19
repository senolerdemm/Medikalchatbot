from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


APPOINTMENT_TIMEZONE = ZoneInfo("Europe/Istanbul")


class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"


@dataclass(slots=True)
class AppointmentSlot:
    slot_id: str
    hospital_name: str
    city: str
    physician_name: str
    specialty: str
    start_at: datetime
    is_available: bool = True

    def matches(self, *, specialty: str | None, preferred_date: date | None) -> bool:
        specialty_match = not specialty or specialty.lower() in self.specialty.lower()
        date_match = not preferred_date or self.start_at.astimezone(APPOINTMENT_TIMEZONE).date() == preferred_date
        return self.is_available and specialty_match and date_match

    def as_text(self) -> str:
        local_time = self.start_at.astimezone(APPOINTMENT_TIMEZONE)
        return (
            f"{self.city} / {self.hospital_name} - {self.specialty} - {self.physician_name} - "
            f"{local_time.strftime('%d.%m.%Y %H:%M')}"
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

    def cancel(self) -> None:
        self.status = AppointmentStatus.CANCELLED
        self.slot.is_available = True

    def confirmation_message(self) -> str:
        local_time = self.slot.start_at.astimezone(APPOINTMENT_TIMEZONE)
        return (
            f"Randevu olusturuldu: {self.slot.hospital_name} / "
            f"{self.slot.specialty} / {self.slot.physician_name} / "
            f"{local_time.strftime('%d.%m.%Y %H:%M')}"
        )
