# packages/agents/base.py
"""Giao thức và lớp cơ sở (Base Agent) cho các tác tử Cờ Tư Lệnh.

Tuân thủ đặc tả tại agent_protocol.md và README.md:
- Không sửa đổi GameState.
- Không trả về nước đi ngoài danh sách legal_actions.
- Hỗ trợ đo lường thời gian quyết định (decision_time_ms).
- Hỗ trợ RNG với seed tái lập.
- Ghi nhận metadata phục vụ nghiên cứu và đánh giá thực nghiệm.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import random
import time
from typing import Any

from commander_game_engine.actions import AtomicAction
from commander_game_engine.game_state import GameState


class AgentError(Exception):
    """Ngoại lệ cơ sở cho các lỗi liên quan đến Agent."""


class NoLegalActionsError(AgentError):
    """Ngoại lệ khi danh sách legal_actions bị rỗng hoặc ván đã kết thúc."""


class InvalidActionReturnedError(AgentError):
    """Ngoại lệ khi agent trả về action không nằm trong legal_actions."""


@dataclass(frozen=True)
class AgentDecision:
    """Kết quả quyết định nước đi của một tác tử."""

    action: AtomicAction
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Lớp cơ sở cho toàn bộ các tác tử AI trong Cờ Tư Lệnh."""

    def __init__(
        self,
        name: str = "BaseAgent",
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.seed = seed
        self.config = config or {}
        self.rng = random.Random(seed)

    @property
    @abstractmethod
    def algorithm(self) -> str:
        """Tên thuật toán (ví dụ: 'random', 'heuristic', 'minimax', 'mcts')."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Phiên bản thuật toán."""

    def select_action(
        self,
        state: GameState,
        legal_actions: list[AtomicAction],
        **kwargs: Any,
    ) -> AgentDecision:
        """Phương thức chuẩn để chọn một nước đi.

        Thực hiện:
        1. Kiểm tra legal_actions rỗng.
        2. Đo thời gian suy nghĩ.
        3. Ủy quyền cho _choose_action().
        4. Kiểm tra action trả về có thuộc legal_actions không.
        5. Đóng gói AgentDecision kèm metadata chuẩn.
        """
        if not legal_actions:
            raise NoLegalActionsError(
                f"Agent '{self.name}' không thể chọn nước đi vì legal_actions rỗng."
            )

        start_time = time.perf_counter()
        action, custom_meta = self._choose_action(state, legal_actions, **kwargs)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if action not in legal_actions:
            raise InvalidActionReturnedError(
                f"Agent '{self.name}' trả về hành động không hợp lệ: {action}."
            )

        meta: dict[str, Any] = {
            "agent_name": self.name,
            "algorithm": self.algorithm,
            "version": self.version,
            "seed": self.seed,
            "decision_time_ms": elapsed_ms,
            "candidates_count": len(legal_actions),
        }
        if custom_meta:
            meta.update(custom_meta)

        return AgentDecision(action=action, metadata=meta)

    @abstractmethod
    def _choose_action(
        self,
        state: GameState,
        legal_actions: list[AtomicAction],
        **kwargs: Any,
    ) -> tuple[AtomicAction, dict[str, Any]]:
        """Thuật toán chọn nước đi cụ thể của từng lớp con.

        Trả về:
            tuple gồm (nước đi được chọn, dict metadata bổ sung).
        """

