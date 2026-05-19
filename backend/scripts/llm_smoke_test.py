from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "backend/src")

from domain.entities.health_query import HealthQuery
from presentation.dependencies import (  # noqa: E402
    get_appointment_agent,
    get_intent_classifier,
    get_personal_agent,
)


async def main() -> None:
    classifier = get_intent_classifier()
    appointment_query = HealthQuery(
        patient_id="user_001",
        text="yarin saat 10 gibi kbb randevusu ara",
    )
    print("intent=", (await classifier.classify(appointment_query)).value)

    try:
        personal_agent = get_personal_agent()
        personal_query = HealthQuery(
            patient_id="user_001",
            text="gecmis kayitlarima gore beni ozetle",
        )
        personal_result = await personal_agent.handle_history_query(personal_query)
        print("personal=", str(personal_result["message"])[:240])
    except Exception as error:  # noqa: BLE001
        print("personal_error=", error)

    try:
        appointment_agent = get_appointment_agent()
        appointment_result = await appointment_agent.handle_appointment_request(
            appointment_query
        )
        print("appointment=", appointment_result["message"])
        print("appointment_action=", appointment_result["payload"].get("action"))
    except Exception as error:  # noqa: BLE001
        print("appointment_error=", error)


if __name__ == "__main__":
    asyncio.run(main())
