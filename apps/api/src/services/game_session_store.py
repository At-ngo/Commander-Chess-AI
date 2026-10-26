"""
Commander Chess AI — In-Memory Game Session Store
"""

from typing import Dict, Optional, List
from ..models.game import GameState


class GameSessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, GameState] = {}

    def get(self, game_id: str) -> Optional[GameState]:
        return self._sessions.get(game_id)

    def save(self, game_state: GameState) -> None:
        self._sessions[game_state.game_id] = game_state

    def delete(self, game_id: str) -> bool:
        if game_id in self._sessions:
            del self._sessions[game_id]
            return True
        return False

    def list(self) -> List[GameState]:
        return list(self._sessions.values())


# Global singleton instance for the API process
session_store = GameSessionStore()
