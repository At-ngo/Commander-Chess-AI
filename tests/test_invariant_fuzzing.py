# tests/test_invariant_fuzzing.py
"""Kiểm thử Bất biến ngẫu nhiên (Invariant Fuzzing).

Mô phỏng hàng loạt ván đấu giữa các tác tử ngẫu nhiên (Random vs Random)
và kiểm tra các bất biến trạng thái (Invariants) sau MỖI nước đi:
1. Không có 2 quân đứng trùng tọa độ.
2. Hai Tư lệnh không bao giờ lộ mặt trực tiếp (Commanders facing).
3. Quân bộ không bao giờ rớt xuống biển sâu (Terrain.SEA).
4. Tàu chiến không bao giờ đi vào đất liền (Terrain.LAND).
5. Tính nhất quán 2 chiều: Mọi nước do move_generator sinh ra đều được
   transition engine chấp nhận (accepted == True).
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "packages") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "packages"))

from commander_game_engine.board import Terrain
from commander_game_engine.game_state import GameState, PieceType, Player
from commander_game_engine.initial_setup import create_initial_state
from commander_game_engine.move_generator import generate_legal_actions
from commander_game_engine.engine import apply_action
from commander_game_engine import rules
from agents import RandomAgent


class TestInvariantFuzzing(unittest.TestCase):
    """Fuzzing kiểm tra bất biến toàn ván đấu."""

    def assert_game_invariants(self, state: GameState, last_action, turn_number: int) -> None:
        """Kiểm tra toàn bộ bất biến vật lý và luật chơi tại một thời điểm."""
        # 1. Bất biến trùng tọa độ
        occupied: dict[tuple[int, int], str] = {}
        for pid, piece in state.pieces.items():
            if piece.carried_by is None:
                self.assertIsNotNone(piece.position, f"Quân {pid} không có tọa độ ở lượt {turn_number}")
                self.assertNotIn(
                    piece.position,
                    occupied,
                    f"Trùng ô tại {piece.position} giữa {occupied.get(piece.position)} và {pid} ở lượt {turn_number}",
                )
                occupied[piece.position] = pid

        # 2. Bất biến cấm Tư lệnh đối mặt (kể cả khi ngồi trên phương tiện cơ động)
        vis_occ = rules._visible_occupancy(state)
        self.assertFalse(
            rules.commanders_face(vis_occ) or rules.state_commanders_face(state),
            f"Hai Tư lệnh bị lộ mặt trực tiếp ở lượt {turn_number} sau hành động {last_action}",
        )

        # 3. Bất biến địa hình (Quân bộ vs Biển sâu, Hải quân vs Đất liền)
        for pid, piece in state.pieces.items():
            if piece.carried_by is None and piece.position is not None:
                region = state.board.get_region(*piece.position)
                if piece.piece_type == PieceType.NAVY:
                    self.assertIn(
                        region,
                        (Terrain.SEA, Terrain.COAST, Terrain.RIVER_BANK),
                        f"Hải quân {pid} đứng ở đất liền tại {piece.position} ({region})",
                    )
                else:
                    self.assertNotEqual(
                        region,
                        Terrain.SEA,
                        f"Quân bộ {pid} ({piece.piece_type.value}) đứng ở biển sâu tại {piece.position}",
                    )

    def test_random_game_invariants_batch(self) -> None:
        """Chạy 5 ván cờ ngẫu nhiên (tối đa 100 lượt/ván), kiểm tra bất biến sau mỗi nước đi."""
        total_actions_verified = 0

        for game_idx in range(1, 6):
            state = create_initial_state()
            bot_red = RandomAgent(name=f"Red_{game_idx}", seed=100 + game_idx)
            bot_blue = RandomAgent(name=f"Blue_{game_idx}", seed=200 + game_idx)
            agents = {Player.RED: bot_red, Player.BLUE: bot_blue}

            for turn in range(1, 101):
                player = state.current_player
                legal_actions = generate_legal_actions(state)
                if not legal_actions:
                    break

                decision = agents[player].select_action(state, legal_actions)

                # Kiểm tra tính hợp lệ 2 chiều: Engine PHẢI duyệt nước đi do generator sinh ra
                result = apply_action(state, decision.action)
                self.assertTrue(
                    result.accepted,
                    f"Engine từ chối nước đi hợp lệ ở ván {game_idx}, lượt {turn}: {result.verdict.reason}",
                )

                # Kiểm tra các bất biến trên trạng thái mới
                self.assert_game_invariants(result.state, decision.action, turn)

                total_actions_verified += 1
                state = result.state
                if result.terminal:
                    break

        self.assertGreater(total_actions_verified, 50, "Cần kiểm tra ít nhất 50 nước đi.")


if __name__ == "__main__":
    unittest.main()

