import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .metrics import register_inventory_collector
from .routers import inventory, products
from .schemas import AppInfo

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("stockpilot")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Schema is owned by Alembic (run in app/prestart.py before Uvicorn starts),
    # so the API never calls create_all() against a real database.
    log.info(
        "%s %s (%s) starting, environment=%s",
        settings.app_name,
        settings.app_version,
        settings.git_sha,
        settings.environment,
    )
    yield
    log.info("%s shutting down", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Inventory management API: products, stock movements and warehouse KPIs.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
register_inventory_collector()

app.include_router(products.router)
app.include_router(inventory.router)


@app.get("/", tags=["system"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    """Cheap check that the process is up. Deliberately does not touch the database,
    so a database outage does not make Kubernetes restart healthy API pods."""
    return {"status": "UP"}


@app.get("/ready", tags=["system"], summary="Readiness probe")
def ready(db: Session = Depends(get_db)):
    """Only report READY when the database answers, so traffic is routed to this pod
    only when it can actually serve requests."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.warning("readiness check failed: database unreachable")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from None
    return {"status": "READY"}


@app.get("/api/info", response_model=AppInfo, tags=["system"], summary="Build information for the running API")
def info():
    return AppInfo(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        git_sha=settings.git_sha,
    )
