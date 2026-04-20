from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from presentation.api.controllers.chat_controller import router as chat_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Turkish Medical AI Assistant API",
        description=(
            "Agent tabanli, DDD ve Clean Architecture prensipleriyle "
            "kurgulanmis tibbi asistan backend'i"
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
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
