from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "backend/src")

from domain.entities.health_query import HealthQuery
from presentation.dependencies import (  # noqa: E402
    get_agent_orchestrator,
    get_intent_classifier,
)


async def main() -> None:
    classifier = get_intent_classifier()
    cases = [
        "bas agrisi neden olur",
        "hangi doktora gitmeliyim kalp carpintim var",
        "gecmis kayitlarima gore beni ozetle",
        "yarin saat 10 gibi kbb randevusu ara",
    ]
    for text in cases:
        query = HealthQuery(patient_id="user_001", text=text)
        print(f"{text} -> {(await classifier.classify(query)).value}")

    orchestrator = get_agent_orchestrator()
    info_result = await orchestrator.process_query(
        HealthQuery(patient_id="user_001", text="bas agrisi neden olur")
    )
    print("info_handled_by=", info_result["handled_by"])
    print("info_message=", str(info_result["message"])[:260])

    history_result = await orchestrator.process_query(
        HealthQuery(patient_id="user_001", text="gecmis kayitlarima gore beni ozetle")
    )
    print("history_handled_by=", history_result["handled_by"])
    print("history_message=", str(history_result["message"])[:260])


if __name__ == "__main__":
    asyncio.run(main())
