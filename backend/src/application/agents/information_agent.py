from __future__ import annotations

import re

from application.services.rag_service import RAGService
from application.services.symptom_guidance_service import SymptomGuidanceService
from domain.entities.health_query import HealthQuery, RetrievedDocument
from domain.ports.ai.llm_engine import LLMEngine
from domain.ports.repositories.user_history_repository import (
    UserHistoryRepository,
)


class InformationAgent:
    def __init__(
        self,
        rag_service: RAGService,
        llm_engine: LLMEngine,
        user_history_repository: UserHistoryRepository,
        symptom_guidance_service: SymptomGuidanceService,
    ):
        self.rag_service = rag_service
        self.llm_engine = llm_engine
        self.user_history_repository = user_history_repository
        self.symptom_guidance_service = symptom_guidance_service

    async def answer_medical_query(
        self,
        query: HealthQuery,
    ) -> dict[str, object]:
        context_docs = await self.rag_service.retrieve(query.text, k=3)
        source_docs = self._source_display_documents(query.text, context_docs)
        llm_context_docs = source_docs or context_docs[:1]
        normalized_text = query.normalized_text()
        asks_for_specialty = self._asks_for_specialty(normalized_text)
        asks_for_cause = self._asks_for_cause(normalized_text)
        recent_conversation = await self._recent_conversation_context(
            query,
            ignore_appointment_bias=asks_for_cause and not asks_for_specialty,
        )
        guidance = self.symptom_guidance_service.analyze(query.text)
        guidance_prompt = self._guidance_prompt(guidance)
        answer_style_prompt = self._answer_style_prompt(
            asks_for_cause=asks_for_cause,
            asks_for_specialty=asks_for_specialty,
        )
        if context_docs:
            system_prompt = (
                "Sen Türkçe medikal bilgi asistanısın. "
                "Cevaplarını sadece verilen bağlam ve kullanıcının sorusuna dayanarak ver. "
                "Kesin tanı koyma ama olası nedenler, kırmızı bayrak belirtiler, "
                "izlenmesi gereken noktalar ve uygun uzmanlık alanı konusunda yardımcı ol. "
                "Eğer kullanıcı sadece bilgi soruyorsa onu gereksiz yere randevuya yönlendirme. "
                "Yanıtı açık, sakin, kısa ve klinik olarak faydalı şekilde ver. "
                "Belge belge uzun özet yapma; kaynakları arka plan olarak kullan. "
                "En fazla 5 kısa cümle yaz. "
                "Bağlam yeterli değilse bunu söyle; alakasız belgeye dayanarak sonuç uydurma. "
                "Semptomlardan çıkarılan uzmanlık ipucuyla belgeler açıkça çelişmiyorsa o uzmanlık "
                "ipucunu esas al."
            )
        else:
            system_prompt = (
                "Sen Türkçe medikal bilgi asistanısın. "
                "Elinde doğrulanmış bağlam olmadığında da genel tıbbi yönlendirme verebilirsin, "
                "ancak bunu genel bilgi olarak sun. Kesin tanı koyma, ilaç dozu verme veya "
                "gereksiz randevu yönlendirmesi yapma. Olası nedenler, dikkat edilmesi gereken "
                "belirtiler ve uygun uzmanlık alanı konusunda kısa yardımcı ol. "
                "En fazla 5 kısa cümle yaz. "
                "Semptomlardan çıkarılan uzmanlık ipucunu, açık bir çelişki yoksa esas al."
            )
        response = await self.llm_engine.generate_response(
            system_prompt=system_prompt,
            user_prompt=(
                f"Kullanıcının mevcut sorusu:\n{query.text}\n\n"
                f"Yakın konuşma bağlamı:\n{recent_conversation or 'Bağlam yok.'}\n\n"
                f"Semptom temelli klinik ipucu:\n{guidance_prompt}\n\n"
                f"Cevap biçimi:\n{answer_style_prompt}\n\n"
                "Bilgi verirken kesin tanı dili kullanma; ancak olası nedenleri, "
                "kırmızı bayrak belirtileri ve uygun sonraki adımları belirt. "
                "Kullanıcı istemedikçe randevu alma diline geçme. "
                "Cevabı belge listesi gibi değil, hasta dostu kısa açıklama olarak yaz. "
                "En fazla 5 kısa cümlede bitir."
            ),
            context_documents=llm_context_docs,
        )
        response = self._clean_response(response, query_text=query.text)
        if self._needs_retrieval_fallback(
            response=response,
            documents=llm_context_docs,
        ):
            response = self._build_retrieval_fallback(
                query_text=query.text,
                documents=llm_context_docs,
                recommended_specialty=guidance.primary_specialty,
            )
        prefix = self._guidance_prefix(guidance) if asks_for_specialty else ""
        if prefix and prefix.lower() not in response.lower():
            response = f"{prefix}\n\n{response}"
        return {
            "message": response,
            "ui_action": "none",
            "payload": {
                "documents_found": len(source_docs),
                "retrieved_documents_found": len(context_docs),
                "recommended_specialty": self._display_specialty_name(
                    guidance.primary_specialty
                ),
                "alternative_specialties": [
                    self._display_specialty_name(specialty)
                    for specialty in (guidance.alternative_specialties or [])
                ],
                "specialty_rationale": guidance.rationale,
                "red_flags": guidance.red_flags or [],
            },
            "sources": [
                {
                    "title": doc.title,
                    "source": doc.source,
                    "excerpt": doc.excerpt(),
                    "score": round(doc.score, 3),
                    "url": doc.metadata.get("url"),
                }
                for doc in source_docs
            ],
        }

    def _source_display_documents(
        self,
        query_text: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        core_tokens = self._content_tokens(query_text)
        query_tokens = self._expanded_query_tokens(query_text)
        if not query_tokens:
            return documents[:2]
        required_title_hits = 1 if len(core_tokens) <= 1 else 2

        strong: list[RetrievedDocument] = []
        weak: list[RetrievedDocument] = []
        for document in documents:
            title = self._normalize(document.title)
            content = self._normalize(document.content)
            if self._is_blocked_source_title(title=title, query_tokens=query_tokens):
                continue

            title_hits = self._title_hit_count(title=title, core_tokens=core_tokens)
            content_hits = sum(1 for token in query_tokens if token in content)
            if title_hits >= required_title_hits:
                strong.append(document)
            elif content_hits > 0:
                weak.append(document)

        if strong:
            return strong[:3]
        return weak[:2]

    def _expanded_query_tokens(self, query_text: str) -> set[str]:
        tokens = self._content_tokens(query_text)
        expanded = set(tokens)
        for token in tokens:
            expanded.update(self._token_variants(token))
        return {token for token in expanded if len(token) >= 3}

    def _title_hit_count(self, *, title: str, core_tokens: set[str]) -> int:
        if not core_tokens:
            return 0
        hits = 0
        for token in core_tokens:
            variants = self._token_variants(token)
            variants.add(token)
            if any(variant in title for variant in variants):
                hits += 1
        return hits

    def _token_variants(self, token: str) -> set[str]:
        variants = {token}
        suffixes = (
            "unun",
            "inin",
            "nın",
            "nin",
            "nun",
            "leri",
            "lari",
            "lar",
            "ler",
            "den",
            "dan",
            "tan",
            "ten",
            "si",
            "su",
            "sü",
        )
        if token.startswith("reflu"):
            variants.update({"reflu", "reflunun"})
        if token.startswith("uykusuz"):
            variants.update({"uykusuzluk", "uykusuz", "uyku"})
        if token.startswith("yanma") or token.startswith("yanmas"):
            variants.update({"yanma", "yanmasi"})
        if token.startswith("agri"):
            variants.update({"agri", "agrisi"})
        if token.startswith("bulanti"):
            variants.update({"bulanti", "bulantisi"})
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                variants.add(token[: -len(suffix)])
        return {variant for variant in variants if len(variant) >= 3}

    def _is_blocked_source_title(
        self,
        *,
        title: str,
        query_tokens: set[str],
    ) -> bool:
        blocked_topics = {
            ("lohusa", "lohusalik", "gebelik", "hamile", "dogum"): {
                "lohusa",
                "lohusalik",
                "gebelik",
                "hamile",
                "dogum",
            },
            ("cocuk", "bebek", "yenidogan"): {"cocuk", "bebek", "yenidogan"},
        }
        for title_terms, allowed_terms in blocked_topics.items():
            if any(term in title for term in title_terms) and not (
                query_tokens & allowed_terms
            ):
                return True
        return False

    def _guidance_prompt(self, guidance) -> str:
        if guidance.primary_specialty is None:
            return "Belirgin bir uzmanlık ipucu çıkmadı."
        alternatives = (
            ", ".join(guidance.alternative_specialties or [])
            if guidance.alternative_specialties
            else "yok"
        )
        red_flags = (
            "; ".join(guidance.red_flags or [])
            if guidance.red_flags
            else "özel bir kırmızı bayrak listesi yok"
        )
        return (
            f"İlk uzmanlık adayı: {guidance.primary_specialty}\n"
            f"Alternatifler: {alternatives}\n"
            f"Gerekçe: {guidance.rationale or 'Yok'}\n"
            f"Kırmızı bayraklar: {red_flags}"
        )

    def _guidance_prefix(self, guidance) -> str:
        if guidance.primary_specialty is None:
            return ""
        if guidance.alternative_specialties:
            alternatives = ", ".join(
                self._display_specialty_name(specialty)
                for specialty in guidance.alternative_specialties
            )
            return (
                f"Belirtilerinize göre ilk değerlendirilebilecek bölüm "
                f"{self._display_specialty_name(guidance.primary_specialty)} gibi görünüyor. Gerekirse {alternatives} da "
                "alternatif olarak düşünülebilir."
            )
        return (
            f"Belirtilerinize göre ilk değerlendirilebilecek bölüm "
            f"{self._display_specialty_name(guidance.primary_specialty)} gibi görünüyor."
        )

    def _answer_style_prompt(
        self,
        *,
        asks_for_cause: bool,
        asks_for_specialty: bool,
    ) -> str:
        if asks_for_cause and not asks_for_specialty:
            return (
                "Kullanıcı neden/nedir bilgisi istiyor. Soru cümlesini tekrar etme; "
                "ilk cümlede doğrudan olası nedeni açıkla. Belirti listesi veya "
                "randevu yönlendirmesiyle başlama. En fazla 3-4 kısa cümle yaz; "
                "uzmanlık bilgisini gerekiyorsa son cümlede kısa not olarak ver."
            )
        if asks_for_specialty:
            return (
                "Kullanıcı uygun bölümü soruyor. Önce bölüm adını söyle, sonra kısa "
                "gerekçe ve acil uyarı varsa onu ekle."
            )
        return (
            "Kullanıcı genel sağlık bilgisi istiyor. Soru cümlesini tekrar etmeden "
            "doğrudan, kısa ve anlaşılır cevap ver."
        )

    def _clean_response(self, response: str, *, query_text: str) -> str:
        cleaned = response.strip()
        query_prefix = re.escape(query_text.strip())
        cleaned = re.sub(
            rf"^\s*{query_prefix}\s*[:?\-.]*\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(
            r"\s*\([^)]*belge\s+\d+[^)]*\)\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(
            r"\bGastroenteroloji uzmanlığı gerekli\.",
            "Şikayetler sık tekrarlıyorsa gastroenteroloji değerlendirmesi uygun olabilir.",
            cleaned,
            flags=re.IGNORECASE,
        )
        return self._remove_incomplete_tail(cleaned)

    def _remove_incomplete_tail(self, text: str) -> str:
        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n")]
        while paragraphs and self._looks_truncated(paragraphs[-1]):
            paragraphs.pop()
        cleaned = "\n\n".join(paragraphs).strip()
        if cleaned:
            return cleaned

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
            "uzmanına",
            "uzmanina",
        }
        last_token = stripped.split()[-1].strip(".,;:!?()[]{}\"'").casefold()
        if last_token in dangling_words:
            return True
        return stripped[-1] not in ".!?:)"

    def _needs_retrieval_fallback(
        self,
        *,
        response: str,
        documents: list[RetrievedDocument],
    ) -> bool:
        return (
            self._looks_truncated(response)
            or self._looks_like_source_heading(response, documents)
            or self._looks_like_prompt_leak(response)
            or self._looks_like_dataset_artifact(response)
        )

    def _looks_like_source_heading(
        self,
        response: str,
        documents: list[RetrievedDocument],
    ) -> bool:
        normalized_response = self._normalize(response)
        if not normalized_response:
            return True
        artifact_markers = (
            "soruyu cevapladi",
            "cevaplandi",
            "cevaplandirildigini",
            "cevap bilgisi",
            "sayfa :",
            "ozet :",
            "makale:",
            "baslik:",
            "kaynak:",
            "icerik:",
        )
        if any(marker in normalized_response for marker in artifact_markers):
            return True
        for document in documents:
            normalized_title = self._normalize(document.title)
            if normalized_title and normalized_response.startswith(normalized_title[:35]):
                return True
            title_parts = [
                part.strip()
                for part in re.split(r"[?.|-]", normalized_title)
                if len(part.strip()) >= 16
            ]
            if any(normalized_response.startswith(part[:35]) for part in title_parts):
                return True
        return False

    def _looks_like_prompt_leak(self, response: str) -> bool:
        normalized_response = self._normalize(response)
        prompt_markers = (
            "cevaplari kisa",
            "cevap bicimi",
            "kullanicinin mevcut sorusu",
            "yakin konusma baglami",
            "semptom temelli klinik ipucu",
            "baglam belgeleri",
            "gorev:",
            "en fazla",
            "kullaniciya bilgi",
            "kendi uzmanlik alanina gore",
            "sadece nihai turkce cevabi ver",
        )
        return any(marker in normalized_response for marker in prompt_markers)

    def _looks_like_dataset_artifact(self, response: str) -> bool:
        normalized_response = self._normalize(response)
        rating_hits = len(re.findall(r"\b\d(?:[.,]\d)?\s*/\s*\d\b", response))
        if rating_hits >= 2 or re.match(r"^\s*\d(?:[.,]\d)?\s*/\s*\d\b", response):
            return True
        if re.search(r"(?im)^\s*#{1,6}\s+", response):
            return True
        if any(
            marker in normalized_response
            for marker in (
                "yapilan calismada",
                "calismanin sonuclari",
                "makale:",
                "puan",
                "rating",
            )
        ):
            return True

        non_empty_lines = [
            line.strip()
            for line in response.splitlines()
            if line.strip()
        ]
        tiny_lines = [
            line
            for line in non_empty_lines
            if len(line.strip(" .,:;!?-")) <= 2
        ]
        if len(tiny_lines) >= 3:
            return True
        single_word_lines = [
            line
            for line in non_empty_lines
            if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", line)) <= 1
        ]
        if (
            len(non_empty_lines) >= 3
            and len(single_word_lines) / len(non_empty_lines) >= 0.75
        ):
            return True
        return False

    def _build_retrieval_fallback(
        self,
        *,
        query_text: str,
        documents: list,
        recommended_specialty: str | None,
    ) -> str:
        if not documents:
            return (
                "Bu konuda genel bilgi verebilirim ancak elimde yeterli kaynak bağlamı "
                "bulunmadı. Şikayetler sıklaşıyor, şiddetleniyor veya günlük yaşamı "
                "etkiliyorsa bir sağlık profesyoneline başvurmanız uygun olur."
            )
        query_tokens = self._expanded_query_tokens(query_text)
        candidate_sentences: list[tuple[int, float, str]] = []
        for document in documents:
            for sentence in self._split_sentences(document.content):
                sentence = self._strip_leading_heading_fragment(sentence)
                if self._looks_like_title_sentence(sentence, document.title):
                    continue
                normalized = self._normalize(sentence)
                if not normalized:
                    continue
                overlap = sum(1 for token in query_tokens if token in normalized)
                if not query_tokens or overlap > 0:
                    candidate_sentences.append((overlap, document.score, sentence))
        candidate_sentences.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected_sentences: list[str] = []
        seen_sentences: set[str] = set()
        for _, _, sentence in candidate_sentences:
            normalized_sentence = self._normalize(sentence)
            if normalized_sentence in seen_sentences:
                continue
            seen_sentences.add(normalized_sentence)
            selected_sentences.append(sentence)
            if len(selected_sentences) >= 2:
                break
        if not selected_sentences:
            selected_sentences = [
                self._split_sentences(documents[0].content)[0]
                if self._split_sentences(documents[0].content)
                else documents[0].excerpt(220)
            ]
        answer = " ".join(selected_sentences[:2]).strip()
        answer = re.sub(
            r"^(dolayısıyla|bu nedenle|bu yüzden)\s+",
            "",
            answer,
            flags=re.IGNORECASE,
        ).strip()
        if answer:
            answer = f"{answer[0].upper()}{answer[1:]}"
        if recommended_specialty:
            answer = (
                f"{answer} Şikayetler sık tekrarlıyorsa {self._display_specialty_name(recommended_specialty)} "
                "değerlendirmesi uygun olabilir."
            )
        return answer

    def _strip_leading_heading_fragment(self, sentence: str) -> str:
        heading_patterns = (
            r"^(?:Sürekli\s+)?Mide Bulantısı(?: ve Baş Ağrısı| ve Nedenleri)?\s+",
            r"^Baş Ağrısı ve Mide Bulantısı\s+",
            r"^Mide Yanması(?: Neden Olur)?\s+",
        )
        cleaned = sentence.strip()
        for pattern in heading_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    def _display_specialty_name(self, specialty: str | None) -> str:
        if not specialty:
            return ""
        display_names = {
            "Noroloji": "Nöroloji",
            "Gogus Hastaliklari": "Göğüs Hastalıkları",
            "Goz Hastaliklari": "Göz Hastalıkları",
            "Kadin Hastaliklari ve Dogum": "Kadın Hastalıkları ve Doğum",
            "Kulak Burun Bogaz": "Kulak Burun Boğaz",
        }
        return display_names.get(specialty, specialty)

    def _looks_like_title_sentence(self, sentence: str, title: str) -> bool:
        if sentence.strip().startswith("-") or sentence.count(" - ") >= 2:
            return True
        normalized_sentence = self._normalize(sentence).strip(" .")
        normalized_title = self._normalize(title).strip(" .")
        if normalized_title and normalized_sentence.startswith(normalized_title[:35]):
            return True
        if (
            normalized_sentence
            and normalized_title.startswith(normalized_sentence[:30])
            and len(normalized_sentence.split()) <= 8
        ):
            return True
        title_markers = ("neden olur", "nasil gecer", "belirtileri", "tedavisi")
        if "?" in sentence and len(normalized_sentence.split()) <= 8:
            return True
        return (
            any(marker in normalized_sentence for marker in title_markers)
            and len(normalized_sentence.split()) <= 8
        )

    def _split_sentences(self, text: str) -> list[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
            if sentence.strip()
        ]

    def _normalize(self, text: str) -> str:
        return text.lower().translate(
            str.maketrans(
                {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
            )
        )

    def _content_tokens(self, text: str) -> set[str]:
        stopwords = {
            "neden",
            "nedir",
            "sebebi",
            "sebep",
            "olur",
            "icin",
            "için",
            "hangi",
            "var",
            "midir",
            "miyim",
        }
        return {
            token
            for token in re.findall(r"[a-zçğıöşü0-9]{3,}", self._normalize(text))
            if token not in stopwords
        }

    async def _recent_conversation_context(
        self,
        query: HealthQuery,
        *,
        ignore_appointment_bias: bool = False,
    ) -> str:
        if query.conversation_id is None:
            return ""
        recent_messages = await self.user_history_repository.list_recent_messages(
            conversation_id=query.conversation_id,
            limit=6,
        )
        if not recent_messages:
            return ""
        if ignore_appointment_bias:
            filtered_messages = [
                message
                for message in recent_messages
                if not self._looks_like_appointment_message(message.content)
            ]
            if filtered_messages:
                recent_messages = filtered_messages
        return "\n".join(
            f"{message.role}: {message.content}"
            for message in recent_messages
        )

    def _asks_for_specialty(self, normalized_text: str) -> bool:
        return any(
            phrase in normalized_text
            for phrase in (
                "hangi bolum",
                "hangi bran",
                "hangi doktora gitmeliyim",
                "hangi bolume gitmeliyim",
                "hangi uzmana gitmeliyim",
            )
        )

    def _asks_for_cause(self, normalized_text: str) -> bool:
        return any(
            phrase in normalized_text
            for phrase in (
                "neden",
                "nedir",
                "sebep",
                "sebebi",
                "neden olur",
                "ne olabilir",
            )
        )

    def _looks_like_appointment_message(self, text: str) -> bool:
        normalized = " ".join(
            text.lower().translate(
                str.maketrans(
                    {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
                )
            ).split()
        )
        appointment_markers = (
            "randevu",
            "slot",
            "rezervasyon",
            "ilkini al",
            "uygun randevu",
            "hangi slotu",
            "rezervasyon icin",
        )
        return any(marker in normalized for marker in appointment_markers)
