from fastapi import FastAPI

from app.config import settings
from app.modules.ai import router as ai_router
from app.modules.bots import router as bots_router
from app.modules.channels import router as channels_router
from app.modules.dialogs import router as dialogs_router


app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(bots_router.router)
app.include_router(channels_router.router)
app.include_router(dialogs_router.router)
app.include_router(ai_router.router)


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
