from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.modules.accounts import router as accounts_router
from app.modules.ai import router as ai_router
from app.modules.bots import router as bots_router
from app.modules.channels import router as channels_router
from app.modules.dialogs import router as dialogs_router
from app.modules.stats import router as stats_router


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router.router)
app.include_router(bots_router.router)
app.include_router(channels_router.router)
app.include_router(dialogs_router.router)
app.include_router(ai_router.router)
app.include_router(stats_router.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
