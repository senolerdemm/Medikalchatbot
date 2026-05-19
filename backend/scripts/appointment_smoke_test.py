from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "backend/src")

from domain.entities.health_query import HealthQuery
from presentation.dependencies import get_appointment_agent


async def main() -> None:
    query = HealthQuery(
        patient_id="user_003",
        text="Ankara'da uygun kalpcileri gormek istiyorum",
    )
    result = await get_appointment_agent().handle_appointment_request(query)
    print(result["message"])
    slot_options = result["payload"].get("slot_options", [])
    print(f"slot_count={len(slot_options)}")
    for slot in slot_options[:5]:
        print(slot["display_text"])


if __name__ == "__main__":
    asyncio.run(main())
