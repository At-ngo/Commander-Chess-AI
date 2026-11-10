# tests/test_rule_scenarios.py
"""Kiểm thử các thế cờ cô lập (Scenario / Tactical Unit Testing).

Bộ kiểm thử này cô lập từng điều luật trọng yếu của Cờ Tư Lệnh trên các
thế cờ thu nhỏ (1-4 quân) để đảm bảo:
1. Move Generator không sinh thừa nước bất hợp lệ.
2. Move Generator không bỏ sót nước hợp lệ.
3. Transition Engine thực thi đúng các ngoại lệ và luật đặc biệt.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "packages") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "packages"))

from commander_game_engine.board import Board, EdgeType, Position, Terrain
from commander_game_engine.game_state import GameState, GameStatus, Piece, PieceType, Player
from commander_game_engine.actions import ActionType, AtomicAction, TurnCommand, TurnCommandType
from commander_game_engine.move_generator import generate_legal_actions, generate_piece_actions
from commander_game_engine.engine import apply_action
from commander_game_engine import rules
from agents.random_agent import RandomAgent


class TestMovementAndObstacles(unittest.TestCase):
    """1. Quy tắc hình học di chuyển và vật cản (Movement & Obstacles)."""

    def setUp(self) -> None:
        self.board = Board()

    def test_tank_moves_and_blocking(self) -> None:
        """Xe tăng đi 4 hướng tối đa 2 đoạn; bị cản nếu đoạn 1 có quân."""
        # Thế cờ 1: Xe tăng đứng giữa đất trống (3, 5)
        state = GameState(board=self.board, current_player=Player.RED)
        tank = Piece(id="red_tank", piece_type=PieceType.TANK, owner=Player.RED, position=(3, 5))
        state.add_piece(tank)

        actions = generate_piece_actions(state, "red_tank")
        destinations = {a.end for a in actions}

        # Kỳ vọng: 4 hướng thẳng x 2 đoạn = 8 nước đi
        expected = {(1, 5), (2, 5), (4, 5), (5, 5), (3, 3), (3, 4), (3, 6), (3, 7)}
        self.assertEqual(destinations, expected)

        # Thế cờ 2: Đặt 1 quân đồng minh cản ở (3, 6)
        friendly_inf = Piece(id="red_inf", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(3, 6))
        state.add_piece(friendly_inf)

        actions_blocked = generate_piece_actions(state, "red_tank")
        move_destinations_blocked = {a.end for a in actions_blocked if a.action_type == ActionType.MOVE}
        pickup_destinations = {a.end for a in actions_blocked if a.action_type == ActionType.PICKUP}
        all_destinations = {a.end for a in actions_blocked}

        # Kỳ vọng: Xe tăng KHÔNG được MOVE đè lên (3, 6) hay nhảy qua đầu tới (3, 7); chỉ có PICKUP lên xe tại (3, 6)
        self.assertNotIn((3, 6), move_destinations_blocked)
        self.assertIn((3, 6), pickup_destinations)
        self.assertNotIn((3, 7), all_destinations)
        # Các hướng khác vẫn đi bình thường
        self.assertIn((3, 4), move_destinations_blocked)
        self.assertIn((3, 3), move_destinations_blocked)

    def test_commander_movement_and_capture_range(self) -> None:
        """Tư lệnh di chuyển thẳng không giới hạn, nhưng chỉ ăn quân trong tầm 1 đoạn."""
        state = GameState(board=self.board, current_player=Player.RED)
        cmd = Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6))
        state.add_piece(cmd)

        # Đặt quân địch ở khoảng cách 1 đoạn (1, 6) và 2 đoạn (0, 8)
        enemy_near = Piece(id="blue_near", piece_type=PieceType.INFANTRY, owner=Player.BLUE, position=(1, 6))
        enemy_far = Piece(id="blue_far", piece_type=PieceType.INFANTRY, owner=Player.BLUE, position=(0, 8))
        state.add_piece(enemy_near)
        state.add_piece(enemy_far)

        actions = generate_piece_actions(state, "red_cmd")
        captures = {a.end for a in actions if a.action_type == ActionType.CAPTURE}

        # Kỳ vọng: Chỉ được ăn quân ở khoảng cách 1 (1, 6), KHÔNG được ăn ở khoảng cách 2 (0, 8)
        self.assertIn((1, 6), captures)
        self.assertNotIn((0, 8), captures)


class TestArtilleryLineOfSight(unittest.TestCase):
    """2. Quy tắc Pháo binh: Bắn xuyên quân khi ăn nhưng bị cản khi di chuyển."""

    def setUp(self) -> None:
        self.board = Board()

    def test_artillery_blocked_on_move(self) -> None:
        """Pháo binh di chuyển vào ô trống bị cản bởi quân đứng giữa."""
        state = GameState(board=self.board, current_player=Player.RED)
        art = Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(2, 5))
        obstacle = Piece(id="obs", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(2, 6))
        state.add_piece(art)
        state.add_piece(obstacle)

        actions = generate_piece_actions(state, "red_art")
        moves = {a.end for a in actions if a.action_type == ActionType.MOVE}

        # Pháo không được đi xuyên quân qua ô trống (2, 7) hoặc (2, 8)
        self.assertNotIn((2, 7), moves)
        self.assertNotIn((2, 8), moves)

    def test_artillery_captures_through_multiple_obstacles(self) -> None:
        """Pháo binh bắn xuyên bất kỳ số lượng quân cản nào để tiêu diệt mục tiêu."""
        state = GameState(board=self.board, current_player=Player.RED)
        art = Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(2, 5))
        obs1 = Piece(id="obs1", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(2, 6))
        obs2 = Piece(id="obs2", piece_type=PieceType.TANK, owner=Player.BLUE, position=(2, 7))
        target = Piece(id="target", piece_type=PieceType.INFANTRY, owner=Player.BLUE, position=(2, 8))

        state.add_piece(art)
        state.add_piece(obs1)
        state.add_piece(obs2)
        state.add_piece(target)

        actions = generate_piece_actions(state, "red_art")
        attack_ends = {a.end for a in actions if a.action_type in (ActionType.CAPTURE, ActionType.BOMBARD)}

        # Pháo bắt buộc phải bắn xuyên được cả 2 vật cản để tấn công (2, 8)
        self.assertIn((2, 8), attack_ends)


class TestCommanderExposureAndPinning(unittest.TestCase):
    """3. Quy tắc cấm Tư lệnh đối mặt trực tiếp và cơ chế ghim quân (Pinning)."""

    def setUp(self) -> None:
        self.board = Board()

    def test_commander_cannot_move_into_direct_facing(self) -> None:
        """Tư lệnh không được tự di chuyển vào thế đối mặt trực tiếp với Tư lệnh địch."""
        state = GameState(board=self.board, current_player=Player.RED)
        red_cmd = Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 5))
        blue_cmd = Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 6))
        state.add_piece(red_cmd)
        state.add_piece(blue_cmd)

        # Cột 6 hoàn toàn trống. Red Commander bước từ (0, 5) sang (0, 6) sẽ lộ mặt Tướng với Blue (11, 6)
        actions = generate_piece_actions(state, "red_cmd")
        destinations = {a.end for a in actions}

        self.assertNotIn((0, 6), destinations)

        # Kiểm tra thử bằng engine validator
        illegal_action = AtomicAction(action_type=ActionType.MOVE, piece_id="red_cmd", start=(0, 5), end=(0, 6))
        verdict = rules.validate_action(state, illegal_action)
        self.assertFalse(verdict.valid)
        self.assertEqual(verdict.code, rules.RuleCode.COMMANDERS_FACING)

    def test_pinned_piece_cannot_leave_line_of_sight(self) -> None:
        """Quân cản duy nhất giữa 2 Tư lệnh không được di chuyển rời khỏi đường thẳng che chắn."""
        state = GameState(board=self.board, current_player=Player.RED)
        red_cmd = Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6))
        blue_cmd = Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 6))
        # Bộ binh Đỏ ở (4, 6) là quân cản DUY NHẤT trên cột 6
        pinned_inf = Piece(id="red_inf", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(4, 6))

        state.add_piece(red_cmd)
        state.add_piece(blue_cmd)
        state.add_piece(pinned_inf)

        actions = generate_piece_actions(state, "red_inf")
        destinations = {a.end for a in actions}

        # CẤM rời cột 6: không được sang ngang (4, 5) hoặc (4, 7)
        self.assertNotIn((4, 5), destinations)
        self.assertNotIn((4, 7), destinations)

        # ĐƯỢC PHÉP di chuyển dọc trên cột 6 (vẫn duy trì vật che chắn)
        self.assertIn((3, 6), destinations)
        self.assertIn((5, 6), destinations)


class TestRiverAndFordCrossing(unittest.TestCase):
    """4. Quy tắc vượt sông sâu và đoạn ngầm (River & Ford Crossing)."""

    def setUp(self) -> None:
        self.board = Board()

    def test_heavy_weapons_cannot_move_across_deep_river(self) -> None:
        """Pháo binh / Tên lửa / Cao xạ không được tự di chuyển ô trống qua sông sâu."""
        state = GameState(board=self.board, current_player=Player.RED)
        art = Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(5, 3))
        state.add_piece(art)

        # Đoạn (5, 3) -> (6, 3) là sông sâu (Deep River)
        self.assertEqual(self.board.get_edge_type((5, 3), (6, 3)), EdgeType.DEEP_RIVER)

        actions = generate_piece_actions(state, "red_art")
        destinations = {a.end for a in actions}

        self.assertNotIn((6, 3), destinations)

    def test_heavy_weapons_can_capture_across_deep_river(self) -> None:
        """Ngoại lệ Q02: Quân nặng được phép vượt sông sâu khi ăn quân địch ở bờ đối diện."""
        state = GameState(board=self.board, current_player=Player.RED)
        art = Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(5, 3))
        enemy = Piece(id="blue_inf", piece_type=PieceType.INFANTRY, owner=Player.BLUE, position=(6, 3))
        state.add_piece(art)
        state.add_piece(enemy)

        actions = generate_piece_actions(state, "red_art")
        captures = {a.end for a in actions if a.action_type == ActionType.CAPTURE}

        self.assertIn((6, 3), captures)

    def test_all_units_can_cross_ford(self) -> None:
        """Mọi đơn vị mặt đất đều được tự do qua đoạn ngầm (x=5 hoặc x=7)."""
        state = GameState(board=self.board, current_player=Player.RED)
        art = Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(5, 5))
        state.add_piece(art)

        # Đoạn (5, 5) -> (6, 5) là ngầm đá (Ford)
        self.assertEqual(self.board.get_edge_type((5, 5), (6, 5)), EdgeType.FORD)

        actions = generate_piece_actions(state, "red_art")
        destinations = {a.end for a in actions}

        self.assertIn((6, 5), destinations)

    def test_navy_cannot_cross_ford(self) -> None:
        """Hải quân (Tàu chiến) không được đi qua đoạn ngầm."""
        state = GameState(board=self.board, current_player=Player.BLUE)
        navy = Piece(id="blue_navy", piece_type=PieceType.NAVY, owner=Player.BLUE, position=(6, 5))
        state.add_piece(navy)

        actions = generate_piece_actions(state, "blue_navy")
        destinations = {a.end for a in actions}

        self.assertNotIn((5, 5), destinations)


class TestCoastAndNavyCombat(unittest.TestCase):
    """5. Tương tác Bờ biển và Hải quân (Coast & Navy Combat)."""

    def setUp(self) -> None:
        self.board = Board()

    def test_ground_unit_bombards_navy_at_sea_without_entering_sea(self) -> None:
        """Quân bộ tấn công Tàu ngoài biển sâu bắt buộc dùng BOMBARD (bắn tại chỗ), không được nhảy xuống biển."""
        state = GameState(board=self.board, current_player=Player.RED)
        art = Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(3, 3))
        navy = Piece(id="blue_navy", piece_type=PieceType.NAVY, owner=Player.BLUE, position=(3, 1))
        state.add_piece(art)
        state.add_piece(navy)

        # Vị trí (3, 1) thuộc biển sâu (SEA: x < 2), (3, 3) thuộc đất liền (LAND)
        self.assertEqual(self.board.get_region(3, 1), Terrain.SEA)
        self.assertEqual(self.board.get_region(3, 3), Terrain.LAND)

        actions = generate_piece_actions(state, "red_art")
        navy_attacks = [a for a in actions if a.end == (3, 1)]

        # Chỉ có 1 hình thức tấn công duy nhất là BOMBARD
        self.assertEqual(len(navy_attacks), 1)
        self.assertEqual(navy_attacks[0].action_type, ActionType.BOMBARD)

        # Thực thi hành động qua engine
        res = apply_action(state, navy_attacks[0])
        self.assertTrue(res.accepted)
        # Pháo vẫn giữ nguyên tọa độ đất liền (3, 3)
        self.assertEqual(res.state.pieces["red_art"].position, (3, 3))
        # Tàu chiến xanh bị tiêu diệt
        self.assertNotIn("blue_navy", res.state.pieces)

    def test_navy_cannot_enter_land(self) -> None:
        """Hải quân không được di chuyển vào đất liền."""
        state = GameState(board=self.board, current_player=Player.BLUE)
        navy = Piece(id="blue_navy", piece_type=PieceType.NAVY, owner=Player.BLUE, position=(4, 2))
        state.add_piece(navy)

        actions = generate_piece_actions(state, "blue_navy")
        destinations = {a.end for a in actions}

        # (4, 3) là đất liền (LAND: x > 2, y != 5, 6)
        self.assertEqual(self.board.get_region(4, 3), Terrain.LAND)
        self.assertNotIn((4, 3), destinations)

    def test_navy_cannot_pass_through_another_navy(self) -> None:
        """Hải quân không được đi xuyên qua tàu chiến khác."""
        state = GameState(board=self.board, current_player=Player.RED)
        navy1 = Piece(id="red_navy_1", piece_type=PieceType.NAVY, owner=Player.RED, position=(0, 0))
        navy2 = Piece(id="red_navy_2", piece_type=PieceType.NAVY, owner=Player.RED, position=(2, 0))
        state.add_piece(navy1)
        state.add_piece(navy2)

        actions = generate_piece_actions(state, "red_navy_1")
        destinations = {a.end for a in actions}

        # Không được nhảy qua navy2 để đến (3, 0)
        self.assertNotIn((3, 0), destinations)


class TestHeroPromotion(unittest.TestCase):
    """6. Quy tắc phong Anh hùng (Hero Promotion)."""

    def setUp(self) -> None:
        self.board = Board()

    def test_auto_promotion_when_only_one_other_piece_survives(self) -> None:
        """Tự động phong Anh hùng khi một phe chỉ còn đúng 1 quân khác Tư lệnh."""
        state = GameState(board=self.board, current_player=Player.RED)
        # Phe Đỏ chỉ còn Tư lệnh và 1 Xe tăng
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
        state.add_piece(Piece(id="red_tank", piece_type=PieceType.TANK, owner=Player.RED, position=(3, 5)))

        # Phe Xanh còn đủ
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 6)))
        state.add_piece(Piece(id="blue_inf1", piece_type=PieceType.INFANTRY, owner=Player.BLUE, position=(10, 2)))
        state.add_piece(Piece(id="blue_inf2", piece_type=PieceType.INFANTRY, owner=Player.BLUE, position=(10, 4)))

        # Xe tăng Đỏ di chuyển
        action = AtomicAction(action_type=ActionType.MOVE, piece_id="red_tank", start=(3, 5), end=(3, 6))
        result = apply_action(state, action)

        self.assertTrue(result.accepted)
        promoted_tank = result.state.pieces["red_tank"]
        self.assertTrue(promoted_tank.is_heroic, "Xe tăng phải được tự phong Anh hùng!")

    def test_heroic_piece_increased_range_and_diagonal(self) -> None:
        """Xe tăng Anh hùng được bổ sung 4 hướng chéo và tăng tầm lên 3 đoạn."""
        state = GameState(board=self.board, current_player=Player.RED)
        hero_tank = Piece(id="red_tank", piece_type=PieceType.TANK, owner=Player.RED, position=(5, 5), is_heroic=True)
        state.add_piece(hero_tank)

        actions = generate_piece_actions(state, "red_tank")
        destinations = {a.end for a in actions}

        # Xe tăng thường chỉ đi 4 hướng thẳng tầm 2
        # Xe tăng Anh hùng có 8 hướng tầm 3: (5+3, 5+3) = (8, 8)
        self.assertIn((8, 8), destinations)
        self.assertIn((2, 2), destinations)
        # Tổng cộng 8 hướng x 3 đoạn = 24 nước đi
        self.assertEqual(len(destinations), 24)

    def test_two_hqs_and_commander_neither_promoted(self) -> None:
        """DEC-015: Khi còn 2 Sở chỉ huy và Tư lệnh thì Sở chỉ huy KHÔNG được phong Anh hùng."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
        state.add_piece(Piece(id="red_hq1", piece_type=PieceType.HEADQUARTERS, owner=Player.RED, position=(1, 5)))
        state.add_piece(Piece(id="red_hq2", piece_type=PieceType.HEADQUARTERS, owner=Player.RED, position=(1, 7)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 4)))

        # Tư lệnh Đỏ di chuyển sang (0, 5)
        action = AtomicAction(action_type=ActionType.MOVE, piece_id="red_cmd", start=(0, 6), end=(0, 5))
        result = apply_action(state, action)
        self.assertTrue(result.accepted)
        self.assertFalse(result.state.pieces["red_hq1"].is_heroic, "HQ1 không được phong Anh hùng khi còn 2 HQ")
        self.assertFalse(result.state.pieces["red_hq2"].is_heroic, "HQ2 không được phong Anh hùng khi còn 2 HQ")

    def test_one_hq_and_commander_promoted(self) -> None:
        """DEC-015: Khi chỉ còn DUY NHẤT 1 Sở chỉ huy và Tư lệnh thì Sở chỉ huy được phong Bộ binh Anh hùng."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
        state.add_piece(Piece(id="red_hq1", piece_type=PieceType.HEADQUARTERS, owner=Player.RED, position=(1, 5)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 4)))

        # Tư lệnh Đỏ di chuyển sang (0, 5)
        action = AtomicAction(action_type=ActionType.MOVE, piece_id="red_cmd", start=(0, 6), end=(0, 5))
        result = apply_action(state, action)
        self.assertTrue(result.accepted)
        promoted_hq = result.state.pieces["red_hq1"]
        self.assertTrue(promoted_hq.is_heroic, "Sở chỉ huy duy nhất phải được phong Anh hùng")

        # Khi đến lượt phe Đỏ, Sở chỉ huy Anh hùng có tầm đi 8 hướng, 2 đoạn như Bộ binh Anh hùng
        result.state.current_player = Player.RED
        actions = generate_piece_actions(result.state, "red_hq1")
        self.assertTrue(len(actions) > 0, "Sở chỉ huy Anh hùng phải có nước đi")


class TestConfirmedRulesDec020(unittest.TestCase):
    """7. Kiểm thử bộ quy tắc DEC-020 đã được Project Owner xác nhận."""

    def setUp(self) -> None:
        self.board = Board()

    def test_carried_enemy_deploy_threat_blocks_commander_step(self) -> None:
        """Tư lệnh bị cấm đi vào ô mà quân đang ngồi trên phương tiện địch có thể triển khai ăn ngay."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(2, 3)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 8)))
        state.add_piece(Piece(id="blue_tank", piece_type=PieceType.TANK, owner=Player.BLUE, position=(3, 4)))
        state.pieces["blue_tank"].cargo = ["blue_inf"]
        state.pieces["blue_inf"] = Piece(
            id="blue_inf",
            piece_type=PieceType.INFANTRY,
            owner=Player.BLUE,
            position=None,
            carried_by="blue_tank",
        )

        legal_ends = {a.end for a in generate_piece_actions(state, "red_cmd")}
        # Từ blue_tank tại (3,4), Bộ binh Xanh trên xe có thể triển khai ăn thẳng 1 bước tới (2,4) và (3,3)
        self.assertNotIn((2, 4), legal_ends)
        self.assertNotIn((3, 3), legal_ends)
        self.assertIn((2, 2), legal_ends)

    def test_aa_suicide_with_carried_commander_is_illegal(self) -> None:
        """Máy bay thường chở Tư lệnh không được bay qua hoặc đáp vào vùng phòng không khiến Tư lệnh chết theo."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_air", piece_type=PieceType.AIRCRAFT, owner=Player.RED, position=(2, 4)))
        state.pieces["red_air"].cargo = ["red_cmd"]
        state.pieces["red_cmd"] = Piece(
            id="red_cmd",
            piece_type=PieceType.COMMANDER,
            owner=Player.RED,
            position=None,
            carried_by="red_air",
        )
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 8)))
        state.add_piece(Piece(id="blue_aa", piece_type=PieceType.ANTI_AIRCRAFT, owner=Player.BLUE, position=(4, 4)))

        air_actions = generate_piece_actions(state, "red_air")
        # Bất kỳ hành động nào còn chở Tư lệnh (carry_cargo=True hoặc BOMB) đi vào/qua vùng PK đều BỊ CẤM
        air_ends_carrying_cmd = {
            a.end for a in air_actions if a.carry_cargo or a.action_type == ActionType.BOMB
        }
        self.assertNotIn((3, 4), air_ends_carrying_cmd)
        self.assertNotIn((4, 4), air_ends_carrying_cmd)
        self.assertNotIn((5, 4), air_ends_carrying_cmd)

        # Riêng đòn rời bỏ cargo (carry_cargo=False) để lại red_cmd an toàn tại (2, 4) vẫn bảo toàn được Tư lệnh
        for a in air_actions:
            if a.end == (4, 4):
                self.assertFalse(a.carry_cargo)
                self.assertEqual(a.action_type, ActionType.CAPTURE)

    def test_checkmate_wins_with_50_bonus_and_stalemate_draws_with_zero_bonus(self) -> None:
        """Chiếu hết thắng (+50đ); hết nước đi hợp lệ nhưng không bị chiếu xử HÒA (STALEMATE, +0đ)."""
        # 1) Stalemate: Đỏ đi red_inf_a (9,9) -> (10,9), khóa hết đường thoát của blue_cmd ở (11,10) mà không chiếu
        stale_state = GameState(board=self.board, current_player=Player.RED)
        stale_state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 5)))
        stale_state.add_piece(Piece(id="red_inf_a", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(9, 9)))
        stale_state.add_piece(Piece(id="red_aa1", piece_type=PieceType.ANTI_AIRCRAFT, owner=Player.RED, position=(11, 8)))
        stale_state.add_piece(Piece(id="red_aa2", piece_type=PieceType.ANTI_AIRCRAFT, owner=Player.RED, position=(9, 10)))
        stale_state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 10)))

        res_stale = apply_action(
            stale_state,
            AtomicAction(action_type=ActionType.MOVE, piece_id="red_inf_a", start=(9, 9), end=(10, 9)),
        )
        self.assertTrue(res_stale.accepted)
        self.assertTrue(res_stale.terminal)
        self.assertIsNone(res_stale.winner)
        self.assertEqual(res_stale.terminal_reason, "STALEMATE")
        self.assertEqual(res_stale.state.game_status, GameStatus.DRAW)
        self.assertEqual(res_stale.state.scores[Player.RED], 0)

        # 2) Checkmate: cùng thế khóa trên nhưng thêm Pháo Đỏ tại (9,8) chiếu xuyên (10,9) vào (11,10)
        mate_state = stale_state.copy()
        mate_state.pieces["red_inf_a"].position = (10, 9)
        mate_state.add_piece(Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(8, 8)))
        res_mate = apply_action(
            mate_state,
            AtomicAction(action_type=ActionType.MOVE, piece_id="red_art", start=(8, 8), end=(9, 8)),
        )
        self.assertTrue(res_mate.accepted)
        self.assertTrue(res_mate.terminal)
        self.assertEqual(res_mate.winner, Player.RED)
        self.assertEqual(res_mate.terminal_reason, "CHECKMATE")
        self.assertEqual(res_mate.state.game_status, GameStatus.RED_WIN)
        self.assertEqual(res_mate.state.scores[Player.RED], 50)

    def test_missile_pierce_capture_only_not_move(self) -> None:
        """Tên lửa được ăn xuyên vật cản nhưng không được di chuyển xuyên vật cản."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 8)))
        state.add_piece(Piece(id="red_msl", piece_type=PieceType.MISSILE, owner=Player.RED, position=(2, 4)))
        state.add_piece(Piece(id="red_obs", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(3, 4)))
        state.add_piece(Piece(id="blue_tank", piece_type=PieceType.TANK, owner=Player.BLUE, position=(4, 4)))

        actions = generate_piece_actions(state, "red_msl")
        captures = {a.end for a in actions if a.action_type in (ActionType.CAPTURE, ActionType.BOMBARD)}
        self.assertIn((4, 4), captures)

        # Nếu ô (4,4) trống -> vẫn bị red_obs ở (3,4) cản nên KHÔNG MOVE được tới (4,4)
        del state.pieces["blue_tank"]
        moves = {a.end for a in generate_piece_actions(state, "red_msl") if a.action_type == ActionType.MOVE}
        self.assertNotIn((4, 4), moves)

    def test_navy_passes_friendly_shore_piece_and_bombards_inland_over_obstacle(self) -> None:
        """Hải quân vượt qua quân ta không phải Hải quân trên bờ biển/sông và bắn Pháo hạm vào đất liền qua vật cản."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 8)))
        state.add_piece(Piece(id="red_navy", piece_type=PieceType.NAVY, owner=Player.RED, position=(1, 2)))
        state.add_piece(Piece(id="red_inf", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(2, 2)))
        state.add_piece(Piece(id="red_art", piece_type=PieceType.ARTILLERY, owner=Player.RED, position=(1, 3)))
        state.add_piece(Piece(id="blue_tank", piece_type=PieceType.TANK, owner=Player.BLUE, position=(1, 4)))

        navy_actions = generate_piece_actions(state, "red_navy")
        move_ends = {a.end for a in navy_actions if a.action_type == ActionType.MOVE}
        bombard_ends = {a.end for a in navy_actions if a.action_type == ActionType.BOMBARD}

        # Vượt qua Bộ binh Đỏ trên bờ (2,2) tới (3,2)
        self.assertIn((3, 2), move_ends)
        # Bắn Pháo hạm qua vật cản (1,3) vào Xe tăng Xanh trên đất liền (1,4)
        self.assertIn((1, 4), bombard_ends)

    def test_all_combat_pieces_can_attack_aircraft(self) -> None:
        """Mọi loại quân chiến đấu đều có thể tấn công/ăn Máy bay trong tầm hợp lệ."""
        for ptype in (
            PieceType.COMMANDER,
            PieceType.INFANTRY,
            PieceType.MILITIA,
            PieceType.TANK,
            PieceType.ENGINEER,
            PieceType.ARTILLERY,
            PieceType.ANTI_AIRCRAFT,
            PieceType.MISSILE,
        ):
            state = GameState(board=self.board, current_player=Player.RED)
            if ptype != PieceType.COMMANDER:
                state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
            state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 9)))
            attacker_id = "red_cmd" if ptype == PieceType.COMMANDER else "red_att"
            state.add_piece(Piece(id=attacker_id, piece_type=ptype, owner=Player.RED, position=(3, 4)))
            state.add_piece(Piece(id="blue_air", piece_type=PieceType.AIRCRAFT, owner=Player.BLUE, position=(4, 4)))

            actions = generate_piece_actions(state, attacker_id)
            self.assertTrue(
                any(a.end == (4, 4) and a.target_piece_id == "blue_air" for a in actions),
                f"{ptype.value} phải có khả năng tấn công Máy bay",
            )

    def test_carried_commander_inside_tank_aircraft_navy_shields_facing(self) -> None:
        """Tư lệnh ngồi trên Xe tăng, Máy bay, Tàu chiến đều chắn đối mặt với Tư lệnh đối phương."""
        for carrier_type, cpos in (
            (PieceType.TANK, (2, 6)),
            (PieceType.AIRCRAFT, (2, 6)),
            (PieceType.NAVY, (2, 2)),
        ):
            state = GameState(board=self.board, current_player=Player.RED)
            blue_col = cpos[1]
            state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, blue_col)))
            state.add_piece(Piece(id="red_carrier", piece_type=carrier_type, owner=Player.RED, position=(cpos[0], blue_col)))
            state.pieces["red_carrier"].cargo = ["red_cmd"]
            state.pieces["red_cmd"] = Piece(
                id="red_cmd",
                piece_type=PieceType.COMMANDER,
                owner=Player.RED,
                position=None,
                carried_by="red_carrier",
            )
            self.assertTrue(
                rules.validate_commander_exposure(state).valid,
                f"Tư lệnh trên {carrier_type.value} phải được che chắn khỏi đối mặt trực tiếp",
            )

    def test_delayed_solitary_hq_promotion(self) -> None:
        """Tư lệnh núp trong SCH duy nhất khi quân khác bị ăn -> SCH chưa phong; bước ra thì phong ngay lập tức."""
        state = GameState(board=self.board, current_player=Player.BLUE)
        state.add_piece(Piece(id="red_hq", piece_type=PieceType.HEADQUARTERS, owner=Player.RED, position=(1, 5)))
        state.pieces["red_hq"].cargo = ["red_cmd"]
        state.pieces["red_cmd"] = Piece(
            id="red_cmd",
            piece_type=PieceType.COMMANDER,
            owner=Player.RED,
            position=None,
            carried_by="red_hq",
        )
        state.add_piece(Piece(id="red_inf", piece_type=PieceType.INFANTRY, owner=Player.RED, position=(3, 4)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 8)))
        state.add_piece(Piece(id="blue_tank", piece_type=PieceType.TANK, owner=Player.BLUE, position=(3, 6)))

        # Xanh ăn red_inf -> Đỏ chỉ còn red_hq (chứa red_cmd) + red_cmd
        res1 = apply_action(
            state,
            AtomicAction(
                action_type=ActionType.CAPTURE,
                piece_id="blue_tank",
                start=(3, 6),
                end=(3, 4),
                target_piece_id="red_inf",
            ),
        )
        self.assertTrue(res1.accepted)
        s2 = res1.state
        self.assertFalse(s2.pieces["red_hq"].is_heroic, "SCH chưa được phong Anh hùng khi Tư lệnh còn đang núp bên trong")

        red_legal = generate_legal_actions(s2)
        self.assertTrue(len(red_legal) > 0)
        self.assertTrue(all(getattr(a, "piece_id", None) == "red_cmd" for a in red_legal))
        self.assertFalse(any(getattr(a, "action_type", None) == ActionType.BOARD for a in red_legal))

        # (1, 4) và (1, 6) bị blue_tank Anh hùng tại (3, 4) kiểm soát; bước ra ô an toàn (0, 5) -> red_hq phong Anh hùng ngay
        red_ends = {getattr(a, "end", None) for a in red_legal}
        self.assertNotIn((1, 4), red_ends, "Tư lệnh không được bước ra (1, 4) vì bị xe tăng Xanh uy hiếp")
        exit_move = next(a for a in red_legal if getattr(a, "end", None) == (0, 5))
        res2 = apply_action(s2, exit_move)
        self.assertTrue(res2.accepted)
        self.assertTrue(res2.state.pieces["red_hq"].is_heroic, "SCH duy nhất phải được phong Anh hùng ngay khi Tư lệnh bước ra")

    def test_random_agent_chooses_compound_and_split_moves(self) -> None:
        """RandomAgent cập nhật nước đi động gồm nước triển khai từ tổ hợp, carry_cargo=False và END_TURN."""
        state = GameState(board=self.board, current_player=Player.RED)
        state.add_piece(Piece(id="red_cmd", piece_type=PieceType.COMMANDER, owner=Player.RED, position=(0, 6)))
        state.add_piece(Piece(id="blue_cmd", piece_type=PieceType.COMMANDER, owner=Player.BLUE, position=(11, 8)))
        state.add_piece(Piece(id="red_tank", piece_type=PieceType.TANK, owner=Player.RED, position=(4, 4)))
        state.pieces["red_tank"].cargo = ["red_inf"]
        state.pieces["red_inf"] = Piece(
            id="red_inf",
            piece_type=PieceType.INFANTRY,
            owner=Player.RED,
            position=None,
            carried_by="red_tank",
        )

        legal = generate_legal_actions(state)
        self.assertTrue(any(isinstance(a, AtomicAction) and a.piece_id == "red_inf" for a in legal))
        self.assertTrue(any(isinstance(a, AtomicAction) and a.piece_id == "red_tank" and not a.carry_cargo for a in legal))
        self.assertTrue(any(isinstance(a, AtomicAction) and a.piece_id == "red_tank" and a.carry_cargo for a in legal))

        # Thực thi 1 nước triển khai red_inf -> vào compound_turn, RandomAgent có thể chọn hành động kế tiếp hoặc END_TURN
        inf_deploy = next(a for a in legal if isinstance(a, AtomicAction) and a.piece_id == "red_inf" and a.end == (4, 5))
        res_step1 = apply_action(state, inf_deploy)
        self.assertIsNotNone(res_step1.state.compound_turn)

        stack_legal = generate_legal_actions(res_step1.state)
        self.assertTrue(any(isinstance(a, TurnCommand) and a.command_type == TurnCommandType.END_TURN for a in stack_legal))
        agent = RandomAgent(seed=7)
        decision = agent.select_action(res_step1.state, stack_legal)
        self.assertIn(decision.action, stack_legal)
        res_step2 = apply_action(res_step1.state, decision.action)
        self.assertTrue(res_step2.accepted)


if __name__ == "__main__":
    unittest.main()
