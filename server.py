from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

from apis.coordinator_api import router as coordinator_router
from apis.health_api import router as health_router
from apis.auth_api import router as auth_router
from config import settings
from provider.secret_manager_provider import SecretProvider
from services.auth_service import set_jwt_secret_key
from db.db import init_engine, close_engine, run_ddl


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_engine()
    await run_ddl()

    app.state.secret_provider = SecretProvider(ttl_seconds=600)

    try:
        with open(settings.JWT_SECRET_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            set_jwt_secret_key(key)
    except Exception as e:
        raise RuntimeError(f"Failed to load JWT secret from file: {settings.JWT_SECRET_FILE}") from e

    yield

    await close_engine()


bearer_schema = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Coordinator Service",
    lifespan=lifespan,
    version="1.0",
    swagger_ui_parameters={
        "url": "./openapi.json",
        "defaultModelsExpandDepth": -1,
    },
)

routers = [
    (coordinator_router, "/api/v1"),
    (auth_router, "/api/v1"),
    (health_router, "/api/v1"),
]

for r, prefix in routers:
    app.include_router(r, prefix=prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title="Coordinator Service",
        version="1.0",
        description="API documentation for the Coordinator Service",
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
