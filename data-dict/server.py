from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from api.domain_metadata_api import router as DomainMetadataRouter
from api.tenant_metadata_api import router as TenantMetadataRouter
from api.table_metadata_api import router as TableMetadataRouter
from api.attribute_metadata_api import router as AttributeMetadataRouter
from api.health_api import router as HealthRouter
from api.data_tool_api import router as DataToolRouter
from api.common_api import router as CommonRouter
from api.glossary_api import router as GlossaryRouter
from api.submit_api import router as SubmitRouter
from db.session import db
import uvicorn
from core.config import get_logger, settings
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from api.strawberry_api import schema
from db.bootstrap import acquire_advisory_lock, run_bootstrap, release_advisory_lock


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    logger.info("Connecting DB...")
    await db.connect(settings.connect_type)
    logger.info("DB connected")

    # Initialize database schema if needed
    if settings.run_bootstrap_on_startup:
        logger.info("Bootstrap-on-startup enabled, trying to acquire advisory lock...")
        async with db.pool.acquire() as conn:
            locked = await acquire_advisory_lock(conn, timeout_seconds=120)
            if locked:
                logger.info("Advisory lock acquired, running bootstrap DDL...")
                try:
                    await run_bootstrap(conn, sql_dir="db/sql")
                    logger.info("Bootstrap DDL executed successfully.")
                except Exception as e:
                    logger.error(f"Bootstrap DDL failed: {e}", exc_info=True)
                    raise
                finally:
                    await release_advisory_lock(conn)
                    logger.info("Advisory lock released.")
            else:
                logger.warning("Could not acquire advisory lock within timeout, skipping bootstrap.")

    try:
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown event
        logger.info("Disconnecting DB...")
        await db.disconnect()
        logger.info("DB disconnected.")


graphql_app = GraphQLRouter(schema)


app = FastAPI(
    lifespan=lifespan,
    title="Data Dictionary API",
    version="1.0",
    swagger_ui_parameters={
        "url": "./openapi.json"
    }
)


routers = [
    (DomainMetadataRouter, "/api/v1"),
    (TenantMetadataRouter, "/api/v1"),
    (TableMetadataRouter, "/api/v1"),
    (AttributeMetadataRouter, "/api/v1"),
    (HealthRouter, "/api/v1"),
    (DataToolRouter, "/api/v1"),
    (CommonRouter, "/api/v1"),
    (SubmitRouter, "/api/v1"),
    (graphql_app, "/graphql"),
    (GlossaryRouter, "/api/v1")
]


for routers, prefix in routers:
    app.include_router(routers, prefix=prefix)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
