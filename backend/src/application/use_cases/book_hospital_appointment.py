from __future__ import annotations

from datetime import date

from application.services.appointment_service import AppointmentService


class BookHospitalAppointmentUseCase:
    def __init__(self, appointment_service: AppointmentService):
        self.appointment_service = appointment_service

    async def execute(
        self,
        *,
        patient_id: str,
        specialty: str,
        preferred_date: date | None = None,
        hospital_name: str | None = None,
        city: str | None = None,
    ) -> dict[str, object]:
        slots = await self.appointment_service.search_slots(
            specialty=specialty,
            city=city,
            preferred_date=preferred_date,
            hospital_name=hospital_name,
        )
        if not slots:
            return {
                "message": (
                    f"{specialty.title()} için uygun randevu bulunamadı. "
                    "Lütfen farklı tarih veya hastane deneyin."
                ),
                "booking": None,
                "suggested_slots": [],
            }

        booking = await self.appointment_service.book_slot(
            patient_id=patient_id,
            slot_id=slots[0].slot_id,
            city=slots[0].city,
        )
        return {
            "message": booking.confirmation_message(),
            "booking": booking,
            "suggested_slots": slots[:3],
        }
