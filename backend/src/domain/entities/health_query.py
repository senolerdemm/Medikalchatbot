from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


TRANSLATION_TABLE = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


class QueryIntent(str, Enum):
    INFORMATION = "information"
    APPOINTMENT = "appointment"
    PERSONAL_HISTORY = "personal_history"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(slots=True)
class RetrievedDocument:
    document_id: str
    title: str
    content: str
    source: str
    score: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)

    def excerpt(self, max_length: int = 180) -> str:
        clean = " ".join(self.content.split())
        if len(clean) <= max_length:
            return clean
        return clean[: max_length - 3].rstrip() + "..."


@dataclass(slots=True)
class HealthQuery:
    patient_id: str
    text: str
    conversation_id: str | None = None
    query_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    intent: QueryIntent | None = None

    def normalized_text(self) -> str:
        return " ".join(self.text.lower().translate(TRANSLATION_TABLE).split())

    def assess_risk(self) -> RiskLevel:
        text = self.normalized_text()
        high_risk_terms = (
            "nefes alamiyorum",
            "gogus agrisi",
            "bayildim",
            "felc",
            "intihar",
            "kanama",
        )
        moderate_terms = (
            "ates",
            "siddetli agri",
            "kusma",
            "carpinti",
            "bas donmesi",
        )
        if any(term in text for term in high_risk_terms):
            return RiskLevel.HIGH
        if any(term in text for term in moderate_terms):
            return RiskLevel.MODERATE
        return RiskLevel.LOW
