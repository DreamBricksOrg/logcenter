import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.agent import sdk_log
from api.logs import router as logs_router
from api.projects import router as projects_router
from api.users import router as users_router
from api.stream import router as stream_router
from api.auth import router as auth_router
from api.dash import router as dash_router
from api.pages import router as pages_router
from middleware.sdk_audit import SdkAuditMiddleware

try:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
    SENTRY_AVAILABLE = True
except Exception:
    SENTRY_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    async def _delayed_startup_log():
        await asyncio.sleep(0.3)
        await sdk_log(
            "INFO",
            "LogCenter startup",
            data={"env": settings.ENV, "version": "0.1.6-dev"},
            status="OK",
        )

    asyncio.create_task(_delayed_startup_log())
    yield
    # === SHUTDOWN ===
    await sdk_log(
        "INFO",
        "LogCenter shutdown",
        data={"env": settings.ENV, "version": "0.1.6-dev"},
        status="INFO",
    )

def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.6-dev", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SdkAuditMiddleware)

    if settings.SENTRY_DSN and SENTRY_AVAILABLE:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.2)
        app.add_middleware(SentryAsgiMiddleware)

    app.mount("/src/static", StaticFiles(directory="src/static"), name="src-static")

    app.include_router(auth_router)
    app.include_router(logs_router)
    app.include_router(projects_router)
    app.include_router(users_router)
    app.include_router(stream_router)
    app.include_router(dash_router)
    app.include_router(pages_router)

    @app.get("/alive")
    async def alive():
        return {"status": "ok", "env": settings.ENV}

    return app

app = create_app()
