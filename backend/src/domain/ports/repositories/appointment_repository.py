from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.appointment import AppointmentBooking


class AppointmentRepository(ABC):
    @abstractmethod
    async def save_booking(
        self,
        *,
        patient_id: str,
        booking: AppointmentBooking,
        city: str | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_bookings(self, patient_id: str) -> list[AppointmentBooking]:
        raise NotImplementedError

    @abstractmethod
    async def list_reserved_slot_ids(self) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    async def cancel_booking(self, patient_id: str, booking_id: str) -> AppointmentBooking | None:
        raise NotImplementedError
