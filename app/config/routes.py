"""Main Routes"""

from fastapi import APIRouter

from app.accounts import routes as accounts_routes
from app.base import routes as base_routes
from app.messages import routes as messages_routes


api_router = APIRouter()

api_router.include_router(accounts_routes.router)
api_router.include_router(base_routes.router)
api_router.include_router(messages_routes.router)


@api_router.get("/health")
def health():
    """Health check endpoint"""
    return {"message": "Healthy"}
