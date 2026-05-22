from fastapi import APIRouter

from app.api.v1.endpoints import ping, users

api_router = APIRouter()
api_router.include_router(ping.router)
api_router.include_router(users.router)
