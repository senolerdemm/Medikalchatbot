from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from domain.entities.appointment import AppointmentBooking, AppointmentSlot
from domain.ports.services.hospital_api_service import HospitalAPIService


class HospitalMockAPI(HospitalAPIService):
    def __init__(self) -> None:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self._slots = [
            AppointmentSlot(
                slot_id="slot-001",
                hospital_name="Sehir Hastanesi",
                physician_name="Dr. Ayse Demir",
                specialty="Dahiliye",
                start_at=now + timedelta(days=1, hours=2),
            ),
            AppointmentSlot(
                slot_id="slot-002",
                hospital_name="Universite Hastanesi",
                physician_name="Dr. Mehmet Kaya",
                specialty="Kardiyoloji",
                start_at=now + timedelta(days=2, hours=4),
            ),
            AppointmentSlot(
                slot_id="slot-003",
                hospital_name="Sehir Hastanesi",
                physician_name="Dr. Elif Yildiz",
                specialty="Dermatoloji",
                start_at=now + timedelta(days=3, hours=1),
            ),
        ]
        self._bookings: dict[str, AppointmentBooking] = {}

    async def get_available_slots(
        self,
        *,
        specialty: str,
        preferred_date: date | None = None,
        hospital_name: str | None = None,
        limit: int = 5,
    ) -> list[AppointmentSlot]:
        matching_slots = [
            slot
            for slot in self._slots
            if slot.matches(specialty=specialty, preferred_date=preferred_date)
            and (not hospital_name or hospital_name.lower() in slot.hospital_name.lower())
        ]
        return matching_slots[:limit]

    async def create_booking(
        self,
        *,
        patient_id: str,
        slot_id: str,
    ) -> AppointmentBooking:
        slot = next(slot for slot in self._slots if slot.slot_id == slot_id)
        booking = AppointmentBooking(patient_id=patient_id, slot=slot)
        booking.confirm()
        self._bookings[booking.booking_id] = booking
        return booking
