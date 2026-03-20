from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.db.session import initialize_database

app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup() -> None:
    if settings.auto_create_tables:
        initialize_database()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
    }
