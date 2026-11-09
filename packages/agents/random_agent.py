# packages/agents/random_agent.py
"""Level 1 Agent — Random Agent cho Cờ Tư Lệnh.

Chọn ngẫu nhiên một nước đi từ danh sách hợp lệ do Game Engine cung cấp.
Hỗ trợ seed để tái lập kết quả thực nghiệm nghiên cứu.
"""

from __future__ import annotations

from typing import Any

from commander_game_engine.actions import AtomicAction
from commander_game_engine.game_state import GameState

from .base import BaseAgent


class RandomAgent(BaseAgent):
    """Tác tử Level 1: Lựa chọn nước đi ngẫu nhiên đồng đều (Uniform Random)."""

    def __init__(
        self,
        name: str = "RandomAgent",
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, seed=seed, config=config)

    @property
    def algorithm(self) -> str:
        return "random"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _choose_action(
        self,
        state: GameState,
        legal_actions: list[AtomicAction],
        **kwargs: Any,
    ) -> tuple[AtomicAction, dict[str, Any]]:
        """Chọn ngẫu nhiên đồng đều một nước đi từ legal_actions."""
        chosen_action = self.rng.choice(legal_actions)
        return chosen_action, {}

