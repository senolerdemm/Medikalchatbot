from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from domain.entities.appointment import (
    APPOINTMENT_TIMEZONE,
    AppointmentBooking,
    AppointmentSlot,
)
from domain.ports.repositories.appointment_repository import AppointmentRepository
from domain.ports.services.hospital_api_service import HospitalAPIService


@dataclass(slots=True)
class AppointmentPreferences:
    action: str
    specialty: str | None = None
    specialty_inferred: bool = False
    specialty_reason: str | None = None
    city: str | None = None
    hospital_name: str | None = None
    physician_name: str | None = None
    preferred_date: date | None = None
    preferred_hour: int | None = None
    city_inferred: bool = False
    preferred_date_explicit: bool = False
    preferred_hour_explicit: bool = False
    slot_id: str | None = None
    booking_id: str | None = None
    selection_index: int | None = None


@dataclass(slots=True)
class AppointmentSearchResult:
    slots: list[AppointmentSlot]
    relaxed: bool = False
    fallback_note: str | None = None


class AppointmentService:
    def __init__(
        self,
        *,
        hospital_api: HospitalAPIService,
        appointment_repository: AppointmentRepository,
    ) -> None:
        self.hospital_api = hospital_api
        self.appointment_repository = appointment_repository

    async def search_slots(
        self,
        *,
        specialty: str,
        city: str | None = None,
        preferred_date: date | None = None,
        preferred_hour: int | None = None,
        hospital_name: str | None = None,
        physician_name: str | None = None,
        limit: int = 8,
    ) -> list[AppointmentSlot]:
        slots = await self.hospital_api.search_slots(
            specialty=specialty,
            city=city,
            preferred_date=preferred_date,
            preferred_hour=preferred_hour,
            hospital_name=hospital_name,
            physician_name=physician_name,
            limit=max(limit * 2, 10),
        )
        reserved_slot_ids = await self.appointment_repository.list_reserved_slot_ids()
        return [
            slot
            for slot in slots
            if slot.slot_id not in reserved_slot_ids
        ][:limit]

    async def search_slots_with_fallbacks(
        self,
        *,
        specialty: str,
        city: str | None = None,
        preferred_date: date | None = None,
        preferred_hour: int | None = None,
        hospital_name: str | None = None,
        physician_name: str | None = None,
        city_inferred: bool = False,
        preferred_date_explicit: bool = False,
        preferred_hour_explicit: bool = False,
        limit: int = 8,
    ) -> AppointmentSearchResult:
        candidate_slots = await self.search_slots(
            specialty=specialty,
            city=city,
            preferred_date=preferred_date,
            preferred_hour=preferred_hour,
            hospital_name=hospital_name,
            physician_name=physician_name,
            limit=limit,
        )
        exact_slots = self._filter_exact_matches(
            slots=candidate_slots,
            preferred_hour=preferred_hour,
            preferred_hour_explicit=preferred_hour_explicit,
        )
        if exact_slots:
            return AppointmentSearchResult(slots=exact_slots)

        attempts: list[tuple[dict[str, object], str]] = []
        if physician_name:
            attempts.append(
                (
                    {
                        "specialty": specialty,
                        "city": city,
                        "preferred_date": preferred_date,
                        "preferred_hour": preferred_hour,
                        "hospital_name": hospital_name,
                        "physician_name": None,
                        "limit": limit,
                    },
                    "Belirttiğiniz doktorla boş slot bulunamadı; aynı bölümdeki diğer uygun seçenekleri listeledim.",
                )
            )
        if hospital_name:
            attempts.append(
                (
                    {
                        "specialty": specialty,
                        "city": city,
                        "preferred_date": preferred_date,
                        "preferred_hour": preferred_hour,
                        "hospital_name": None,
                        "physician_name": None,
                        "limit": limit,
                    },
                    "Belirttiğiniz hastanede boş slot bulunamadı; aynı şehirdeki benzer seçenekleri listeledim.",
                )
            )
        if preferred_hour_explicit and preferred_hour is not None:
            attempts.append(
                (
                    {
                        "specialty": specialty,
                        "city": city,
                        "preferred_date": preferred_date,
                        "preferred_hour": None,
                        "hospital_name": hospital_name,
                        "physician_name": physician_name,
                        "limit": limit,
                    },
                    "Belirttiğiniz saate tam uyan boş slot bulunamadı; en yakın saatleri listeledim.",
                )
            )
        if preferred_date_explicit and preferred_date is not None:
            attempts.append(
                (
                    {
                        "specialty": specialty,
                        "city": city,
                        "preferred_date": None,
                        "preferred_hour": preferred_hour,
                        "hospital_name": hospital_name,
                        "physician_name": physician_name,
                        "limit": limit,
                    },
                    "Belirttiğiniz tarihte boş slot bulunamadı; en yakın tarihli seçenekleri listeledim.",
                )
            )
        if preferred_date_explicit and preferred_hour_explicit:
            attempts.append(
                (
                    {
                        "specialty": specialty,
                        "city": city,
                        "preferred_date": None,
                        "preferred_hour": None,
                        "hospital_name": hospital_name,
                        "physician_name": physician_name,
                        "limit": limit,
                    },
                    "Belirttiğiniz tarih ve saate tam uyan boş slot bulunamadı; en yakın uygun seçenekleri listeledim.",
                )
            )
        if city_inferred and city:
            attempts.append(
                (
                    {
                        "specialty": specialty,
                        "city": None,
                        "preferred_date": preferred_date,
                        "preferred_hour": preferred_hour,
                        "hospital_name": hospital_name,
                        "physician_name": physician_name,
                        "limit": limit,
                    },
                    "Profil şehrinizde boş slot bulunamadı; diğer şehirlerdeki yakın seçenekleri listeledim.",
                )
            )

        seen_slot_ids: set[str] = set()
        for kwargs, note in attempts:
            slots = await self.search_slots(**kwargs)
            filtered_slots = [
                slot for slot in slots if slot.slot_id not in seen_slot_ids
            ]
            if filtered_slots:
                return AppointmentSearchResult(
                    slots=filtered_slots,
                    relaxed=True,
                    fallback_note=note,
                )
            seen_slot_ids.update(slot.slot_id for slot in slots)

        return AppointmentSearchResult(slots=[])

    def _filter_exact_matches(
        self,
        *,
        slots: list[AppointmentSlot],
        preferred_hour: int | None,
        preferred_hour_explicit: bool,
    ) -> list[AppointmentSlot]:
        if not preferred_hour_explicit or preferred_hour is None:
            return slots
        return [
            slot
            for slot in slots
            if slot.start_at.astimezone(APPOINTMENT_TIMEZONE).hour == preferred_hour
        ]

    async def book_slot(
        self,
        *,
        patient_id: str,
        slot_id: str,
        city: str | None = None,
    ) -> AppointmentBooking:
        reserved_slot_ids = await self.appointment_repository.list_reserved_slot_ids()
        if slot_id in reserved_slot_ids:
            raise ValueError("Secilen randevu slotu artik musait degil.")
        booking = await self.hospital_api.book_slot(patient_id=patient_id, slot_id=slot_id)
        await self.appointment_repository.save_booking(
            patient_id=patient_id,
            booking=booking,
            city=city or booking.slot.city,
        )
        return booking

    async def cancel_booking(
        self,
        *,
        patient_id: str,
        booking_id: str,
    ) -> AppointmentBooking | None:
        booking = await self.hospital_api.cancel_booking(booking_id=booking_id)
        repository_booking = await self.appointment_repository.cancel_booking(patient_id, booking_id)
        return booking or repository_booking

    async def list_bookings(self, patient_id: str) -> list[AppointmentBooking]:
        return await self.appointment_repository.list_bookings(patient_id)

    def extract_preferences(self, text: str) -> AppointmentPreferences:
        normalized = self._normalize(text)
        return AppointmentPreferences(
            action=self._extract_action(normalized),
            specialty=self._extract_specialty(normalized),
            city=self._extract_city(normalized),
            hospital_name=self._extract_hospital(normalized),
            physician_name=self._extract_physician(text),
            preferred_date=self._extract_date(normalized),
            preferred_hour=self._extract_hour(normalized),
            slot_id=self._extract_slot_id(normalized),
            booking_id=self._extract_booking_id(normalized),
            selection_index=self._extract_selection_index(normalized),
        )

    def pick_slot_from_preferences(
        self,
        *,
        slots: list[AppointmentSlot],
        preferences: AppointmentPreferences,
    ) -> AppointmentSlot | None:
        if not slots:
            return None

        if preferences.slot_id is not None:
            return next((slot for slot in slots if slot.slot_id == preferences.slot_id), None)

        if preferences.selection_index is not None and 0 <= preferences.selection_index < len(slots):
            return slots[preferences.selection_index]

        if len(slots) == 1:
            return slots[0]

        return None

    def _normalize(self, text: str) -> str:
        return text.lower().translate(
            str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
        )

    def _extract_action(self, normalized: str) -> str:
        if re.search(r"\b(iptal|vazgec|sil|kaldir)\b", normalized):
            return "cancel"
        if (
            re.search(r"\brandevularim(i)?\b", normalized)
            or "randevulari gor" in normalized
            or "mevcut randevular" in normalized
            or "aktif randevu" in normalized
            or "mevcut randevu" in normalized
            or re.search(r"\blistele\b", normalized)
        ):
            return "list"
        if re.search(r"\b(al|almak|olustur|rezerve|ayarla|onayla|ayir|rezervasyon)\b", normalized):
            return "book"
        return "search"

    def _extract_specialty(self, normalized: str) -> str | None:
        keyword_map = {
            "kardiyo": "Kardiyoloji",
            "kalp": "Kardiyoloji",
            "kalpci": "Kardiyoloji",
            "kalp doktoru": "Kardiyoloji",
            "gastro": "Gastroenteroloji",
            "gastroenteroloji": "Gastroenteroloji",
            "reflu": "Gastroenteroloji",
            "mide yanmasi": "Gastroenteroloji",
            "eksime": "Gastroenteroloji",
            "endokrin": "Endokrinoloji",
            "diyabet": "Endokrinoloji",
            "seker": "Endokrinoloji",
            "insulin": "Endokrinoloji",
            "tiroid": "Endokrinoloji",
            "guatr": "Endokrinoloji",
            "gogus": "Gogus Hastaliklari",
            "akciger": "Gogus Hastaliklari",
            "oksuruk": "Gogus Hastaliklari",
            "astim": "Gogus Hastaliklari",
            "koah": "Gogus Hastaliklari",
            "balgam": "Gogus Hastaliklari",
            "cilt": "Dermatoloji",
            "deri": "Dermatoloji",
            "cocuk": "Pediatri",
            "bebek": "Pediatri",
            "ortopedi": "Ortopedi",
            "psik": "Psikiyatri",
            "psikolog": "Psikiyatri",
            "psikolojik": "Psikiyatri",
            "anksiyete": "Psikiyatri",
            "panik": "Psikiyatri",
            "depresyon": "Psikiyatri",
            "noro": "Noroloji",
            "dahiliye": "Dahiliye",
            "mide": "Gastroenteroloji",
            "goz": "Goz Hastaliklari",
            "gorme": "Goz Hastaliklari",
            "kbb": "Kulak Burun Bogaz",
            "bogaz": "Kulak Burun Bogaz",
            "kulak": "Kulak Burun Bogaz",
            "burun": "Kulak Burun Bogaz",
            "sinuzit": "Kulak Burun Bogaz",
            "genel cerrahi": "Genel Cerrahi",
            "cerrahi": "Genel Cerrahi",
            "jinekoloji": "Kadin Hastaliklari ve Dogum",
            "kadin dogum": "Kadin Hastaliklari ve Dogum",
            "adet": "Kadin Hastaliklari ve Dogum",
            "gebelik": "Kadin Hastaliklari ve Dogum",
            "hamilelik": "Kadin Hastaliklari ve Dogum",
            "uroloji": "Uroloji",
            "nefro": "Nefroloji",
            "kreatinin": "Nefroloji",
            "protein kacagi": "Nefroloji",
            "romatizma": "Romatoloji",
            "romatoloji": "Romatoloji",
            "eklem sisligi": "Romatoloji",
            "hematoloji": "Hematoloji",
            "anemi": "Hematoloji",
            "kan hastaligi": "Hematoloji",
            "onkoloji": "Onkoloji",
            "kanser": "Onkoloji",
            "fizik tedavi": "Fizik Tedavi",
        }
        for keyword, specialty in keyword_map.items():
            if keyword in normalized:
                return specialty
        return None

    def _extract_city(self, normalized: str) -> str | None:
        for city in ("ankara", "istanbul", "eskisehir", "izmir", "bursa"):
            if city in normalized:
                return city.title()
        return None

    def _extract_hospital(self, normalized: str) -> str | None:
        hospitals = (
            "sehir hastanesi",
            "universite hastanesi",
            "acibadem",
            "medipol",
            "memorial",
            "liv hospital",
        )
        for hospital in hospitals:
            if hospital in normalized:
                return hospital.title()
        return None

    def _extract_physician(self, text: str) -> str | None:
        match = re.search(r"(dr\.?\s+[a-zA-ZçğıöşüÇĞİÖŞÜ]+\s+[a-zA-ZçğıöşüÇĞİÖŞÜ]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_slot_id(self, normalized: str) -> str | None:
        match = re.search(r"(slot-[a-z0-9-]+)", normalized)
        return match.group(1) if match else None

    def _extract_booking_id(self, normalized: str) -> str | None:
        match = re.search(r"((?:seed-booking|booking|randevu)-[a-z0-9-]+)", normalized)
        return match.group(1) if match else None

    def _extract_selection_index(self, normalized: str) -> int | None:
        if "ilk" in normalized or "birinci" in normalized:
            return 0
        if "ikinci" in normalized:
            return 1
        if "ucuncu" in normalized:
            return 2
        match = re.search(r"\b([1-5])\.\s*(?:slot|secenek)?", normalized)
        if match:
            return int(match.group(1)) - 1
        return None

    def _extract_date(self, normalized: str) -> date | None:
        today = datetime.now().date()

        if "yarin" in normalized:
            return today + timedelta(days=1)
        if "bugun" in normalized:
            return today

        iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", normalized)
        if iso_match:
            return date.fromisoformat(iso_match.group(1))

        dot_match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", normalized)
        if dot_match:
            day, month, year = map(int, dot_match.groups())
            return date(year, month, day)

        weekdays = {
            "pazartesi": 0,
            "sali": 1,
            "carsamba": 2,
            "persembe": 3,
            "cuma": 4,
            "cumartesi": 5,
            "pazar": 6,
        }
        for name, weekday in weekdays.items():
            if name in normalized:
                delta = (weekday - today.weekday()) % 7
                delta = 7 if delta == 0 else delta
                return today + timedelta(days=delta)

        return None

    def has_explicit_date_reference(self, text: str) -> bool:
        normalized = self._normalize(text)
        if any(
            keyword in normalized
            for keyword in (
                "yarin",
                "bugun",
                "pazartesi",
                "sali",
                "carsamba",
                "persembe",
                "cuma",
                "cumartesi",
                "pazar",
            )
        ):
            return True
        return bool(
            re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", normalized)
            or re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", normalized)
        )

    def has_explicit_hour_reference(self, text: str) -> bool:
        normalized = self._normalize(text)
        if any(
            keyword in normalized
            for keyword in ("sabah", "ogle", "oglen", "ogleden sonra", "aksam")
        ):
            return True
        return bool(
            re.search(r"\bsaat\s*\d{1,2}(?::\d{2})?\b", normalized)
            or re.search(r"\b\d{1,2}:\d{2}\b", normalized)
            or re.search(r"\b\d{1,2}\s*gibi\b", normalized)
        )

    def _extract_hour(self, normalized: str) -> int | None:
        time_match = re.search(
            r"(?:saat\s*)?(\d{1,2})(?::(\d{2}))?\s*(?:gibi|civari|dolaylarinda)?",
            normalized,
        )
        if time_match:
            hour = int(time_match.group(1))
            if 0 <= hour <= 23:
                return hour

        if "sabah" in normalized:
            return 9
        if "ogle" in normalized:
            return 12
        if "ogleden sonra" in normalized or "aksamustu" in normalized:
            return 15
        if "aksam" in normalized:
            return 18

        return None
