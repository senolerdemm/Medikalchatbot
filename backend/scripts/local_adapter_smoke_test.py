from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "backend/src")

from presentation.dependencies import get_llm_engine


async def main() -> None:
    engine = get_llm_engine()
    text = await engine.generate_response(
        system_prompt="Sen Türkçe ve kısa cevap veren tıbbi yardımcı bir modelsin.",
        user_prompt="Sadece 'tamam' yaz.",
    )
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
