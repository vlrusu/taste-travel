from fastapi import APIRouter

from app.api.v1.endpoints import health, me, recommendations


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(me.router, tags=["me"])
api_router.include_router(recommendations.router, tags=["recommendations"])
