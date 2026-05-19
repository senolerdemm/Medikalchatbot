import asyncio
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.postgres.base import Base, engine
from infrastructure.database.postgres.demo_seed import ensure_demo_data
from presentation.api.controllers.appointment_controller import router as appointment_router
from presentation.api.controllers.auth_controller import router as auth_router
from presentation.api.controllers.chat_controller import router as chat_router
from presentation.dependencies import get_llm_engine


logger = logging.getLogger(__name__)


def initialize_database(*, retries: int = 1, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            ensure_demo_data()
            return
        except SQLAlchemyError as error:
            last_error = error
            if attempt == retries:
                break
            logger.warning(
                "PostgreSQL bağlantısı hazır değil, tekrar deneniyor (%s/%s).",
                attempt,
                retries,
            )
            time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error


def create_app() -> FastAPI:
    app = FastAPI(
        title="Turkish Language Based Smart Medical Assistant API",
        description=(
            "Türkçe Dil Tabanlı Akıllı Tıbbi Asistan projesi için "
            "çok ajanlı backend servisi"
        ),
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat_router)
    app.include_router(auth_router)
    app.include_router(appointment_router)

    async def _warm_up_llm() -> None:
        await get_llm_engine().warm_up()
        logger.info("LLM warm-up tamamlandı.")

    @app.on_event("startup")
    async def _ensure_database() -> None:
        await asyncio.to_thread(
            initialize_database,
            retries=10,
            delay_seconds=2.0,
        )
        asyncio.create_task(_warm_up_llm())

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
