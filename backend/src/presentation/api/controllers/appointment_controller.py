from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from application.services.appointment_service import AppointmentService
from domain.entities.patient import PatientAccount
from presentation.api.schemas.requests import AppointmentSearchRequest
from presentation.api.schemas.responses import AppointmentBookingResponse, AppointmentSlotResponse
from presentation.dependencies import get_appointment_service, get_current_user


router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentBookingResponse])
async def list_appointments(
    current_user: PatientAccount = Depends(get_current_user),
    appointment_service: AppointmentService = Depends(get_appointment_service),
) -> list[AppointmentBookingResponse]:
    bookings = await appointment_service.list_bookings(current_user.patient_id)
    return [
        AppointmentBookingResponse(
            booking_id=booking.booking_id,
            status=booking.status.value,
            slot=AppointmentSlotResponse(
                slot_id=booking.slot.slot_id,
                hospital_name=booking.slot.hospital_name,
                city=booking.slot.city,
                physician_name=booking.slot.physician_name,
                specialty=booking.slot.specialty,
                start_at=booking.slot.start_at.isoformat(),
                is_available=booking.slot.is_available,
            ),
        )
        for booking in bookings
    ]

@router.post("/search", response_model=list[AppointmentSlotResponse])
async def search_appointments(
    request: AppointmentSearchRequest,
    current_user: PatientAccount = Depends(get_current_user),
    appointment_service: AppointmentService = Depends(get_appointment_service),
) -> list[AppointmentSlotResponse]:
    try:
        preferred_date = date.fromisoformat(request.preferred_date) if request.preferred_date else None
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Tarih formatı YYYY-MM-DD olmalı.") from error
    slots = await appointment_service.search_slots(
        specialty=request.specialty,
        city=request.city,
        preferred_date=preferred_date,
        hospital_name=request.hospital_name,
    )
    return [
        AppointmentSlotResponse(
            slot_id=slot.slot_id,
            hospital_name=slot.hospital_name,
            city=slot.city,
            physician_name=slot.physician_name,
            specialty=slot.specialty,
            start_at=slot.start_at.isoformat(),
            is_available=slot.is_available,
        )
        for slot in slots
    ]


@router.post("/{slot_id}/book", response_model=AppointmentBookingResponse)
async def book_appointment(
    slot_id: str,
    current_user: PatientAccount = Depends(get_current_user),
    appointment_service: AppointmentService = Depends(get_appointment_service),
) -> AppointmentBookingResponse:
    try:
        booking = await appointment_service.book_slot(
            patient_id=current_user.patient_id,
            slot_id=slot_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AppointmentBookingResponse(
        booking_id=booking.booking_id,
        status=booking.status.value,
        slot=AppointmentSlotResponse(
            slot_id=booking.slot.slot_id,
            hospital_name=booking.slot.hospital_name,
            city=booking.slot.city,
            physician_name=booking.slot.physician_name,
            specialty=booking.slot.specialty,
            start_at=booking.slot.start_at.isoformat(),
            is_available=booking.slot.is_available,
        ),
    )


@router.post("/{booking_id}/cancel", response_model=AppointmentBookingResponse)
async def cancel_appointment(
    booking_id: str,
    current_user: PatientAccount = Depends(get_current_user),
    appointment_service: AppointmentService = Depends(get_appointment_service),
) -> AppointmentBookingResponse:
    booking = await appointment_service.cancel_booking(
        patient_id=current_user.patient_id,
        booking_id=booking_id,
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı.")
    return AppointmentBookingResponse(
        booking_id=booking.booking_id,
        status=booking.status.value,
        slot=AppointmentSlotResponse(
            slot_id=booking.slot.slot_id,
            hospital_name=booking.slot.hospital_name,
            city=booking.slot.city,
            physician_name=booking.slot.physician_name,
            specialty=booking.slot.specialty,
            start_at=booking.slot.start_at.isoformat(),
            is_available=booking.slot.is_available,
        ),
    )
