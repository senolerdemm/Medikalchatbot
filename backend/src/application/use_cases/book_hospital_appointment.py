from __future__ import annotations

from datetime import date

from domain.entities.appointment import AppointmentBooking, AppointmentSlot
from domain.ports.services.hospital_api_service import HospitalAPIService


class BookHospitalAppointmentUseCase:
    def __init__(self, hospital_api: HospitalAPIService):
        self.hospital_api = hospital_api

    async def execute(
        self,
        *,
        patient_id: str,
        specialty: str,
        preferred_date: date | None = None,
        hospital_name: str | None = None,
    ) -> dict[str, object]:
        slots = await self.hospital_api.get_available_slots(
            specialty=specialty,
            preferred_date=preferred_date,
            hospital_name=hospital_name,
        )
        if not slots:
            return {
                "message": (
                    f"{specialty.title()} icin uygun randevu bulunamadi. "
                    "Lutfen farkli tarih veya hastane deneyin."
                ),
                "booking": None,
                "suggested_slots": [],
            }

        booking = await self.hospital_api.create_booking(
            patient_id=patient_id,
            slot_id=slots[0].slot_id,
        )
        return {
            "message": booking.confirmation_message(),
            "booking": booking,
            "suggested_slots": slots[:3],
        }
