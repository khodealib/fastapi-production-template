"""Root API router: mounts all module routers."""

from __future__ import annotations

from fastapi import APIRouter

from .modules.users.routes import auth_router, users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
