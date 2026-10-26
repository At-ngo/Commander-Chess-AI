"""
Commander Chess AI — Services Package
"""

from .engine_adapter import BaseEngineAdapter, MockEngineAdapter
from .game_session_store import GameSessionStore, session_store

# Default active engine adapter instance
default_engine_adapter: BaseEngineAdapter = MockEngineAdapter()

__all__ = [
    "BaseEngineAdapter",
    "MockEngineAdapter",
    "default_engine_adapter",
    "GameSessionStore",
    "session_store",
]
