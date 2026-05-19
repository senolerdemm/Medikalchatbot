from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from domain.entities.appointment import (
    APPOINTMENT_TIMEZONE,
    AppointmentBooking,
    AppointmentStatus,
)
from domain.entities.health_query import HealthQuery
from domain.entities.patient import ConversationMessage, PatientHistoryEntry, PatientProfile
from domain.ports.ai.llm_engine import LLMEngine
from domain.ports.repositories.appointment_repository import AppointmentRepository
from domain.ports.repositories.user_history_repository import (
    UserHistoryRepository,
)


@dataclass(slots=True)
class PersonalContext:
    profile: PatientProfile | None
    history_entries: list[PatientHistoryEntry]
    recent_messages: list[ConversationMessage]
    bookings: list[AppointmentBooking]
    medications: list[str]
    allergy_notes: list[str]
    lab_entries: list[PatientHistoryEntry]
    visit_entries: list[PatientHistoryEntry]
    medication_entries: list[PatientHistoryEntry]
    interaction_entries: list[PatientHistoryEntry]
    upcoming_bookings: list[AppointmentBooking]
    cancelled_bookings: list[AppointmentBooking]


class PersonalAgent:
    SUMMARY_KEYWORDS = (
        "ozet",
        "durumum",
        "profil",
        "genel durum",
        "gecmisime gore",
        "beni ozetle",
        "kayitlarima gore",
    )
    MEDICATION_KEYWORDS = ("ilac", "ilaclar", "recete")
    ALLERGY_KEYWORDS = ("alerji", "alerjik")
    LAB_KEYWORDS = ("tahlil", "sonuc", "lab", "kan degeri", "hba1c")
    APPOINTMENT_KEYWORDS = ("randevu", "kontrol", "muayene")
    VISIT_KEYWORDS = ("ziyaret", "poliklinik", "muayene oldum", "gitmistim")
    CONVERSATION_KEYWORDS = (
        "sohbet",
        "konusma",
        "mesaj",
        "az once",
        "ne demistik",
        "ne konustuk",
    )
    RECOMMENDATION_KEYWORDS = (
        "oner",
        "oneri",
        "dikkat etmeliyim",
        "ne yapmaliyim",
        "sence nasil",
    )

    def __init__(
        self,
        user_history_repository: UserHistoryRepository,
        appointment_repository: AppointmentRepository,
        llm_engine: LLMEngine,
    ):
        self.user_history_repository = user_history_repository
        self.appointment_repository = appointment_repository
        self.llm_engine = llm_engine

    async def handle_history_query(
        self,
        query: HealthQuery,
    ) -> dict[str, object]:
        profile = await self.user_history_repository.get_patient_profile(
            query.patient_id
        )
        history_entries = await self.user_history_repository.list_history_entries(
            query.patient_id,
            limit=20,
        )
        recent_messages: list[ConversationMessage] = []
        if query.conversation_id is not None:
            recent_messages = await self.user_history_repository.list_recent_messages(
                conversation_id=query.conversation_id,
                limit=10,
            )
        bookings = await self.appointment_repository.list_bookings(query.patient_id)

        context = self._build_context(
            profile=profile,
            history_entries=history_entries,
            recent_messages=recent_messages,
            bookings=bookings,
        )
        focus_areas = self._detect_focus_areas(query.text)
        conversation_summary = await self._summarize_recent_conversation(
            query_text=query.text,
            recent_messages=recent_messages,
        )
        direct_response = self._build_direct_fact_response(
            focus_areas=focus_areas,
            context=context,
            conversation_summary=conversation_summary,
        )
        if direct_response is not None:
            response = direct_response
        else:
            response = await self._build_grounded_llm_response(
                query=query,
                context=context,
                focus_areas=focus_areas,
                conversation_summary=conversation_summary,
            )

        return {
            "message": response,
            "ui_action": "show_history_summary",
                "payload": {
                    "focus_areas": focus_areas,
                    "profile_summary": profile.summary() if profile else "Kayıt bulunamadı.",
                "history_entries": [
                    {
                        "type": entry.entry_type,
                        "summary": entry.summary,
                        "recorded_at": entry.recorded_at.isoformat(),
                    }
                    for entry in context.history_entries
                ],
                "upcoming_appointments": [
                    self._booking_payload(booking)
                    for booking in context.upcoming_bookings
                ],
                "cancelled_appointments": [
                    self._booking_payload(booking)
                    for booking in context.cancelled_bookings
                ],
                "medications": context.medications,
                "allergy_notes": context.allergy_notes,
                "conversation_summary": conversation_summary,
                "recent_messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                    }
                    for message in context.recent_messages
                ],
            },
            "sources": [],
        }

    def _build_context(
        self,
        *,
        profile: PatientProfile | None,
        history_entries: list[PatientHistoryEntry],
        recent_messages: list[ConversationMessage],
        bookings: list[AppointmentBooking],
    ) -> PersonalContext:
        clinical_history = [
            entry
            for entry in history_entries
            if entry.entry_type != "interaction"
        ]
        interaction_entries = [
            entry
            for entry in history_entries
            if entry.entry_type == "interaction"
        ]
        medications = self._collect_medications(profile, clinical_history)
        allergy_notes = self._collect_allergy_notes(profile, clinical_history)
        lab_entries = [
            entry for entry in clinical_history if entry.entry_type == "lab"
        ]
        visit_entries = [
            entry
            for entry in clinical_history
            if entry.entry_type in {"visit", "appointment"}
        ]
        medication_entries = [
            entry
            for entry in clinical_history
            if entry.entry_type == "medication"
        ]
        now = datetime.now(APPOINTMENT_TIMEZONE)
        upcoming_bookings = [
            booking
            for booking in bookings
            if booking.status is AppointmentStatus.CONFIRMED
            and self._booking_start_at(booking) >= now
        ]
        cancelled_bookings = [
            booking
            for booking in bookings
            if booking.status is AppointmentStatus.CANCELLED
        ]
        return PersonalContext(
            profile=profile,
            history_entries=clinical_history,
            recent_messages=recent_messages,
            bookings=bookings,
            medications=medications,
            allergy_notes=allergy_notes,
            lab_entries=lab_entries,
            visit_entries=visit_entries,
            medication_entries=medication_entries,
            interaction_entries=interaction_entries,
            upcoming_bookings=upcoming_bookings,
            cancelled_bookings=cancelled_bookings,
        )

    def _detect_focus_areas(self, query_text: str) -> list[str]:
        normalized = self._normalize(query_text)
        focus_areas: list[str] = []
        if self._contains_any(normalized, self.MEDICATION_KEYWORDS):
            focus_areas.append("medications")
        if self._contains_any(normalized, self.ALLERGY_KEYWORDS):
            focus_areas.append("allergies")
        if self._contains_any(normalized, self.LAB_KEYWORDS):
            focus_areas.append("labs")
        if self._contains_any(normalized, self.APPOINTMENT_KEYWORDS):
            focus_areas.append("appointments")
        if self._contains_any(normalized, self.VISIT_KEYWORDS):
            focus_areas.append("visits")
        if self._contains_any(normalized, self.CONVERSATION_KEYWORDS):
            focus_areas.append("conversation")
        if self._contains_any(normalized, self.RECOMMENDATION_KEYWORDS):
            focus_areas.append("recommendation")
        if not focus_areas or self._contains_any(normalized, self.SUMMARY_KEYWORDS):
            focus_areas.append("summary")
        return list(dict.fromkeys(focus_areas))

    async def _summarize_recent_conversation(
        self,
        *,
        query_text: str,
        recent_messages: list[ConversationMessage],
    ) -> str:
        if not recent_messages:
            return ""

        user_messages = [
            message.content
            for message in recent_messages
            if message.role == "user"
        ]
        if not user_messages:
            return ""
        return "Yakın konuşmada öne çıkan kullanıcı konuları: " + "; ".join(
            user_messages[-3:]
        )

    def _build_direct_fact_response(
        self,
        *,
        focus_areas: list[str],
        context: PersonalContext,
        conversation_summary: str,
    ) -> str | None:
        non_summary_focus = [
            area
            for area in focus_areas
            if area not in {"summary", "recommendation"}
        ]
        if "summary" in focus_areas and not non_summary_focus:
            return self._build_fallback_summary(
                context=context,
                focus_areas=focus_areas,
                conversation_summary=conversation_summary,
            )
        if len(non_summary_focus) != 1:
            return None

        focus = non_summary_focus[0]
        if focus == "medications":
            if context.medications:
                return (
                    "Kayıtlarınıza göre düzenli ilaçlarınız: "
                    + ", ".join(context.medications)
                    + "."
                )
            return "Kayıtlarınızda ilaç bilgisi bulunmuyor."

        if focus == "allergies":
            if context.allergy_notes:
                return (
                    "Kayıtlarınızdaki alerji veya alerjiyle ilişkili notlar: "
                    + "; ".join(context.allergy_notes[:3])
                    + "."
                )
            return "Kayıtlarınızda açık bir alerji bilgisi bulunmuyor."

        if focus == "labs":
            if not context.lab_entries:
                return "Kayıtlarınızda tahlil veya laboratuvar sonucu bulunmuyor."
            latest = [
                f"{entry.recorded_at.strftime('%d.%m.%Y')}: {entry.summary}"
                for entry in context.lab_entries[:3]
            ]
            return "Son laboratuvar kayıtlarınız:\n- " + "\n- ".join(latest)

        if focus == "appointments":
            if not context.bookings:
                return "Kayıtlı randevu bulunmuyor."
            lines = []
            if context.upcoming_bookings:
                lines.append("Aktif randevularınız:")
                lines.extend(
                    f"- {self._format_booking_line(booking)}"
                    for booking in context.upcoming_bookings[:4]
                )
            if context.cancelled_bookings:
                lines.append("İptal edilmiş kayıtlar:")
                lines.extend(
                    f"- {self._format_booking_line(booking)}"
                    for booking in context.cancelled_bookings[:2]
                )
            if not lines:
                lines.append("Kayıtlı randevu geçmişi:")
                lines.extend(
                    f"- {self._format_booking_line(booking)}"
                    for booking in context.bookings[:4]
                )
            return "\n".join(lines) if lines else "Kayıtlı randevu bulunmuyor."

        if focus == "visits":
            if not context.visit_entries:
                return "Kayıtlarınızda ziyaret veya kontrol özeti bulunmuyor."
            latest_visits = [
                f"{entry.recorded_at.strftime('%d.%m.%Y')}: {entry.summary}"
                for entry in context.visit_entries[:4]
            ]
            return "Son ziyaret ve kontrol kayıtlarınız:\n- " + "\n- ".join(
                latest_visits
            )

        if focus == "conversation":
            if conversation_summary:
                return f"Yakın sohbet özeti: {conversation_summary}"
            if context.recent_messages:
                latest_messages = [
                    f"{self._role_label(message.role)}: {message.content}"
                    for message in context.recent_messages[-4:]
                ]
                return "Yakın sohbet kayıtları:\n- " + "\n- ".join(latest_messages)
            return "Bu konuşma için okunabilir son mesaj kaydı bulunmuyor."

        return None

    async def _build_grounded_llm_response(
        self,
        *,
        query: HealthQuery,
        context: PersonalContext,
        focus_areas: list[str],
        conversation_summary: str,
    ) -> str:
        prompt = self._build_grounded_prompt(
            query_text=query.text,
            context=context,
            focus_areas=focus_areas,
            conversation_summary=conversation_summary,
        )
        response = await self.llm_engine.generate_response(
            system_prompt=(
                "Sen kullanıcının kendi sağlık kayıtlarını açıklayan bir "
                "Personal History Agent'sin. Kurallar:\n"
                "1. Yalnızca verilen kayıtlara dayan.\n"
                "2. Kayıtlarda olmayan bilgi, tanı, ilaç veya randevu uydurma.\n"
                "3. Belirsiz veya eksik alan varsa bunu açıkça belirt.\n"
                "4. Kullanıcı ilaç, alerji, tahlil, randevu veya önceki sohbet "
                "soruyorsa doğrudan onu cevapla.\n"
                "5. Kesin tanı koyma; gerekirse 'kayıtlar tanı için yeterli değil' "
                "de.\n"
                "6. Kullanıcı ne yapması gerektiğini sorarsa, yalnızca kayıtlardan "
                "çıkabilen güvenli ve genel sonraki adımları öner.\n"
                "7. Cevabı yalnızca Türkçe yaz.\n"
                "8. İngilizce etiket, rol adı, başlık veya durum ifadesi kullanma.\n"
                "9. Gerekirse teknik terimleri Türkçe karşılıklarıyla açıkla."
            ),
            user_prompt=prompt,
        )
        cleaned = self._turkify_common_terms(response.strip())
        cleaned = self._remove_incomplete_tail(cleaned)
        if (
            cleaned
            and not self._looks_like_missing_profile_fallback(cleaned, context)
            and not self._looks_truncated(cleaned)
        ):
            return cleaned
        return self._build_fallback_summary(
            context=context,
            focus_areas=focus_areas,
            conversation_summary=conversation_summary,
        )

    def _build_grounded_prompt(
        self,
        *,
        query_text: str,
        context: PersonalContext,
        focus_areas: list[str],
        conversation_summary: str,
    ) -> str:
        profile_summary = (
            context.profile.summary()
            if context.profile
            else "Hasta profili bulunamadı."
        )
        history_lines = [
            f"- [{self._entry_type_label(entry.entry_type)}] {entry.summary} ({entry.recorded_at.strftime('%d.%m.%Y')})"
            for entry in context.history_entries[:8]
        ] or ["- Klinik kayıt bulunamadı."]
        appointment_lines = [
            f"- {self._format_booking_line(booking)}"
            for booking in context.bookings[:6]
        ] or ["- Kayıtlı randevu yok."]
        interaction_lines = [
            f"- {entry.summary} ({entry.recorded_at.strftime('%d.%m.%Y')})"
            for entry in context.interaction_entries[:3]
        ] or ["- Ayrıca etkileşim özeti yok."]
        recent_messages = [
            f"- {self._role_label(message.role)}: {message.content}"
            for message in context.recent_messages[-6:]
        ] or ["- Yakın mesaj kaydı yok."]
        focus_labels = ", ".join(self._focus_label(area) for area in focus_areas)

        return (
            f"Kullanıcı sorusu: {query_text}\n"
            f"Odak alanları: {focus_labels}\n\n"
            f"Hasta profili:\n{profile_summary}\n\n"
            "Düzenli ilaçlar:\n"
            + (
                "\n".join(f"- {item}" for item in context.medications)
                if context.medications
                else "- İlaç bilgisi yok."
            )
            + "\n\nAlerji ve ilgili notlar:\n"
            + (
                "\n".join(f"- {item}" for item in context.allergy_notes)
                if context.allergy_notes
                else "- Alerji notu yok."
            )
            + "\n\nKlinik geçmiş kayıtları:\n"
            + "\n".join(history_lines)
            + "\n\nRandevu kayıtları:\n"
            + "\n".join(appointment_lines)
            + "\n\nYakın sohbet özeti:\n"
            + (conversation_summary or "Yakın sohbet özeti yok.")
            + "\n\nHam son mesajlar:\n"
            + "\n".join(recent_messages)
            + "\n\nSon etkileşim özetleri:\n"
            + "\n".join(interaction_lines)
            + "\n\nGörev: Kullanıcı sorusunu sadece bu verilere dayanarak cevapla. "
            "İstersen önce kısa cevap ver, sonra ilgili maddeleri kısa maddeler "
            "hâlinde açıkla."
        )

    def _build_fallback_summary(
        self,
        *,
        context: PersonalContext,
        focus_areas: list[str],
        conversation_summary: str,
    ) -> str:
        profile_summary = (
            context.profile.summary()
            if context.profile
            else "Hasta profili bulunamadı."
        )
        parts = [f"Profil özeti: {self._strip_sentence_end(profile_summary)}."]

        if context.medications and (
            "medications" in focus_areas or "summary" in focus_areas
        ):
            parts.append("Düzenli ilaçlar: " + ", ".join(context.medications) + ".")

        if context.allergy_notes and (
            "allergies" in focus_areas or "summary" in focus_areas
        ):
            parts.append(
                "Alerji veya ilgili notlar: "
                + "; ".join(
                    self._strip_sentence_end(item)
                    for item in context.allergy_notes[:3]
                )
                + "."
            )

        if context.lab_entries and ("labs" in focus_areas or "summary" in focus_areas):
            parts.append(
                "Son laboratuvar kaydı: "
                + self._strip_sentence_end(context.lab_entries[0].summary)
                + f" ({context.lab_entries[0].recorded_at.strftime('%d.%m.%Y')})."
            )

        if context.upcoming_bookings and (
            "appointments" in focus_areas or "summary" in focus_areas
        ):
            parts.append(
                "Yaklaşan randevu: "
                + self._format_booking_line(context.upcoming_bookings[0])
                + "."
            )

        if conversation_summary and (
            "conversation" in focus_areas or "summary" in focus_areas
        ):
            parts.append("Yakın sohbet özeti: " + conversation_summary)

        parts.append(
            "Bu özet yalnızca mevcut kayıtlara dayanır; kayıtlarda yer almayan bilgi için ek değerlendirme gerekir."
        )
        return "\n".join(parts)

    def _strip_sentence_end(self, text: str) -> str:
        return text.strip().rstrip(".!?;:")

    def _remove_incomplete_tail(self, text: str) -> str:
        lines = [line.rstrip() for line in text.strip().splitlines()]
        while lines and self._looks_truncated(lines[-1]):
            lines.pop()
        return "\n".join(lines).strip()

    def _looks_truncated(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True
        dangling_words = {
            "ve",
            "veya",
            "ile",
            "için",
            "icin",
            "bu",
            "şu",
            "su",
            "dan",
            "den",
            "da",
            "de",
            "bir",
            "gibi",
            "olarak",
            "*",
        }
        last_token = stripped.split()[-1].strip(".,;:!?()[]{}\"'").casefold()
        if last_token in dangling_words:
            return True
        if re.search(r"(^|\n)\s*[*-]\s*[a-zçğıöşüA-ZÇĞİÖŞÜ]?\s*$", stripped):
            return True
        return stripped[-1] not in ".!?:)"

    def _looks_like_missing_profile_fallback(
        self,
        text: str,
        context: PersonalContext,
    ) -> bool:
        if context.profile is None:
            return False
        normalized = self._normalize(text)
        return "profil bilgisi yok" in normalized or "hasta profili bulunamadi" in normalized

    def _collect_medications(
        self,
        profile: PatientProfile | None,
        history_entries: list[PatientHistoryEntry],
    ) -> list[str]:
        medications: list[str] = []
        seen: set[str] = set()

        def add(item: str) -> None:
            normalized = " ".join(item.lower().split())
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            medications.append(item.strip())

        if profile is not None:
            for medication in profile.medications:
                add(medication)

        for entry in history_entries:
            if entry.entry_type == "medication":
                add(entry.summary)

        return medications

    def _collect_allergy_notes(
        self,
        profile: PatientProfile | None,
        history_entries: list[PatientHistoryEntry],
    ) -> list[str]:
        notes: list[str] = []
        seen: set[str] = set()

        def add(item: str) -> None:
            normalized = " ".join(item.lower().split())
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            notes.append(item.strip())

        if profile is not None:
            for condition in profile.chronic_conditions:
                if "alerj" in self._normalize(condition):
                    add(condition)
            if profile.notes and "alerj" in self._normalize(profile.notes):
                add(profile.notes)

        for entry in history_entries:
            normalized_summary = self._normalize(entry.summary)
            if entry.entry_type == "allergy" or "alerj" in normalized_summary:
                add(entry.summary)

        return notes

    def _booking_payload(self, booking: AppointmentBooking) -> dict[str, object]:
        start_at = self._booking_start_at(booking)
        return {
            "booking_id": booking.booking_id,
            "status": booking.status.value,
            "status_label": self._status_label(booking.status.value),
            "hospital_name": booking.slot.hospital_name,
            "city": booking.slot.city,
            "physician_name": booking.slot.physician_name,
            "specialty": booking.slot.specialty,
            "start_at": start_at.isoformat(),
            "display_text": self._format_booking_line(booking),
        }

    def _format_booking_line(self, booking: AppointmentBooking) -> str:
        local_time = self._booking_start_at(booking).astimezone(APPOINTMENT_TIMEZONE)
        return (
            f"{booking.slot.hospital_name} / {booking.slot.specialty} / "
            f"{booking.slot.physician_name} / {local_time.strftime('%d.%m.%Y %H:%M')} / "
            f"durum: {self._status_label(booking.status.value)}"
        )

    def _booking_start_at(self, booking: AppointmentBooking) -> datetime:
        start_at = booking.slot.start_at
        if start_at.tzinfo is None:
            return start_at.replace(tzinfo=APPOINTMENT_TIMEZONE)
        return start_at

    def _role_label(self, role: str) -> str:
        normalized = self._normalize(role)
        if normalized in {"user", "kullanici"}:
            return "Kullanıcı"
        if normalized in {"assistant", "asistan"}:
            return "Asistan"
        return "Mesaj"

    def _entry_type_label(self, entry_type: str) -> str:
        labels = {
            "lab": "Tahlil",
            "visit": "Ziyaret",
            "medication": "İlaç",
            "appointment": "Randevu",
            "interaction": "Sohbet",
            "allergy": "Alerji",
        }
        return labels.get(entry_type, entry_type or "Kayıt")

    def _status_label(self, status: str) -> str:
        labels = {
            "confirmed": "Onaylandı",
            "cancelled": "İptal edildi",
            "canceled": "İptal edildi",
            "pending": "Beklemede",
        }
        return labels.get(status, status or "Bilinmiyor")

    def _focus_label(self, focus: str) -> str:
        labels = {
            "summary": "Genel özet",
            "medications": "İlaçlar",
            "allergies": "Alerjiler",
            "labs": "Tahliller",
            "appointments": "Randevular",
            "visits": "Ziyaretler",
            "conversation": "Sohbet hafızası",
            "recommendation": "Genel öneri",
        }
        return labels.get(focus, focus)

    def _turkify_common_terms(self, text: str) -> str:
        if not text:
            return text
        replacements = {
            r"\buser\b": "kullanıcı",
            r"\bassistant\b": "asistan",
            r"\bconfirmed\b": "onaylandı",
            r"\bcancelled\b": "iptal edildi",
            r"\bcanceled\b": "iptal edildi",
            r"\bappointment\b": "randevu",
            r"\bappointments\b": "randevular",
            r"\bmedication\b": "ilaç",
            r"\bmedications\b": "ilaçlar",
            r"\blab\b": "tahlil",
            r"\blabs\b": "tahliller",
            r"\bvisit\b": "ziyaret",
            r"\bvisits\b": "ziyaretler",
            r"\bhistory\b": "geçmiş",
            r"\bsummary\b": "özet",
            r"\bprofile\b": "profil",
            r"\bupcoming\b": "yaklaşan",
            r"\brecent conversation\b": "yakın sohbet",
            r"\brecent messages\b": "son mesajlar",
            r"\bstatus\b": "durum",
        }
        cleaned = text
        for pattern, replacement in replacements.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        return cleaned

    def _normalize(self, text: str) -> str:
        return text.lower().translate(
            str.maketrans(
                {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
            )
        )

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)
