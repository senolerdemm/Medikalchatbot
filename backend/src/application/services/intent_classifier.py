from __future__ import annotations

import re

from domain.entities.health_query import HealthQuery, QueryIntent
from domain.ports.ai.llm_engine import LLMEngine
from domain.ports.repositories.user_history_repository import (
    UserHistoryRepository,
)


class IntentClassifier:
    """
    Intent kararini gereksiz yere randevuya itmeden verir.

    1. Acik ve guvenli rule-based kararlar once alinir.
    2. Belirsiz veya follow-up mesajlarda LLM devreye girer.
    3. LLM yanit veremezse fallback yine rule-based olur.
    """

    HISTORY_KEYWORDS = (
        "gecmis",
        "kayit",
        "tahlil",
        "sonuc",
        "ilac",
        "alerji",
        "onceki",
        "rapor",
        "ozet",
        "gecirdigim",
        "profilim",
        "kayitlarim",
        "gecmisime gore",
    )

    APPOINTMENT_KEYWORDS = (
        "randevu",
        "muayene",
        "slot",
        "rezerv",
        "rezervasyon",
        "randevularim",
        "poliklinik",
        "iptal",
        "ilkini",
        "ikinciyi",
        "ucuncuyu",
        "onayla",
        "ayarla",
        "ayir",
        "booking",
    )

    APPOINTMENT_SEARCH_TERMS = (
        "uygun",
        "goster",
        "gor",
        "bak",
        "ara",
        "bul",
        "var mi",
        "müsait",
        "musait",
    )

    TIME_TERMS = (
        "yarin",
        "bugun",
        "saat",
        "pazartesi",
        "sali",
        "carsamba",
        "persembe",
        "cuma",
        "cumartesi",
        "pazar",
    )

    LOCATION_TERMS = (
        "ankara",
        "istanbul",
        "eskisehir",
        "izmir",
        "bursa",
        "hastane",
        "acibadem",
        "memorial",
        "medipol",
        "liv hospital",
        "universite hastanesi",
        "sehir hastanesi",
    )

    SPECIALTY_TERMS = (
        "kardiyo",
        "kalp",
        "gastro",
        "reflu",
        "mide",
        "endokrin",
        "diyabet",
        "seker",
        "tiroid",
        "gogus",
        "akciger",
        "kbb",
        "kulak",
        "burun",
        "bogaz",
        "dermat",
        "cilt",
        "dahiliye",
        "noroloji",
        "noro",
        "ortopedi",
        "psikiyatri",
        "psikolog",
        "psikolojik",
        "goz",
        "uroloji",
        "nefroloji",
        "romatoloji",
        "hematoloji",
        "onkoloji",
        "pediatri",
        "cocuk",
        "kadin dogum",
        "jinekoloji",
        "genel cerrahi",
        "fizik tedavi",
    )

    INFORMATION_KEYWORDS = (
        "neden",
        "nedir",
        "niye",
        "ne olabilir",
        "olabilir mi",
        "belirti",
        "semptom",
        "sebep",
        "sebebi",
        "acil mi",
        "normal mi",
        "iyi gelir",
        "ne yapmaliyim",
        "hangi bran",
        "hangi bolum",
        "hangi doktora gitmeliyim",
        "rahatsizligim var",
        "agri",
        "ates",
        "oksuruk",
        "bas agrisi",
        "mide",
        "carpinti",
        "nefes",
    )

    def __init__(
        self,
        *,
        llm_engine: LLMEngine | None = None,
        user_history_repository: UserHistoryRepository | None = None,
    ) -> None:
        self.llm_engine = llm_engine
        self.user_history_repository = user_history_repository

    async def classify(self, query: HealthQuery) -> QueryIntent:
        normalized_text = query.normalized_text()
        heuristic_intent = self._classify_with_rules(normalized_text)

        if self._is_confident_rule_decision(
            normalized_text=normalized_text,
            heuristic_intent=heuristic_intent,
            query=query,
        ):
            return heuristic_intent

        if self.llm_engine is None:
            return heuristic_intent

        recent_context = await self._recent_conversation_context(query)
        llm_intent = await self._classify_with_llm(
            query_text=query.text,
            recent_context=recent_context,
        )
        if llm_intent is not None:
            return llm_intent
        return heuristic_intent

    def _classify_with_rules(self, normalized_text: str) -> QueryIntent:
        has_history = self._contains_any(normalized_text, self.HISTORY_KEYWORDS)
        has_explicit_appointment = self._contains_any(
            normalized_text,
            self.APPOINTMENT_KEYWORDS,
        )
        looks_like_appointment_search = self._looks_like_appointment_search(
            normalized_text
        )
        looks_like_information = self._looks_like_information(normalized_text)

        if has_history and not has_explicit_appointment:
            return QueryIntent.PERSONAL_HISTORY
        if looks_like_information and not has_explicit_appointment:
            return QueryIntent.INFORMATION
        if has_explicit_appointment or looks_like_appointment_search:
            return QueryIntent.APPOINTMENT
        return QueryIntent.INFORMATION

    def _is_confident_rule_decision(
        self,
        *,
        normalized_text: str,
        heuristic_intent: QueryIntent,
        query: HealthQuery,
    ) -> bool:
        if heuristic_intent is QueryIntent.PERSONAL_HISTORY:
            return True

        has_explicit_appointment = self._contains_any(
            normalized_text,
            self.APPOINTMENT_KEYWORDS,
        )
        looks_like_appointment_search = self._looks_like_appointment_search(
            normalized_text
        )
        looks_like_information = self._looks_like_information(normalized_text)

        if heuristic_intent is QueryIntent.APPOINTMENT:
            return has_explicit_appointment or looks_like_appointment_search

        if heuristic_intent is QueryIntent.INFORMATION and (
            looks_like_information
            or (
                not has_explicit_appointment
                and not looks_like_appointment_search
                and query.conversation_id is None
            )
        ):
            return True

        return False

    def _looks_like_appointment_search(self, normalized_text: str) -> bool:
        has_search_term = self._contains_word_or_phrase(
            normalized_text,
            self.APPOINTMENT_SEARCH_TERMS,
        )
        has_specialty = self._contains_any(normalized_text, self.SPECIALTY_TERMS)
        has_location = self._contains_any(normalized_text, self.LOCATION_TERMS)
        has_time = self._contains_any(normalized_text, self.TIME_TERMS)

        if has_search_term and (has_specialty or has_location or has_time):
            return True
        if has_specialty and has_time:
            return True
        return False

    def _looks_like_information(self, normalized_text: str) -> bool:
        if self._contains_any(normalized_text, self.INFORMATION_KEYWORDS):
            return True
        if "hangi doktora gitmeliyim" in normalized_text:
            return True
        if "hangi bolume gitmeliyim" in normalized_text:
            return True
        return False

    async def _classify_with_llm(
        self,
        *,
        query_text: str,
        recent_context: str,
    ) -> QueryIntent | None:
        response = await self.llm_engine.generate_structured_output(
            system_prompt=(
                "Sen bir medikal sohbet yönlendiricisisin. "
                "Kullanıcının isteğini yalnızca şu intentlerden birine ata: "
                "information, appointment, personal_history.\n"
                "- information: semptom, olası neden, genel tıbbi bilgi, hangi "
                "branşa gitmesi gerektiği, risk veya aciliyet soruları.\n"
                "- appointment: randevu arama, uygun doktor/slot gösterme, "
                "rezervasyon, iptal veya mevcut randevuları listeleme.\n"
                "- personal_history: kullanıcının kendi kayıtları, ilaçları, "
                "tahlilleri, önceki görüşmeleri veya profiline dair özet.\n"
                "Semptom anlatımı tek başına appointment değildir. Kullanıcı "
                "gerçekten randevu aramıyorsa appointment seçme."
            ),
            user_prompt=(
                f"Güncel kullanıcı mesajı:\n{query_text}\n\n"
                f"Yakın konuşma bağlamı:\n{recent_context or 'Bağlam yok.'}"
            ),
            schema_hint=(
                '{"intent":"information|appointment|personal_history",'
                '"reason":"kisa aciklama","confidence":0.0}'
            ),
        )
        if response is None:
            return None

        raw_intent = str(response.get("intent", "")).strip().lower()
        if raw_intent == QueryIntent.INFORMATION.value:
            return QueryIntent.INFORMATION
        if raw_intent == QueryIntent.APPOINTMENT.value:
            return QueryIntent.APPOINTMENT
        if raw_intent == QueryIntent.PERSONAL_HISTORY.value:
            return QueryIntent.PERSONAL_HISTORY
        return None

    async def _recent_conversation_context(self, query: HealthQuery) -> str:
        if (
            query.conversation_id is None
            or self.user_history_repository is None
        ):
            return ""
        recent_messages = await self.user_history_repository.list_recent_messages(
            conversation_id=query.conversation_id,
            limit=6,
        )
        if not recent_messages:
            return ""
        return "\n".join(
            f"{message.role}: {message.content}"
            for message in recent_messages
        )

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _contains_word_or_phrase(self, text: str, keywords: tuple[str, ...]) -> bool:
        for keyword in keywords:
            escaped = re.escape(keyword)
            if " " in keyword:
                pattern = rf"(?<!\w){escaped}(?!\w)"
            else:
                pattern = rf"\b{escaped}\b"
            if re.search(pattern, text):
                return True
        return False
