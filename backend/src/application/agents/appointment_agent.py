from __future__ import annotations

from application.use_cases.book_hospital_appointment import (
    BookHospitalAppointmentUseCase,
)
from domain.entities.health_query import HealthQuery


class AppointmentAgent:
    def __init__(self, book_appointment: BookHospitalAppointmentUseCase):
        self.book_appointment = book_appointment

    async def handle_appointment_request(
        self,
        query: HealthQuery,
    ) -> dict[str, object]:
        specialty = self._extract_specialty(query.text)
        outcome = await self.book_appointment.execute(
            patient_id=query.patient_id,
            specialty=specialty,
        )
        slots = outcome["suggested_slots"]
        slot_descriptions = [slot.as_text() for slot in slots]
        if slot_descriptions:
            suggestion_text = " | Onerilen slotlar: " + " ; ".join(slot_descriptions)
        else:
            suggestion_text = ""
        return {
            "message": f"{outcome['message']}{suggestion_text}",
            "sources": [],
        }

    def _extract_specialty(self, text: str) -> str:
        normalized = text.lower().translate(
            str.maketrans(
                {
                    "ç": "c",
                    "ğ": "g",
                    "ı": "i",
                    "ö": "o",
                    "ş": "s",
                    "ü": "u",
                }
            )
        )
        keyword_map = {
            "kardiyo": "Kardiyoloji",
            "kalp": "Kardiyoloji",
            "cilt": "Dermatoloji",
            "deri": "Dermatoloji",
            "cocuk": "Pediatri",
            "ortopedi": "Ortopedi",
            "psik": "Psikiyatri",
            "noroloji": "Noroloji",
        }
        for keyword, specialty in keyword_map.items():
            if keyword in normalized:
                return specialty
        return "Dahiliye"
