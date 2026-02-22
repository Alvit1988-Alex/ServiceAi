import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine

from app.config import settings
from app.modules.accounts import router as accounts_router
from app.modules.auth import router as auth_router
from app.modules.ai import router as ai_router
from app.modules.bots import router as bots_router
from app.modules.channels import router as channels_router
from app.modules.dialogs import router as dialogs_router
from app.modules.stats import router as stats_router
from app.modules.diagnostics import router as diagnostics_router
from app.modules.webchat.router import router as webchat_router
from app.modules.integrations.bitrix24.router import router as bitrix_integrations_router


app = FastAPI(
    title=settings.app_name,
    debug=settings.runtime_debug,
)

def configure_cors() -> None:
    debug = settings.runtime_debug

    allow_origins = settings.cors_allow_origins
    allow_credentials = settings.cors_allow_credentials

    if allow_origins is None or (debug and not allow_origins):
        allow_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    if not debug:
        if allow_credentials and (not allow_origins or allow_origins == ["*"]):
            raise ValueError("CORS allow_origins must be explicitly set when allow_credentials=true in production")
    else:
        if allow_origins == ["*"] and allow_credentials:
            raise ValueError("In debug, use allow_credentials=false when allow_origins='*'")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


configure_cors()

app.include_router(accounts_router.router)
app.include_router(auth_router.router)
app.include_router(bots_router.router)
app.include_router(channels_router.router)
app.include_router(channels_router.webhooks_router)
app.include_router(dialogs_router.router)
app.include_router(ai_router.router)
app.include_router(stats_router.router)
app.include_router(diagnostics_router.router)
app.include_router(webchat_router)
app.include_router(bitrix_integrations_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def verify_database_connection() -> None:
    """Fail fast with a clear message if the database is unreachable."""

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - defensive logging
        logging.exception(
            "Database connection failed. Check DATABASE_URL (port, host, credentials) and ensure the DB is running."
        )
        raise
