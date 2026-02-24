from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, plans, settings
# from routers import gamification, shop

app = FastAPI(
    title="Life Timer API",
    version="0.1.0",
    description="Backend для синхронизации Life Timer между устройствами",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # в проде заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
# app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
# app.include_router(gamification.router, prefix="/gamification", tags=["gamification"])
# app.include_router(shop.router, prefix="/shop", tags=["shop"])


@app.get("/health")
async def health():
    return {"status": "ok"}