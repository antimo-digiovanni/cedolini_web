from fastapi import APIRouter

from app.api.routes.auctions import router as auctions_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.domain import router as domain_router
from app.api.routes.health import router as health_router
from app.api.routes.loads import router as loads_router

api_router = APIRouter()
api_router.include_router(auctions_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(health_router)
api_router.include_router(loads_router)
api_router.include_router(domain_router)
