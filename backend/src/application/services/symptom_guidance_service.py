from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SymptomGuidance:
    primary_specialty: str | None = None
    alternative_specialties: list[str] | None = None
    rationale: str | None = None
    confidence: float = 0.0
    red_flags: list[str] | None = None


class SymptomGuidanceService:
    """
    Basit ama klinik olarak makul semptom -> uzmanlik esleme katmani.

    Bu servis LLM'den bagimsizdir ve iki amaca hizmet eder:
    - InformationAgent dogru branşi daha tutarli önersin.
    - AppointmentAgent branş yazilmamissa semptomdan mantikli bir aday çikarsin.
    """

    def analyze(self, text: str) -> SymptomGuidance:
        normalized = self._canonicalize_symptoms(self._normalize(text))
        scores: dict[str, int] = {}
        matches: dict[str, list[str]] = {}

        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Noroloji",
            weighted_terms={
                "bas agrisi": 4,
                "bas agrim": 4,
                "basim agriyor": 4,
                "basim agri": 4,
                "basimda agri": 4,
                "migren": 5,
                "basimin agrisi": 4,
                "tek tarafli bas agrisi": 5,
                "isik hassasiyeti": 4,
                "ses hassasiyeti": 3,
                "aura": 5,
                "uyusma": 4,
                "denge kaybi": 4,
                "goz kararmasi": 3,
                "bas donmesi": 3,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Kulak Burun Bogaz",
            weighted_terms={
                "kulak": 5,
                "burun": 5,
                "bogaz agrisi": 5,
                "bogazda agri": 5,
                "bogaz enfeksiyonu": 5,
                "bogaz sisligi": 4,
                "sinuzit": 5,
                "burun akintisi": 4,
                "geniz akintisi": 4,
                "kulak cinlamasi": 4,
                "bademcik": 4,
                "yutkunma": 3,
                "ses kisikligi": 3,
                "sinus": 4,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Kardiyoloji",
            weighted_terms={
                "gogus agrisi": 6,
                "carpinti": 6,
                "kalp": 5,
                "nefes darligi": 4,
                "eforla agri": 4,
                "tansiyon": 3,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Dermatoloji",
            weighted_terms={
                "kasinti": 5,
                "dokuntu": 5,
                "sivilce": 5,
                "egzama": 5,
                "cilt": 4,
                "ben": 3,
                "sac dokulmesi": 3,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Gastroenteroloji",
            weighted_terms={
                "reflu": 6,
                "mide yanmasi": 6,
                "goguste yanma": 4,
                "agza aci su gelmesi": 6,
                "eksime": 6,
                "hazimsizlik": 4,
                "mide agrisi": 5,
                "mide bulantisi": 3,
                "mide bulantim": 3,
                "siskinlik": 4,
                "yemek borusu": 5,
                "yutakta yanma": 4,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Endokrinoloji",
            weighted_terms={
                "diyabet": 6,
                "seker": 5,
                "insulin": 5,
                "hba1c": 6,
                "aclik sekeri": 5,
                "tokluk sekeri": 5,
                "tiroid": 6,
                "tsh": 5,
                "guatr": 5,
                "hipotiroidi": 6,
                "hipertiroidi": 6,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Dahiliye",
            weighted_terms={
                "mide bulantisi": 4,
                "karin agrisi": 5,
                "ishal": 4,
                "kabizlik": 4,
                "halsizlik": 3,
                "ates": 3,
                "genel halsizlik": 4,
                "kusma": 4,
                "hazimsizlik": 2,
                "mide agrisi": 2,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Gogus Hastaliklari",
            weighted_terms={
                "oksuruk": 5,
                "balgam": 5,
                "hirilti": 5,
                "nefes darligi": 4,
                "akciger": 5,
                "astim": 5,
                "bronit": 4,
                "bronsit": 4,
                "koah": 5,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Goz Hastaliklari",
            weighted_terms={
                "goz": 5,
                "bulanik gorme": 5,
                "gozde agri": 4,
                "goz kizarmasi": 4,
                "capak": 3,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Pediatri",
            weighted_terms={
                "cocuk": 6,
                "bebek": 6,
                "cocugum": 6,
                "bebegim": 6,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Kadin Hastaliklari ve Dogum",
            weighted_terms={
                "adet": 5,
                "regl": 5,
                "hamilelik": 6,
                "gebelik": 6,
                "kadin dogum": 6,
                "vajinal": 4,
                "gebeyim": 6,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Ortopedi",
            weighted_terms={
                "diz agrisi": 5,
                "eklem agrisi": 4,
                "omuz agrisi": 4,
                "bel agrisi": 4,
                "sirt agrisi": 4,
                "ayak bilegi": 4,
                "hareket kisitliligi": 3,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Romatoloji",
            weighted_terms={
                "romatizma": 6,
                "eklem sisligi": 5,
                "sabah tutuklugu": 5,
                "eklemde sislik": 5,
                "yaygin eklem agrisi": 4,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Uroloji",
            weighted_terms={
                "idrar": 5,
                "idrarda yanma": 5,
                "sik idrara cikma": 4,
                "bobrek": 4,
                "mesane": 4,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Nefroloji",
            weighted_terms={
                "kreatinin": 6,
                "protein kacagi": 6,
                "nefroloji": 5,
                "bobrek yetmezligi": 6,
                "odem": 4,
            },
        )

        if "reflu" in normalized and self._contains_any(
            normalized,
            ("bogaz", "ses kisikligi", "yutkunma", "geniz")
        ):
            scores["Gastroenteroloji"] = scores.get("Gastroenteroloji", 0) + 3
            matches.setdefault("Gastroenteroloji", []).append(
                "reflu + bogaz/yutak belirtileri"
            )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Psikiyatri",
            weighted_terms={
                "anksiyete": 5,
                "panik": 5,
                "depres": 5,
                "uykusuzluk": 3,
                "kaygi": 4,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Hematoloji",
            weighted_terms={
                "anemi": 6,
                "kan hastaligi": 6,
                "demir eksikligi": 5,
                "hematoloji": 6,
            },
        )
        self._score(
            normalized,
            scores=scores,
            matches=matches,
            specialty="Onkoloji",
            weighted_terms={
                "kanser": 6,
                "onkoloji": 6,
                "kemoterapi": 5,
                "tumor": 5,
            },
        )

        if self._contains_any(normalized, ("bas agrisi", "bas agrim", "basim")) and self._contains_any(
            normalized,
            (
                "sinuzit",
                "burun tikanikligi",
                "burun akintisi",
                "geniz akintisi",
                "yuz agrisi",
            ),
        ):
            scores["Kulak Burun Bogaz"] = scores.get("Kulak Burun Bogaz", 0) + 4
            matches.setdefault("Kulak Burun Bogaz", []).append(
                "bas agrisi + sinus belirtileri"
            )

        if self._contains_any(normalized, ("bas agrisi", "bas agrim", "basim")) and self._contains_any(
            normalized,
            ("migren", "isik hassasiyeti", "bulanti", "uyusma", "aura"),
        ):
            scores["Noroloji"] = scores.get("Noroloji", 0) + 4
            matches.setdefault("Noroloji", []).append(
                "bas agrisi + norolojik ipuclari"
            )

        if not scores:
            return SymptomGuidance(
                primary_specialty=None,
                alternative_specialties=[],
                rationale=None,
                confidence=0.0,
                red_flags=self._red_flags(normalized),
            )

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        primary_specialty, primary_score = ranked[0]
        alternatives = [
            specialty
            for specialty, score in ranked[1:3]
            if score >= max(primary_score - 2, 3)
        ]
        matched_terms = ", ".join(matches.get(primary_specialty, [])[:3])
        rationale = (
            f"'{matched_terms}' ipuclarina gore ilk uygun uzmanlik alani {primary_specialty}."
            if matched_terms
            else f"Belirtilere gore ilk uygun uzmanlik alani {primary_specialty}."
        )
        confidence = min(primary_score / 10, 0.95)

        return SymptomGuidance(
            primary_specialty=primary_specialty,
            alternative_specialties=alternatives,
            rationale=rationale,
            confidence=confidence,
            red_flags=self._red_flags(normalized),
        )

    def _score(
        self,
        normalized: str,
        *,
        scores: dict[str, int],
        matches: dict[str, list[str]],
        specialty: str,
        weighted_terms: dict[str, int],
    ) -> None:
        for term, weight in weighted_terms.items():
            if term in normalized:
                scores[specialty] = scores.get(specialty, 0) + weight
                matches.setdefault(specialty, []).append(term)

    def _red_flags(self, normalized: str) -> list[str]:
        red_flags: list[str] = []
        if self._contains_any(normalized, ("bas agrisi", "bas agrim", "basim")):
            red_flags.extend(
                [
                    "ani ve hayatinizdaki en siddetli bas agrisi",
                    "bas agrisina konusma bozuklugu, kol-bacakta uyusma veya kuvvetsizlik eslik etmesi",
                    "ates veya ense sertligi ile birlikte bas agrisi",
                ]
            )
        if self._contains_any(normalized, ("gogus agrisi", "carpinti", "nefes darligi")):
            red_flags.extend(
                [
                    "gogus agrisinin nefes darligi, bayilma veya soguk terleme ile olmasi",
                ]
            )
        return red_flags

    def _normalize(self, text: str) -> str:
        return " ".join(
            text.lower()
            .translate(
                str.maketrans(
                    {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
                )
            )
            .split()
        )

    def _canonicalize_symptoms(self, normalized: str) -> str:
        replacements = {
            "bas agrim": "bas agrisi",
            "basim agriyor": "bas agrisi",
            "basim agri": "bas agrisi",
            "basimda agri": "bas agrisi",
            "basimin agrisi": "bas agrisi",
            "mide bulantim": "mide bulantisi",
            "bulantim": "bulanti",
        }
        canonical = normalized
        for source, target in replacements.items():
            canonical = canonical.replace(source, target)
        return canonical

    def _contains_any(self, text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)
