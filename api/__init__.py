"""
FastAPI REST API Package for SIH26166.
"""
from api.routes import router
from api.server import app

__all__ = ["router", "app"]
