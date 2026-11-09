# tests/test_agents.py
"""Bộ kiểm thử đơn vị cho AI Agents (BaseAgent, RandomAgent)."""

from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "packages") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "packages"))

from commander_game_engine.initial_setup import create_initial_state
from commander_game_engine.move_generator import generate_legal_actions
from agents import (
    AgentDecision,
    NoLegalActionsError,
    RandomAgent,
)


class TestRandomAgent(unittest.TestCase):
    """Kiểm thử tác tử RandomAgent."""

    def setUp(self) -> None:
        self.state = create_initial_state()
        self.legal_actions = generate_legal_actions(self.state)

    def test_random_agent_selects_legal_action(self) -> None:
        """Đảm bảo nước đi được chọn luôn nằm trong danh sách nước hợp lệ."""
        agent = RandomAgent(name="TestRandom", seed=42)
        decision = agent.select_action(self.state, self.legal_actions)

        self.assertIsInstance(decision, AgentDecision)
        self.assertIn(decision.action, self.legal_actions)

    def test_reproducibility_with_seed(self) -> None:
        """Đảm bảo hai agent cùng seed sinh chuỗi nước đi hoàn toàn giống nhau."""
        agent1 = RandomAgent(name="Agent1", seed=999)
        agent2 = RandomAgent(name="Agent2", seed=999)

        moves1 = [agent1.select_action(self.state, self.legal_actions).action for _ in range(10)]
        moves2 = [agent2.select_action(self.state, self.legal_actions).action for _ in range(10)]

        self.assertEqual(moves1, moves2)

    def test_empty_legal_actions_raises_error(self) -> None:
        """Đảm bảo báo lỗi NoLegalActionsError khi danh sách nước đi rỗng."""
        agent = RandomAgent(name="TestEmpty")
        with self.assertRaises(NoLegalActionsError):
            agent.select_action(self.state, [])

    def test_metadata_structure(self) -> None:
        """Đảm bảo trả về đầy đủ metadata phục vụ nghiên cứu."""
        agent = RandomAgent(name="TestMeta", seed=100)
        decision = agent.select_action(self.state, self.legal_actions)

        meta = decision.metadata
        self.assertEqual(meta["agent_name"], "TestMeta")
        self.assertEqual(meta["algorithm"], "random")
        self.assertEqual(meta["version"], "1.0.0")
        self.assertEqual(meta["seed"], 100)
        self.assertEqual(meta["candidates_count"], len(self.legal_actions))
        self.assertIn("decision_time_ms", meta)
        self.assertGreaterEqual(meta["decision_time_ms"], 0.0)

    def test_agent_does_not_mutate_state(self) -> None:
        """Đảm bảo agent không làm thay đổi trạng thái GameState được truyền vào."""
        agent = RandomAgent(name="TestImmutability", seed=77)
        state_before = deepcopy(self.state)

        _ = agent.select_action(self.state, self.legal_actions)

        self.assertEqual(self.state.current_player, state_before.current_player)
        self.assertEqual(self.state.turn_number, state_before.turn_number)
        self.assertEqual(len(self.state.pieces), len(state_before.pieces))
        for pid, piece in state_before.pieces.items():
            current_piece = self.state.pieces[pid]
            self.assertEqual(piece.position, current_piece.position)
            self.assertEqual(piece.owner, current_piece.owner)


if __name__ == "__main__":
    unittest.main()

