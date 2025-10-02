import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.logs import router as logs_router
from api.projects import router as projects_router

try:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
    SENTRY_AVAILABLE = True
except Exception:
    SENTRY_AVAILABLE = False

def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.5-dev")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.SENTRY_DSN and SENTRY_AVAILABLE:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.2)
        app.add_middleware(SentryAsgiMiddleware)

    app.include_router(logs_router)
    app.include_router(projects_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.ENV}

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=False)
