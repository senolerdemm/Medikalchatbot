from __future__ import annotations

from uuid import uuid4

from sqlalchemy import asc, select

from domain.entities.appointment import AppointmentBooking, AppointmentSlot, AppointmentStatus
from domain.ports.repositories.appointment_repository import AppointmentRepository
from infrastructure.database.postgres.base import session_scope
from infrastructure.database.postgres.models import AppointmentModel


class PostgresAppointmentRepository(AppointmentRepository):
    async def save_booking(
        self,
        *,
        patient_id: str,
        booking: AppointmentBooking,
        city: str | None = None,
    ) -> None:
        with session_scope() as session:
            existing = session.scalar(
                select(AppointmentModel).where(
                    AppointmentModel.external_booking_id == booking.booking_id
                )
            )
            if existing is None:
                session.add(
                    AppointmentModel(
                        id=str(uuid4()),
                        user_id=patient_id,
                        external_booking_id=booking.booking_id,
                        slot_id=booking.slot.slot_id,
                        hospital_name=booking.slot.hospital_name,
                        city=city or booking.slot.city,
                        physician_name=booking.slot.physician_name,
                        specialty=booking.slot.specialty,
                        start_at=booking.slot.start_at,
                        status=booking.status.value,
                    )
                )
                return

            existing.user_id = patient_id
            existing.slot_id = booking.slot.slot_id
            existing.hospital_name = booking.slot.hospital_name
            existing.city = city or booking.slot.city
            existing.physician_name = booking.slot.physician_name
            existing.specialty = booking.slot.specialty
            existing.start_at = booking.slot.start_at
            existing.status = booking.status.value

    async def list_bookings(self, patient_id: str) -> list[AppointmentBooking]:
        with session_scope() as session:
            rows = session.scalars(
                select(AppointmentModel)
                .where(AppointmentModel.user_id == patient_id)
                .order_by(asc(AppointmentModel.start_at))
            ).all()
            return [
                AppointmentBooking(
                    patient_id=patient_id,
                    booking_id=row.external_booking_id,
                    slot=AppointmentSlot(
                        slot_id=row.slot_id,
                        hospital_name=row.hospital_name,
                        city=row.city or "Bilinmiyor",
                        physician_name=row.physician_name,
                        specialty=row.specialty,
                        start_at=row.start_at,
                        is_available=row.status != AppointmentStatus.CONFIRMED.value,
                    ),
                    status=AppointmentStatus(row.status),
                )
                for row in rows
            ]

    async def list_reserved_slot_ids(self) -> set[str]:
        with session_scope() as session:
            rows = session.scalars(
                select(AppointmentModel.slot_id).where(
                    AppointmentModel.status == AppointmentStatus.CONFIRMED.value
                )
            ).all()
            return set(rows)

    async def cancel_booking(self, patient_id: str, booking_id: str) -> AppointmentBooking | None:
        with session_scope() as session:
            row = session.scalar(
                select(AppointmentModel).where(
                    AppointmentModel.user_id == patient_id,
                    AppointmentModel.external_booking_id == booking_id,
                )
            )
            if row is None:
                return None
            row.status = AppointmentStatus.CANCELLED.value
            return AppointmentBooking(
                patient_id=patient_id,
                booking_id=row.external_booking_id,
                slot=AppointmentSlot(
                    slot_id=row.slot_id,
                    hospital_name=row.hospital_name,
                    city=row.city or "Bilinmiyor",
                    physician_name=row.physician_name,
                    specialty=row.specialty,
                    start_at=row.start_at,
                    is_available=True,
                ),
                status=AppointmentStatus.CANCELLED,
            )
