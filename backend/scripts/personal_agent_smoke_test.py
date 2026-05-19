from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "backend/src")

from domain.entities.health_query import HealthQuery  # noqa: E402
from presentation.dependencies import get_agent_orchestrator  # noqa: E402


async def main() -> None:
    orchestrator = get_agent_orchestrator()
    cases = [
        "gecmis kayitlarima gore beni ozetle",
        "ilaclarim neler",
        "son tahlillerimi ozetle",
        "son randevularimi soyle",
    ]

    for text in cases:
        result = await orchestrator.process_query(
            HealthQuery(patient_id="user_001", text=text)
        )
        print(f"CASE: {text}")
        print(f"HANDLED_BY: {result['handled_by']}")
        print(f"MESSAGE: {str(result['message'])[:420]}")
        print("---")


if __name__ == "__main__":
    asyncio.run(main())
