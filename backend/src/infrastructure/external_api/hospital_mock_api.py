from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable
from uuid import uuid4

from domain.entities.appointment import (
    APPOINTMENT_TIMEZONE,
    AppointmentBooking,
    AppointmentSlot,
)
from domain.ports.services.hospital_api_service import HospitalAPIService


class HospitalMockAPI(HospitalAPIService):
    def __init__(self) -> None:
        self._slots = self._build_slots()
        self._slots_by_id = {slot.slot_id: slot for slot in self._slots}
        self._bookings: dict[str, AppointmentBooking] = {}

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
        normalized_specialty = specialty.casefold()
        normalized_city = city.casefold() if city else None
        normalized_hospital = hospital_name.casefold() if hospital_name else None
        normalized_physician = physician_name.casefold() if physician_name else None
        matching_slots = [
            slot
            for slot in self._slots
            if slot.matches(specialty=specialty, preferred_date=preferred_date)
            and (not normalized_hospital or normalized_hospital in slot.hospital_name.casefold())
            and (not normalized_city or normalized_city == slot.city.casefold())
            and (not normalized_physician or normalized_physician in slot.physician_name.casefold())
        ]
        if not matching_slots:
            matching_slots = self._ensure_demo_slots(
                specialty=specialty,
                city=city,
                preferred_date=preferred_date,
                preferred_hour=preferred_hour,
                hospital_name=hospital_name,
                physician_name=physician_name,
            )
        matching_slots.sort(
            key=lambda slot: (
                0 if normalized_city and slot.city.casefold() == normalized_city else 1,
                0 if slot.specialty.casefold() == normalized_specialty else 1,
                0
                if normalized_hospital and normalized_hospital in slot.hospital_name.casefold()
                else 1,
                0
                if preferred_hour is None
                else abs(slot.start_at.astimezone(APPOINTMENT_TIMEZONE).hour - preferred_hour),
                slot.start_at,
                slot.hospital_name,
            )
        )
        return matching_slots[:limit]

    def _ensure_demo_slots(
        self,
        *,
        specialty: str,
        city: str | None,
        preferred_date: date | None,
        preferred_hour: int | None,
        hospital_name: str | None,
        physician_name: str | None,
    ) -> list[AppointmentSlot]:
        slot_date = preferred_date or (
            datetime.now(APPOINTMENT_TIMEZONE) + timedelta(days=1)
        ).date()
        target_city = city or "Ankara"
        target_hospital = hospital_name or self._default_hospital(target_city, specialty)
        target_physician = physician_name or self._default_physician(specialty)
        base_hour = preferred_hour if preferred_hour is not None else 10
        candidate_hours = tuple(
            hour for hour in (base_hour, base_hour + 1, base_hour - 1, 14) if 8 <= hour <= 18
        )

        generated: list[AppointmentSlot] = []
        for hour in dict.fromkeys(candidate_hours):
            slot_id = (
                "demo-"
                f"{self._slug(target_city)}-"
                f"{self._slug(specialty)}-"
                f"{slot_date.isoformat()}-"
                f"{hour:02d}"
            )
            existing = self._slots_by_id.get(slot_id)
            if existing is not None:
                generated.append(existing)
                continue
            slot = AppointmentSlot(
                slot_id=slot_id,
                hospital_name=target_hospital,
                city=target_city,
                physician_name=target_physician,
                specialty=specialty,
                start_at=datetime.combine(
                    slot_date,
                    time(hour=hour, minute=0, tzinfo=APPOINTMENT_TIMEZONE),
                ),
            )
            self._slots.append(slot)
            self._slots_by_id[slot.slot_id] = slot
            generated.append(slot)
        return generated

    def _default_hospital(self, city: str, specialty: str) -> str:
        specialty_key = specialty.casefold()
        city_key = city.casefold()
        for slot in self._slots:
            if slot.city.casefold() == city_key and slot.specialty.casefold() == specialty_key:
                return slot.hospital_name
        return f"{city} Demo Hastanesi"

    def _default_physician(self, specialty: str) -> str:
        specialty_key = specialty.casefold()
        for slot in self._slots:
            if slot.specialty.casefold() == specialty_key:
                return slot.physician_name
        return "Dr. Demo Hekim"

    def _slug(self, value: str) -> str:
        normalized = value.lower().translate(
            str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
        )
        return "-".join(part for part in normalized.split() if part)

    async def book_slot(
        self,
        *,
        patient_id: str,
        slot_id: str,
    ) -> AppointmentBooking:
        slot = self._slots_by_id.get(slot_id)
        if slot is None:
            raise ValueError("Seçilen randevu slotu bulunamadı.")
        if not slot.is_available:
            raise ValueError("Seçilen randevu slotu artık müsait değil.")

        booking = AppointmentBooking(
            patient_id=patient_id,
            booking_id=f"booking-{uuid4()}",
            slot=slot,
        )
        booking.confirm()
        self._bookings[booking.booking_id] = booking
        return booking

    async def cancel_booking(self, *, booking_id: str) -> AppointmentBooking | None:
        booking = self._bookings.get(booking_id)
        if booking is None:
            return None
        booking.cancel()
        return booking

    async def list_patient_bookings(self, *, patient_id: str) -> list[AppointmentBooking]:
        bookings = [
            booking
            for booking in self._bookings.values()
            if booking.patient_id == patient_id
        ]
        bookings.sort(key=lambda booking: booking.slot.start_at)
        return bookings

    def _build_slots(self) -> list[AppointmentSlot]:
        now = datetime.now(APPOINTMENT_TIMEZONE).replace(minute=0, second=0, microsecond=0)
        schedules = self._build_schedule_templates()

        slots: list[AppointmentSlot] = []
        slot_counter = 1
        for hospital, city, physician, specialty, day_offset, hours in schedules:
            for extra_day in range(0, 21):
                slot_date = (now + timedelta(days=day_offset + extra_day)).date()
                for hour in hours:
                    start_at = datetime.combine(
                        slot_date,
                        time(hour=hour, minute=0, tzinfo=APPOINTMENT_TIMEZONE),
                    )
                    slots.append(
                        AppointmentSlot(
                            slot_id=f"slot-{slot_counter:03d}",
                            hospital_name=hospital,
                            city=city,
                            physician_name=physician,
                            specialty=specialty,
                            start_at=start_at,
                        )
                    )
                    slot_counter += 1
        return slots

    def _build_schedule_templates(self) -> list[tuple[str, str, str, str, int, tuple[int, ...]]]:
        templates: list[tuple[str, str, str, str, int, tuple[int, ...]]] = []

        def add_group(
            *,
            city: str,
            hospital: str,
            specialty: str,
            physicians: Iterable[str],
            day_offset: int,
            hours: tuple[int, ...],
        ) -> None:
            for physician in physicians:
                templates.append((hospital, city, physician, specialty, day_offset, hours))

        add_group(
            city="Ankara",
            hospital="Ankara Sehir Hastanesi",
            specialty="Kardiyoloji",
            physicians=("Dr. Dilara Kurt", "Dr. Mehmet Kaan", "Dr. Sibel Gursoy"),
            day_offset=1,
            hours=(9, 10, 11, 12, 14, 15, 16),
        )
        add_group(
            city="Ankara",
            hospital="Hacettepe Universite Hastanesi",
            specialty="Kardiyoloji",
            physicians=("Dr. Cem Basaran", "Dr. Aylin Karasu"),
            day_offset=1,
            hours=(10, 11, 13, 15, 17),
        )
        add_group(
            city="Ankara",
            hospital="Medicana Ankara",
            specialty="Kardiyoloji",
            physicians=("Dr. Banu Guler", "Dr. Levent Dogan"),
            day_offset=2,
            hours=(9, 10, 12, 14, 16),
        )
        add_group(
            city="Ankara",
            hospital="Liv Hospital Ankara",
            specialty="Kulak Burun Bogaz",
            physicians=("Dr. Can Ozturk", "Dr. Deniz Ersoy"),
            day_offset=1,
            hours=(9, 10, 11, 13, 15, 16),
        )
        add_group(
            city="Ankara",
            hospital="Ankara Sehir Hastanesi",
            specialty="Dermatoloji",
            physicians=("Dr. Elif Yildiz", "Dr. Seda Yalcin"),
            day_offset=1,
            hours=(9, 10, 12, 14, 16),
        )
        add_group(
            city="Ankara",
            hospital="Gazi Universite Hastanesi",
            specialty="Dahiliye",
            physicians=("Dr. Murat Coskun", "Dr. Ekin Gok"),
            day_offset=1,
            hours=(10, 11, 13, 16),
        )
        add_group(
            city="Ankara",
            hospital="Ankara Sehir Hastanesi",
            specialty="Gastroenteroloji",
            physicians=("Dr. Selma Kaya", "Dr. Onur Erdem"),
            day_offset=1,
            hours=(9, 10, 11, 14, 16),
        )
        add_group(
            city="Ankara",
            hospital="Ankara Sehir Hastanesi",
            specialty="Endokrinoloji",
            physicians=("Dr. Pinar Ates", "Dr. Ufuk Celen"),
            day_offset=1,
            hours=(9, 10, 12, 14, 16),
        )
        add_group(
            city="Ankara",
            hospital="Ataturk Gogus Hastaliklari Hastanesi",
            specialty="Gogus Hastaliklari",
            physicians=("Dr. Serkan Kuru", "Dr. Sema Ozkan"),
            day_offset=1,
            hours=(9, 10, 11, 13, 15),
        )
        add_group(
            city="Ankara",
            hospital="Dışkapı Yıldırım Beyazıt Hastanesi",
            specialty="Goz Hastaliklari",
            physicians=("Dr. Nilay Bilge", "Dr. Hakan Unal"),
            day_offset=2,
            hours=(9, 11, 14, 16),
        )
        add_group(
            city="Ankara",
            hospital="Bilkent Sehir Hastanesi",
            specialty="Psikiyatri",
            physicians=("Dr. Zeynep Koc", "Dr. Alper Can"),
            day_offset=1,
            hours=(10, 12, 14, 16),
        )
        add_group(
            city="Ankara",
            hospital="Bilkent Sehir Hastanesi",
            specialty="Uroloji",
            physicians=("Dr. Burak Oner", "Dr. Tolga Ileri"),
            day_offset=2,
            hours=(9, 11, 13, 16),
        )
        add_group(
            city="Ankara",
            hospital="Hacettepe Universite Hastanesi",
            specialty="Nefroloji",
            physicians=("Dr. Melis Yaman",),
            day_offset=2,
            hours=(10, 12, 15),
        )
        add_group(
            city="Ankara",
            hospital="Gazi Universite Hastanesi",
            specialty="Romatoloji",
            physicians=("Dr. Esra Ekinci",),
            day_offset=3,
            hours=(9, 11, 14),
        )
        add_group(
            city="Ankara",
            hospital="Ankara Sehir Hastanesi",
            specialty="Pediatri",
            physicians=("Dr. Burcu Aydin", "Dr. Mert Sayan"),
            day_offset=1,
            hours=(9, 10, 11, 14, 15),
        )
        add_group(
            city="Ankara",
            hospital="Etlik Sehir Hastanesi",
            specialty="Kadin Hastaliklari ve Dogum",
            physicians=("Dr. Berrin Oz", "Dr. Irem Tekin"),
            day_offset=1,
            hours=(9, 11, 13, 15),
        )
        add_group(
            city="Ankara",
            hospital="Ankara Sehir Hastanesi",
            specialty="Hematoloji",
            physicians=("Dr. Aysu Kiran",),
            day_offset=3,
            hours=(10, 12, 15),
        )
        add_group(
            city="Ankara",
            hospital="Hacettepe Universite Hastanesi",
            specialty="Onkoloji",
            physicians=("Dr. Levent Ercan",),
            day_offset=4,
            hours=(9, 11, 14),
        )
        add_group(
            city="Ankara",
            hospital="Etlik Sehir Hastanesi",
            specialty="Noroloji",
            physicians=("Dr. Ilker Sarp", "Dr. Derya Ozen"),
            day_offset=2,
            hours=(9, 11, 14, 16),
        )

        add_group(
            city="Istanbul",
            hospital="Acibadem Altunizade",
            specialty="Kardiyoloji",
            physicians=("Dr. Selin Tas", "Dr. Baris Ertem"),
            day_offset=1,
            hours=(9, 10, 11, 14, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Memorial Sisli",
            specialty="Kardiyoloji",
            physicians=("Dr. Kerem Aydin", "Dr. Nil Ozkaya"),
            day_offset=1,
            hours=(10, 13, 15, 17),
        )
        add_group(
            city="Istanbul",
            hospital="Medipol Mega",
            specialty="Dermatoloji",
            physicians=("Dr. Berna Koc", "Dr. Ilayda Sari"),
            day_offset=1,
            hours=(10, 12, 15, 17),
        )
        add_group(
            city="Istanbul",
            hospital="Acibadem Altunizade",
            specialty="Gastroenteroloji",
            physicians=("Dr. Akin Demir", "Dr. Buse Guner"),
            day_offset=1,
            hours=(9, 11, 13, 15, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Medipol Mega",
            specialty="Endokrinoloji",
            physicians=("Dr. Burcin Ak", "Dr. Emre Kose"),
            day_offset=1,
            hours=(9, 10, 12, 14, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Sureyyapasa Gogus Hastaliklari Hastanesi",
            specialty="Gogus Hastaliklari",
            physicians=("Dr. Riza Caglar", "Dr. Selda Oztas"),
            day_offset=1,
            hours=(9, 10, 11, 13, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Istanbul Egitim ve Arastirma Hastanesi",
            specialty="Goz Hastaliklari",
            physicians=("Dr. Oznur Bas", "Dr. Sinan Telli"),
            day_offset=2,
            hours=(9, 11, 14, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Medipol Mega",
            specialty="Psikiyatri",
            physicians=("Dr. Ece Tan",),
            day_offset=2,
            hours=(10, 12, 14, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Memorial Bahcelievler",
            specialty="Dahiliye",
            physicians=("Dr. Cagla Er", "Dr. Onur Kuru"),
            day_offset=1,
            hours=(9, 11, 13, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Basaksehir Cam Sakura Sehir Hastanesi",
            specialty="Kulak Burun Bogaz",
            physicians=("Dr. Nazli Yurt", "Dr. Gokhan Sener"),
            day_offset=1,
            hours=(9, 10, 11, 13, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Liv Hospital Ulus",
            specialty="Kulak Burun Bogaz",
            physicians=("Dr. Cem Aksoy", "Dr. Su Acar"),
            day_offset=2,
            hours=(10, 12, 14, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Acibadem Maslak",
            specialty="Noroloji",
            physicians=("Dr. Pelin Ozer", "Dr. Faruk Uslu"),
            day_offset=2,
            hours=(11, 13, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Memorial Bahcelievler",
            specialty="Uroloji",
            physicians=("Dr. Okan Sener",),
            day_offset=3,
            hours=(9, 11, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Acibadem Maslak",
            specialty="Pediatri",
            physicians=("Dr. Ayca Keskin", "Dr. Selen Aras"),
            day_offset=2,
            hours=(9, 10, 12, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Zeynep Kamil Hastanesi",
            specialty="Kadin Hastaliklari ve Dogum",
            physicians=("Dr. Aylin Yuce", "Dr. Merve Kadi"),
            day_offset=1,
            hours=(9, 11, 13, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Memorial Sisli",
            specialty="Nefroloji",
            physicians=("Dr. Tunc Yalcin",),
            day_offset=3,
            hours=(10, 12, 14),
        )
        add_group(
            city="Istanbul",
            hospital="Acibadem Altunizade",
            specialty="Romatoloji",
            physicians=("Dr. Gaye Acar",),
            day_offset=4,
            hours=(9, 11, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Medipol Mega",
            specialty="Genel Cerrahi",
            physicians=("Dr. Huseyin Kara", "Dr. Selim Toker"),
            day_offset=2,
            hours=(9, 11, 14, 16),
        )
        add_group(
            city="Istanbul",
            hospital="Liv Hospital Ulus",
            specialty="Fizik Tedavi",
            physicians=("Dr. Nehir Ozen",),
            day_offset=3,
            hours=(10, 13, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Acibadem Altunizade",
            specialty="Hematoloji",
            physicians=("Dr. Yigit Ocal",),
            day_offset=4,
            hours=(10, 12, 15),
        )
        add_group(
            city="Istanbul",
            hospital="Memorial Sisli",
            specialty="Onkoloji",
            physicians=("Dr. Arda Ince",),
            day_offset=4,
            hours=(9, 11, 14),
        )

        add_group(
            city="Eskisehir",
            hospital="Eskisehir Sehir Hastanesi",
            specialty="Dahiliye",
            physicians=("Dr. Ayse Demir", "Dr. Soner Kilic"),
            day_offset=1,
            hours=(9, 11, 14, 16),
        )
        add_group(
            city="Eskisehir",
            hospital="Osmangazi Universite Hastanesi",
            specialty="Gastroenteroloji",
            physicians=("Dr. Eda Yildirim",),
            day_offset=2,
            hours=(10, 12, 15),
        )
        add_group(
            city="Eskisehir",
            hospital="Osmangazi Universite Hastanesi",
            specialty="Kardiyoloji",
            physicians=("Dr. Mehmet Kaya", "Dr. Defne Ates"),
            day_offset=1,
            hours=(10, 13, 15, 17),
        )
        add_group(
            city="Eskisehir",
            hospital="Eskisehir Sehir Hastanesi",
            specialty="Kulak Burun Bogaz",
            physicians=("Dr. Burcu Inal",),
            day_offset=1,
            hours=(10, 12, 17),
        )
        add_group(
            city="Eskisehir",
            hospital="Osmangazi Universite Hastanesi",
            specialty="Endokrinoloji",
            physicians=("Dr. Ebru Cetin",),
            day_offset=2,
            hours=(9, 11, 14),
        )
        add_group(
            city="Eskisehir",
            hospital="Eskisehir Sehir Hastanesi",
            specialty="Gogus Hastaliklari",
            physicians=("Dr. Sarp Kose",),
            day_offset=2,
            hours=(10, 12, 15),
        )
        add_group(
            city="Eskisehir",
            hospital="Osmangazi Universite Hastanesi",
            specialty="Goz Hastaliklari",
            physicians=("Dr. Meltem Ince",),
            day_offset=3,
            hours=(9, 11, 16),
        )
        add_group(
            city="Eskisehir",
            hospital="Anadolu Hastanesi",
            specialty="Psikiyatri",
            physicians=("Dr. Dilan Arikan",),
            day_offset=3,
            hours=(10, 13, 15),
        )
        add_group(
            city="Eskisehir",
            hospital="Anadolu Hastanesi",
            specialty="Ortopedi",
            physicians=("Dr. Hakan Eren",),
            day_offset=2,
            hours=(9, 11, 14),
        )

        add_group(
            city="Izmir",
            hospital="Ege Universite Hastanesi",
            specialty="Kardiyoloji",
            physicians=("Dr. Asena Peker",),
            day_offset=1,
            hours=(9, 10, 12, 15),
        )
        add_group(
            city="Izmir",
            hospital="Memorial Izmir",
            specialty="Ortopedi",
            physicians=("Dr. Asli Saran",),
            day_offset=1,
            hours=(10, 13, 15),
        )
        add_group(
            city="Izmir",
            hospital="Izmir Sehir Hastanesi",
            specialty="Dermatoloji",
            physicians=("Dr. Ipek Cinar",),
            day_offset=2,
            hours=(9, 10, 14),
        )
        add_group(
            city="Izmir",
            hospital="Ege Universite Hastanesi",
            specialty="Gastroenteroloji",
            physicians=("Dr. Ugur Koc",),
            day_offset=2,
            hours=(9, 11, 14),
        )
        add_group(
            city="Izmir",
            hospital="Izmir Sehir Hastanesi",
            specialty="Dahiliye",
            physicians=("Dr. Simge Yildiz",),
            day_offset=1,
            hours=(10, 12, 15),
        )
        add_group(
            city="Izmir",
            hospital="Ege Universite Hastanesi",
            specialty="Goz Hastaliklari",
            physicians=("Dr. Derya Bilgin",),
            day_offset=2,
            hours=(9, 11, 16),
        )
        add_group(
            city="Izmir",
            hospital="Memorial Izmir",
            specialty="Psikiyatri",
            physicians=("Dr. Cansu Ergin",),
            day_offset=2,
            hours=(10, 12, 14),
        )
        add_group(
            city="Izmir",
            hospital="Tepecik Egitim ve Arastirma Hastanesi",
            specialty="Kadin Hastaliklari ve Dogum",
            physicians=("Dr. Ozge Suna",),
            day_offset=1,
            hours=(9, 11, 13),
        )
        add_group(
            city="Izmir",
            hospital="Ege Universite Hastanesi",
            specialty="Pediatri",
            physicians=("Dr. Beliz Arda",),
            day_offset=1,
            hours=(9, 10, 12, 15),
        )

        add_group(
            city="Bursa",
            hospital="Bursa Acibadem",
            specialty="Noroloji",
            physicians=("Dr. Ahmet Gul",),
            day_offset=1,
            hours=(10, 12, 15),
        )
        add_group(
            city="Bursa",
            hospital="Bursa Sehir Hastanesi",
            specialty="Genel Cerrahi",
            physicians=("Dr. Gokce Ates",),
            day_offset=2,
            hours=(9, 11, 16),
        )
        add_group(
            city="Bursa",
            hospital="Memorial Bursa",
            specialty="Fizik Tedavi",
            physicians=("Dr. Leyla Sancak",),
            day_offset=3,
            hours=(10, 14),
        )
        add_group(
            city="Bursa",
            hospital="Bursa Sehir Hastanesi",
            specialty="Kardiyoloji",
            physicians=("Dr. Fikret Unal",),
            day_offset=1,
            hours=(9, 11, 15),
        )
        add_group(
            city="Bursa",
            hospital="Bursa Acibadem",
            specialty="Dahiliye",
            physicians=("Dr. Muge Erden",),
            day_offset=1,
            hours=(10, 12, 16),
        )
        add_group(
            city="Bursa",
            hospital="Bursa Sehir Hastanesi",
            specialty="Endokrinoloji",
            physicians=("Dr. Pervin Isik",),
            day_offset=2,
            hours=(9, 11, 14),
        )
        add_group(
            city="Bursa",
            hospital="Bursa Acibadem",
            specialty="Goz Hastaliklari",
            physicians=("Dr. Levent Bay",),
            day_offset=2,
            hours=(10, 13, 15),
        )
        add_group(
            city="Bursa",
            hospital="Bursa Sehir Hastanesi",
            specialty="Psikiyatri",
            physicians=("Dr. Nihan Demir",),
            day_offset=3,
            hours=(10, 12, 15),
        )

        return templates
