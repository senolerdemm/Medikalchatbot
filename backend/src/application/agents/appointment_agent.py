from __future__ import annotations

from datetime import date
from typing import Any

from application.services.appointment_service import AppointmentPreferences, AppointmentService
from application.services.symptom_guidance_service import SymptomGuidanceService
from domain.entities.appointment import AppointmentBooking, AppointmentSlot
from domain.entities.health_query import HealthQuery
from domain.ports.ai.llm_engine import LLMEngine
from domain.ports.repositories.user_history_repository import UserHistoryRepository


class AppointmentAgent:
    def __init__(
        self,
        appointment_service: AppointmentService,
        user_history_repository: UserHistoryRepository,
        llm_engine: LLMEngine,
        symptom_guidance_service: SymptomGuidanceService,
    ):
        self.appointment_service = appointment_service
        self.user_history_repository = user_history_repository
        self.llm_engine = llm_engine
        self.symptom_guidance_service = symptom_guidance_service

    async def handle_appointment_request(
        self,
        query: HealthQuery,
    ) -> dict[str, object]:
        preferences = await self._build_preferences(query)

        if preferences.action == "list":
            return await self._handle_list(query.patient_id)

        if preferences.action == "cancel":
            return await self._handle_cancel(query.patient_id, preferences)

        if preferences.specialty is None:
            return {
                "message": "Randevu için önce bölüm bilgisini belirtmeniz gerekiyor. Örneğin kardiyoloji, dermatoloji veya KBB diyebilirsiniz.",
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "follow_up",
                    "requires_specialty": True,
                    "slot_options": [],
                    "follow_up_question": "Hangi bölüm için randevu arayalım?",
                },
                "sources": [],
            }

        search_result = await self.appointment_service.search_slots_with_fallbacks(
            specialty=preferences.specialty,
            city=preferences.city,
            preferred_date=preferences.preferred_date,
            preferred_hour=preferences.preferred_hour,
            hospital_name=preferences.hospital_name,
            physician_name=preferences.physician_name,
            city_inferred=preferences.city_inferred,
            preferred_date_explicit=preferences.preferred_date_explicit,
            preferred_hour_explicit=preferences.preferred_hour_explicit,
        )
        slots = search_result.slots
        slot_payload = [self._slot_payload(slot) for slot in slots]

        if preferences.action == "book":
            return await self._handle_booking(
                query.patient_id,
                preferences,
                slots,
                slot_payload,
                relaxed_search=search_result.relaxed,
                fallback_note=search_result.fallback_note,
            )

        if not slots:
            return {
                "message": "Bu isteğe uygun boş randevu bulunamadı. Farklı şehir, tarih, hastane veya bölüm tercihleriyle tekrar deneyebilirsiniz.",
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "search",
                    "booked": False,
                    "slot_options": [],
                    "follow_up_question": "İsterseniz farklı bir şehir, hastane veya tarih belirtebilirsiniz.",
                },
                "sources": [],
            }

        time_hint = (
            f" Saat tercihinize en yakın seçenekleri ({preferences.preferred_hour}:00 civarı) öne çıkardım."
            if preferences.preferred_hour is not None
            else ""
        )
        inferred_note = (
            f" Belirtilerinize göre öncelikle {preferences.specialty} seçeneklerini listeledim."
            if preferences.specialty_inferred and preferences.specialty
            else ""
        )
        return {
            "message": (
                (
                    f"{search_result.fallback_note} "
                    if search_result.relaxed and search_result.fallback_note
                    else "Uygun randevu seçeneklerini listeledim."
                )
                + f"{inferred_note}{time_hint} Rezervasyon için slot numarasını ya da 'ilkini al' gibi bir ifade kullanabilirsiniz."
            ),
            "ui_action": "show_appointment_options",
            "payload": {
                "action": "search",
                "booked": False,
                "specialty": preferences.specialty,
                "specialty_inferred": preferences.specialty_inferred,
                "specialty_reason": preferences.specialty_reason,
                "city": preferences.city,
                "hospital_name": preferences.hospital_name,
                "preferred_date": preferences.preferred_date.isoformat() if preferences.preferred_date else None,
                "preferred_hour": preferences.preferred_hour,
                "slot_options": slot_payload,
                "follow_up_question": "Hangi slotu ayirmami istersiniz?",
            },
            "sources": [],
        }

    async def _handle_list(self, patient_id: str) -> dict[str, object]:
        bookings = await self.appointment_service.list_bookings(patient_id)
        if not bookings:
            return {
                "message": "Kayıtlı aktif randevu bulunmuyor.",
                "ui_action": "show_appointment_options",
                "payload": {"action": "list", "bookings": []},
                "sources": [],
            }

        booking_payload = [self._booking_payload(booking) for booking in bookings]
        return {
            "message": "Kayıtlı randevularınızı listeledim.",
            "ui_action": "show_appointment_options",
            "payload": {"action": "list", "bookings": booking_payload},
            "sources": [],
        }

    async def _handle_cancel(
        self,
        patient_id: str,
        preferences: AppointmentPreferences,
    ) -> dict[str, object]:
        bookings = await self.appointment_service.list_bookings(patient_id)
        if not bookings:
            return {
                "message": "İptal edilebilecek kayıtlı bir randevu bulunmuyor.",
                "ui_action": "show_appointment_options",
                "payload": {"action": "cancel", "cancelled": False, "bookings": []},
                "sources": [],
            }

        target = None
        if preferences.booking_id:
            target = next((booking for booking in bookings if booking.booking_id == preferences.booking_id), None)
        if target is None:
            target = bookings[0]

        cancelled = await self.appointment_service.cancel_booking(
            patient_id=patient_id,
            booking_id=target.booking_id,
        )
        if cancelled is None:
            return {
                "message": "Seçilen randevu iptal edilemedi.",
                "ui_action": "show_appointment_options",
                "payload": {"action": "cancel", "cancelled": False, "bookings": [self._booking_payload(target)]},
                "sources": [],
            }

        return {
            "message": f"{cancelled.slot.hospital_name} için randevunuz iptal edildi.",
            "ui_action": "show_appointment_options",
            "payload": {
                "action": "cancel",
                "cancelled": True,
                "booking": self._booking_payload(cancelled),
            },
            "sources": [],
        }

    async def _handle_booking(
        self,
        patient_id: str,
        preferences: AppointmentPreferences,
        slots: list[AppointmentSlot],
        slot_payload: list[dict[str, object]],
        *,
        relaxed_search: bool,
        fallback_note: str | None,
    ) -> dict[str, object]:
        if not slots:
            return {
                "message": "Bu kriterlerde müsait slot bulunamadı. Farklı tarih veya hastane deneyebiliriz.",
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "book",
                    "booked": False,
                    "slot_options": [],
                    "requested": self._requested_payload(preferences),
                },
                "sources": [],
            }

        if (
            relaxed_search
            and preferences.slot_id is None
            and preferences.selection_index is None
        ):
            return {
                "message": (
                    f"{fallback_note or 'Belirttiğiniz koşullara tam uyan boş slot bulunamadı; en yakın seçenekleri listeledim.'} "
                    "İsterseniz 'ilkini al' ya da slot numarasıyla belirli bir seçeneği onaylayabilirsiniz."
                ),
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "book",
                    "booked": False,
                    "requires_slot_selection": True,
                    "slot_options": slot_payload,
                    "follow_up_question": "Bu alternatiflerden hangisini onaylayayım?",
                },
                "sources": [],
            }

        chosen_slot = self.appointment_service.pick_slot_from_preferences(
            slots=slots,
            preferences=preferences,
        )
        if chosen_slot is None and self._can_auto_select_slot(preferences, slots) and not relaxed_search:
            chosen_slot = slots[0]
        if chosen_slot is None and relaxed_search:
            return {
                "message": (
                    f"{fallback_note or 'Tam eşleşen boş slot bulunamadı; en yakın seçenekleri listeledim.'} "
                    "Uygun görürseniz 'ilkini al' ya da slot numarasıyla devam edebilirsiniz."
                ),
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "book",
                    "booked": False,
                    "requires_slot_selection": True,
                    "slot_options": slot_payload,
                    "follow_up_question": "Bu alternatiflerden hangisini onaylayayım?",
                },
                "sources": [],
            }
        if chosen_slot is None:
            return {
                "message": "Birden fazla uygun slot buldum. Rezervasyon için slot numarasını veya 'ilkini al' ifadesini belirtmeniz gerekiyor.",
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "book",
                    "booked": False,
                    "requires_slot_selection": True,
                    "slot_options": slot_payload,
                    "follow_up_question": "Hangi slotu onaylayayım?",
                },
                "sources": [],
            }

        try:
            booking = await self.appointment_service.book_slot(
                patient_id=patient_id,
                slot_id=chosen_slot.slot_id,
                city=chosen_slot.city,
            )
        except ValueError as error:
            return {
                "message": str(error),
                "ui_action": "show_appointment_options",
                "payload": {
                    "action": "book",
                    "booked": False,
                    "slot_options": slot_payload,
                },
                "sources": [],
            }

        return {
            "message": booking.confirmation_message(),
            "ui_action": "show_appointment_options",
            "payload": {
                "action": "book",
                "booked": True,
                "booking": self._booking_payload(booking),
                "slot_options": slot_payload,
            },
            "sources": [],
        }

    def _slot_payload(self, slot: AppointmentSlot) -> dict[str, object]:
        return {
            "slot_id": slot.slot_id,
            "hospital_name": slot.hospital_name,
            "city": slot.city,
            "physician_name": slot.physician_name,
            "specialty": slot.specialty,
            "start_at": slot.start_at.isoformat(),
            "hour": slot.start_at.hour,
            "display_text": slot.as_text(),
        }

    def _booking_payload(self, booking: AppointmentBooking) -> dict[str, object]:
        return {
            "booking_id": booking.booking_id,
            "status": booking.status.value,
            "slot": self._slot_payload(booking.slot),
        }

    def _requested_payload(
        self,
        preferences: AppointmentPreferences,
    ) -> dict[str, object]:
        return {
            "specialty": preferences.specialty,
            "city": preferences.city,
            "hospital_name": preferences.hospital_name,
            "physician_name": preferences.physician_name,
            "preferred_date": (
                preferences.preferred_date.isoformat()
                if preferences.preferred_date
                else None
            ),
            "preferred_hour": preferences.preferred_hour,
            "city_inferred": preferences.city_inferred,
            "preferred_date_explicit": preferences.preferred_date_explicit,
            "preferred_hour_explicit": preferences.preferred_hour_explicit,
        }

    def _can_auto_select_slot(
        self,
        preferences: AppointmentPreferences,
        slots: list[AppointmentSlot],
    ) -> bool:
        if not slots:
            return False
        if len(slots) == 1:
            return True
        if preferences.physician_name or preferences.hospital_name:
            return True
        if preferences.preferred_date is not None and preferences.preferred_hour is not None:
            return True
        return False

    async def _build_preferences(self, query: HealthQuery) -> AppointmentPreferences:
        direct_preferences = self.appointment_service.extract_preferences(query.text)
        recent_messages = []
        if query.conversation_id is not None:
            recent_messages = await self.user_history_repository.list_recent_messages(
                conversation_id=query.conversation_id,
                limit=6,
            )

        user_context = " ".join(
            message.content
            for message in recent_messages
            if message.role == "user"
        )
        combined_context = " ".join(
            part for part in (query.text, user_context) if part.strip()
        )
        history_preferences = self.appointment_service.extract_preferences(user_context)

        profile = await self.user_history_repository.get_patient_profile(query.patient_id)
        recent_context = "\n".join(
            f"{message.role}: {message.content}"
            for message in recent_messages
        )
        llm_preferences = await self._extract_llm_preferences(
            query=query,
            recent_context=recent_context,
            profile_city=profile.city if profile else None,
        )
        symptom_guidance = self.symptom_guidance_service.analyze(query.text)
        should_override_llm_specialty = (
            direct_preferences.specialty is None
            and history_preferences.specialty is None
            and symptom_guidance.primary_specialty is not None
            and llm_preferences.specialty is not None
            and llm_preferences.specialty != symptom_guidance.primary_specialty
            and symptom_guidance.confidence >= 0.45
        )
        inferred_specialty = (
            symptom_guidance.primary_specialty
            if (
                direct_preferences.specialty is None
                and history_preferences.specialty is None
                and (
                    llm_preferences.specialty is None
                    or should_override_llm_specialty
                )
            )
            else None
        )
        has_explicit_city = any(
            value
            for value in (
                direct_preferences.city,
                llm_preferences.city,
                history_preferences.city,
            )
        )
        has_explicit_date = self.appointment_service.has_explicit_date_reference(
            combined_context
        )
        has_explicit_hour = self.appointment_service.has_explicit_hour_reference(
            combined_context
        )
        resolved_hour = (
            direct_preferences.preferred_hour
            if direct_preferences.preferred_hour is not None
            else llm_preferences.preferred_hour
            if has_explicit_hour and llm_preferences.preferred_hour is not None
            else history_preferences.preferred_hour
        )

        return AppointmentPreferences(
            action=self._merge_action(
                direct_preferences=direct_preferences,
                llm_preferences=llm_preferences,
                history_preferences=history_preferences,
            ),
            specialty=(
                direct_preferences.specialty
                or (
                    symptom_guidance.primary_specialty
                    if should_override_llm_specialty
                    else llm_preferences.specialty
                )
                or history_preferences.specialty
                or inferred_specialty
            ),
            specialty_inferred=inferred_specialty is not None,
            specialty_reason=(
                symptom_guidance.rationale if inferred_specialty is not None else None
            ),
            city=(
                direct_preferences.city
                or llm_preferences.city
                or history_preferences.city
                or (profile.city if profile else None)
            ),
            city_inferred=not has_explicit_city and profile is not None and profile.city is not None,
            hospital_name=(
                direct_preferences.hospital_name
                or llm_preferences.hospital_name
                or history_preferences.hospital_name
            ),
            physician_name=(
                direct_preferences.physician_name
                or llm_preferences.physician_name
                or history_preferences.physician_name
            ),
            preferred_date=(
                direct_preferences.preferred_date
                or llm_preferences.preferred_date
                or history_preferences.preferred_date
            ),
            preferred_date_explicit=has_explicit_date,
            preferred_hour=resolved_hour,
            preferred_hour_explicit=has_explicit_hour,
            slot_id=(
                direct_preferences.slot_id
                or llm_preferences.slot_id
                or history_preferences.slot_id
            ),
            booking_id=(
                direct_preferences.booking_id
                or llm_preferences.booking_id
                or history_preferences.booking_id
            ),
            selection_index=(
                direct_preferences.selection_index
                if direct_preferences.selection_index is not None
                else llm_preferences.selection_index
            ),
        )

    async def _extract_llm_preferences(
        self,
        *,
        query: HealthQuery,
        recent_context: str,
        profile_city: str | None,
    ) -> AppointmentPreferences:
        payload = await self.llm_engine.generate_structured_output(
            system_prompt=(
                "Sen yalnızca randevu niyeti ve parametre çıkaran bir yardımcı "
                "bileşensin. Tanı koyma veya açıklama yapma. Kullanıcının mevcut "
                "mesajını ve yakın konuşma bağlamını kullanarak sadece geçerli "
                "JSON dön. action alanı search, book, cancel veya list olabilir. "
                "specialty alanında bölümü Türkçe resmî adıyla döndürmeye çalış. "
                "selection_index sıfır tabanlı olsun; 'ilkini al' için 0 dön."
            ),
            user_prompt=(
                f"Kullanıcı profili varsayılan şehri: {profile_city or 'yok'}\n"
                f"Yakın konuşma bağlamı:\n{recent_context or 'Bağlam yok.'}\n\n"
                f"Güncel kullanıcı mesajı:\n{query.text}"
            ),
            schema_hint=(
                "{"
                '"action":"search|book|cancel|list",'
                '"specialty":"string|null",'
                '"city":"string|null",'
                '"hospital_name":"string|null",'
                '"physician_name":"string|null",'
                '"preferred_date":"YYYY-MM-DD|null",'
                '"preferred_hour":0,'
                '"slot_id":"string|null",'
                '"booking_id":"string|null",'
                '"selection_index":0'
                "}"
            ),
        )
        if payload is None:
            return AppointmentPreferences(action="search")

        specialty = self._normalize_specialty(self._string_or_none(payload.get("specialty")))
        preferred_date = self._date_or_none(payload.get("preferred_date"))
        preferred_hour = self._hour_or_none(payload.get("preferred_hour"))
        selection_index = self._selection_index_or_none(payload.get("selection_index"))
        action = self._string_or_none(payload.get("action")) or "search"

        return AppointmentPreferences(
            action=action if action in {"search", "book", "cancel", "list"} else "search",
            specialty=specialty,
            city=self._title_or_none(payload.get("city")),
            hospital_name=self._title_or_none(payload.get("hospital_name")),
            physician_name=self._string_or_none(payload.get("physician_name")),
            preferred_date=preferred_date,
            preferred_hour=preferred_hour,
            slot_id=self._string_or_none(payload.get("slot_id")),
            booking_id=self._string_or_none(payload.get("booking_id")),
            selection_index=selection_index,
        )

    def _merge_action(
        self,
        *,
        direct_preferences: AppointmentPreferences,
        llm_preferences: AppointmentPreferences,
        history_preferences: AppointmentPreferences,
    ) -> str:
        if direct_preferences.action != "search":
            return direct_preferences.action
        if llm_preferences.action != "search":
            return llm_preferences.action
        if history_preferences.action == "list" and (
            llm_preferences.selection_index is not None
            or llm_preferences.slot_id is not None
            or direct_preferences.selection_index is not None
            or direct_preferences.slot_id is not None
        ):
            return "book"
        return "search"

    def _normalize_specialty(self, value: str | None) -> str | None:
        if value is None:
            return None
        extracted = self.appointment_service.extract_preferences(value).specialty
        return extracted or value

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        normalized = text.lower().replace(" ", "")
        invalid_placeholders = {
            "null",
            "none",
            "yok",
            "string",
            "string|null",
            "string/null",
            "str|null",
            "yyyy-mm-dd|null",
        }
        if not text or normalized in invalid_placeholders:
            return None
        return text

    def _title_or_none(self, value: Any) -> str | None:
        text = self._string_or_none(value)
        return text.title() if text else None

    def _date_or_none(self, value: Any) -> date | None:
        text = self._string_or_none(value)
        if text is None:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    def _hour_or_none(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            hour = int(value)
        except (TypeError, ValueError):
            return None
        return hour if 0 <= hour <= 23 else None

    def _selection_index_or_none(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        return index if index >= 0 else None
