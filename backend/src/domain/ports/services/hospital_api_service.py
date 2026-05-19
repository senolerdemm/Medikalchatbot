from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from domain.entities.appointment import AppointmentBooking, AppointmentSlot


class HospitalAPIService(ABC):
    @abstractmethod
    async def search_slots(
        self,
        *,
        specialty: str,
        city: str | None = None,
        preferred_date: date | None = None,
        preferred_hour: int | None = None,
        hospital_name: str | None = None,
        physician_name: str | None = None,
        limit: int = 5,
    ) -> list[AppointmentSlot]:
        raise NotImplementedError

    @abstractmethod
    async def book_slot(
        self,
        *,
        patient_id: str,
        slot_id: str,
    ) -> AppointmentBooking:
        raise NotImplementedError

    @abstractmethod
    async def cancel_booking(self, *, booking_id: str) -> AppointmentBooking | None:
        raise NotImplementedError

    @abstractmethod
    async def list_patient_bookings(self, *, patient_id: str) -> list[AppointmentBooking]:
        raise NotImplementedError
