"""
Commander Chess AI — Routers Package
"""

from .health import router as health_router
from .agents import router as agents_router
from .games import router as games_router
from .replays import router as replays_router

__all__ = [
    "health_router",
    "agents_router",
    "games_router",
    "replays_router",
]
