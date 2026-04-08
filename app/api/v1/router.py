from fastapi import APIRouter
from app.api.v1.endpoints import media

api_router = APIRouter()

# Include các endpoint của v1
api_router.include_router(media.router, prefix="/media", tags=["Media"])




