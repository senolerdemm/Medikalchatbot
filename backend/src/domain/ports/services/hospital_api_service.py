from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from domain.entities.appointment import AppointmentBooking, AppointmentSlot


class HospitalAPIService(ABC):
    @abstractmethod
    async def get_available_slots(
        self,
        *,
        specialty: str,
        preferred_date: date | None = None,
        hospital_name: str | None = None,
        limit: int = 5,
    ) -> list[AppointmentSlot]:
        raise NotImplementedError

    @abstractmethod
    async def create_booking(
        self,
        *,
        patient_id: str,
        slot_id: str,
    ) -> AppointmentBooking:
        raise NotImplementedError
