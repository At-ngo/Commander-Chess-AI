"""
Integration unit tests for game rules and bug fixes
"""
import unittest
from apps.api.src.models.enums import Side, PieceType, ActionType, EventType, GameMode, TurnPhase, GameStatus, TerminationReason
from apps.api.src.models.common import Position
from apps.api.src.models.game import PieceState, LegalAction, ActionRequest, GameState
from apps.api.src.services.engine_adapter import (
    default_engine_adapter,
    is_commanders_facing,
    is_hq_facing_enemy_commander,
    can_navy_occupy_square,
    is_ford_square,
    is_shore_square,
    is_sea_square,
    can_piece_cross_river_to_empty,
    get_air_defense_zones,
    is_square_attacked_by_enemy,
    is_commander_in_check,
    select_smart_ai_action,
)


class TestRulesIntegration(unittest.TestCase):
    def test_terrain_and_ford_checks(self):
        # Sông ngầm (BUG-NAVY-001)
        self.assertTrue(is_ford_square(5, 5))
        self.assertTrue(is_ford_square(5, 6))
        self.assertTrue(is_ford_square(7, 5))
        self.assertTrue(is_ford_square(7, 6))
        self.assertFalse(is_ford_square(6, 5))

        # Tàu chiến cấm vào sông ngầm
        self.assertFalse(can_navy_occupy_square(5, 5))
        self.assertTrue(can_navy_occupy_square(6, 5))
        self.assertTrue(can_navy_occupy_square(1, 5))
        self.assertFalse(can_navy_occupy_square(3, 3))  # Đất liền sâu

        # Ô bờ (Q8 & RULE-SHORE-001)
        self.assertTrue(is_shore_square(2, 4))  # Bờ biển
        self.assertTrue(is_shore_square(3, 5))  # Bờ sông
        self.assertFalse(is_shore_square(5, 5))  # Sông ngầm không tính là bờ thông thường
        self.assertFalse(is_shore_square(3, 3))  # Đất liền sâu

    def test_heroic_missile_air_defense_q6(self):
        # Test Tên lửa Anh hùng tại (y=4, x=6) theo đúng ví dụ của Project Owner
        missile = PieceState(
            piece_id="test_missile",
            side=Side.RED,
            type=PieceType.MISSILE,
            position=Position(x=6, y=4),
            is_hero=True,
        )
        zones = get_air_defense_zones(Side.RED, [missile])
        self.assertEqual(len(zones), 28)

        # Check the 8 knight points
        knight_expected = [
            (5, 6), (7, 6), (4, 5), (8, 5),
            (4, 3), (8, 3), (5, 2), (7, 2)
        ]
        for pt in knight_expected:
            self.assertIn(pt, zones, f"Missing knight point {pt}")

    def test_commander_facing_bug_cmd_001(self):
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=6, y=0))
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=6, y=11))

        # Đang đối mặt trên cùng cột 6 không có vật cản
        self.assertTrue(is_commanders_facing([red_cmd, blue_cmd]))

        # Có vật cản ở giữa (x=6, y=5)
        obstacle = PieceState(piece_id="obs", side=Side.RED, type=PieceType.TANK, position=Position(x=6, y=5))
        self.assertFalse(is_commanders_facing([red_cmd, blue_cmd, obstacle]))

        # Khi Tư lệnh đỏ trú ẩn trong Sở chỉ huy: Sở chỉ huy che chở hoàn toàn (Q9)
        red_hq = PieceState(
            piece_id="r_hq",
            side=Side.RED,
            type=PieceType.HEADQUARTERS,
            position=Position(x=6, y=0),
            carrying_piece_ids=["r_cmd"],
        )
        red_cmd_in_hq = red_cmd.model_copy(update={"carried_by_id": "r_hq"})
        self.assertFalse(is_commanders_facing([red_cmd_in_hq, blue_cmd, red_hq]))

    def test_navy_attack_rules_q5_and_q8(self):
        red_navy = PieceState(piece_id="r_navy", side=Side.RED, type=PieceType.NAVY, position=Position(x=2, y=4))
        blue_navy_1 = PieceState(piece_id="b_navy_1", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=2, y=6))
        blue_navy_2 = PieceState(piece_id="b_navy_2", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=2, y=7))
        blue_inf = PieceState(piece_id="b_inf", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=3, y=4))

        pieces = [red_navy, blue_navy_1, blue_navy_2, blue_inf]
        state = GameState(
            game_id="test",
            mode="HUMAN_VS_HUMAN",
            status="IN_PROGRESS",
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase="NORMAL",
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=pieces,
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        actions = default_engine_adapter.get_legal_actions(state)
        navy_actions = [a for a in actions if a.piece_id == "r_navy"]

        # Q5: Hải quân chỉ tấn công hải quân địch ở phía trước (b_navy_1), không ăn b_navy_2 phía sau
        hit_navy_1 = any(a.target_piece_id == "b_navy_1" for a in navy_actions)
        hit_navy_2 = any(a.target_piece_id == "b_navy_2" for a in navy_actions)
        self.assertTrue(hit_navy_1)
        self.assertFalse(hit_navy_2)

        # Q8: Đánh quân ở đất liền sâu (b_inf tại x=3, y=4) bắt buộc CAPTURE_STAND
        inf_act = next((a for a in navy_actions if a.target_piece_id == "b_inf"), None)
        self.assertIsNotNone(inf_act)
        self.assertEqual(inf_act.action_type, ActionType.CAPTURE_STAND)

    def test_river_crossing_rule_river_001(self):
        # Cao xạ, Pháo binh, Tên lửa không được tự vượt sông sâu sang ô trống
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ANTI_AIR, 3, 5, 3, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 3, 5, 3, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.MISSILE, 3, 5, 3, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.MISSILE, 4, 5, 4, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 6, 5, 6, 6))

        # DEC-018: Tuyệt đối không được vượt sông sang ô trống theo đường chéo (dù có chạm x=5 hay x=7)
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.MISSILE, 4, 5, 5, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.MISSILE, 5, 5, 6, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.MISSILE, 6, 5, 7, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 4, 5, 5, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 6, 5, 7, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 7, 5, 8, 6))
        self.assertFalse(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 4, 4, 6, 6))

        # Nhưng qua sông ngầm THEO ĐƯỜNG THẲNG tại x=5 và x=7 thì được
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.ANTI_AIR, 5, 5, 5, 6))
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 5, 5, 5, 6))
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.MISSILE, 5, 5, 5, 6))
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.ANTI_AIR, 7, 5, 7, 6))
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.ARTILLERY, 7, 5, 7, 6))
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.MISSILE, 7, 5, 7, 6))

        # Xe tăng tự vượt sông sâu được
        self.assertTrue(can_piece_cross_river_to_empty(PieceType.TANK, 3, 5, 3, 6))

    def test_missile_and_artillery_deep_river_actions_and_captures(self):
        # Kiểm tra Tên lửa & Pháo binh: Không đi chéo/thẳng qua sông sâu sang ô trống,
        # nhưng ĂN THẾ CHỖ quân địch bên kia sông thì được phép
        red_msl = PieceState(piece_id="r_msl", side=Side.RED, type=PieceType.MISSILE, position=Position(x=4, y=5), is_alive=True)
        red_art = PieceState(piece_id="r_art", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=6, y=5), is_alive=True)
        blue_enemy1 = PieceState(piece_id="b_inf1", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=5, y=6), is_alive=True)
        blue_enemy2 = PieceState(piece_id="b_inf2", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=6, y=7), is_alive=True)
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=6, y=0), is_alive=True)
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=3, y=10), is_alive=True)

        state = GameState(
            game_id="g_msl_art_river",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_msl, red_art, blue_enemy1, blue_enemy2, red_cmd, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        legal_actions = default_engine_adapter.get_legal_actions(state)
        msl_actions = [a for a in legal_actions if a.piece_id == "r_msl"]
        art_actions = [a for a in legal_actions if a.piece_id == "r_art"]

        # 1. Tên lửa tại (4, 5):
        # - Không được đi ô trống thẳng tới (4, 6) hay (4, 7) qua sông sâu
        msl_empty_deep_straight = [a for a in msl_actions if a.action_type == ActionType.MOVE and a.to_pos.x == 4 and a.to_pos.y in (6, 7)]
        self.assertEqual(len(msl_empty_deep_straight), 0, "Tên lửa không được đi thẳng qua sông sâu sang ô trống")

        # - Không được đi ô trống chéo tới (3, 6) qua sông sâu
        msl_empty_deep_diag = [a for a in msl_actions if a.action_type == ActionType.MOVE and a.to_pos.x == 3 and a.to_pos.y == 6]
        self.assertEqual(len(msl_empty_deep_diag), 0, "Tên lửa không được đi chéo qua sông sâu sang ô trống")

        # - ĐƯỢC PHÉP ăn quân địch bên kia sông tại (5, 6) thế chỗ (CAPTURE_REPLACE)
        msl_capture_enemy1 = next((a for a in msl_actions if a.action_type == ActionType.CAPTURE_REPLACE and a.target_piece_id == "b_inf1"), None)
        self.assertIsNotNone(msl_capture_enemy1, "Tên lửa phải ăn được quân địch bên kia sông tại (5, 6) thế chỗ")

        # 2. Pháo binh tại (6, 5):
        # - Không được đi ô trống thẳng tới (6, 6) qua sông sâu
        art_empty_deep_straight = [a for a in art_actions if a.action_type == ActionType.MOVE and a.to_pos.x == 6 and a.to_pos.y == 6]
        self.assertEqual(len(art_empty_deep_straight), 0, "Pháo binh không được đi thẳng qua sông sâu sang ô trống")

        # - Không được đi ô trống chéo tới (7, 6) qua sông sâu (dù x=7 là ngầm nhưng đi chéo là qua sông sâu)
        art_empty_deep_diag = [a for a in art_actions if a.action_type == ActionType.MOVE and a.to_pos.x == 7 and a.to_pos.y == 6]
        self.assertEqual(len(art_empty_deep_diag), 0, "Pháo binh không được đi chéo qua sông sâu sang ô trống")

        # - ĐƯỢC PHÉP ăn quân địch bên kia sông thế chỗ:
        # Ăn b_inf1 tại (5, 6) chéo thế chỗ
        art_capture_enemy1 = next((a for a in art_actions if a.action_type == ActionType.CAPTURE_REPLACE and a.target_piece_id == "b_inf1"), None)
        self.assertIsNotNone(art_capture_enemy1, "Pháo binh phải ăn được b_inf1 tại (5, 6) thế chỗ qua sông")
        # Ăn b_inf2 tại (6, 7) thẳng thế chỗ (bắn xuyên ô trống (6, 6))
        art_capture_enemy2 = next((a for a in art_actions if a.action_type == ActionType.CAPTURE_REPLACE and a.target_piece_id == "b_inf2"), None)
        self.assertIsNotNone(art_capture_enemy2, "Pháo binh phải ăn được b_inf2 tại (6, 7) thế chỗ qua sông")

    def test_navy_blocked_by_intermediate_land_rule_1(self):
        # Rule 1: Tàu chiến ở (x=2, y=3) (bờ) đi chéo 4 đoạn về phía (x=4, y=5)
        # Giữa đường qua (x=3, y=4) là đất liền sâu => KHÔNG ĐƯỢC ĐI XUYÊN QUA ĐẤT LIỀN
        navy = PieceState(piece_id="r_navy", side=Side.RED, type=PieceType.NAVY, position=Position(x=2, y=3))
        state = GameState(
            game_id="test_navy_land",
            mode="HUMAN_VS_HUMAN",
            status="IN_PROGRESS",
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase="NORMAL",
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[navy],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )
        actions = default_engine_adapter.get_legal_actions(state)
        # Không được có nước đi tới (x=3, y=4) (đất liền) hoặc (x=4, y=5) (phía sau đất liền)
        destinations = [(a.to_pos.x, a.to_pos.y) for a in actions if a.piece_id == "r_navy"]
        self.assertNotIn((3, 4), destinations, "Navy cannot occupy deep land (3, 4)")
        self.assertNotIn((4, 5), destinations, "Navy cannot jump over intermediate land to reach (4, 5)")

    def test_missile_and_aircraft_sea_restrictions_rule_4(self):
        # Rule 4: Tên lửa và máy bay không thể di chuyển trên biển.
        # Máy bay được bay qua biển để lên tàu chiến đồng minh trên biển.
        missile = PieceState(piece_id="r_msl", side=Side.RED, type=PieceType.MISSILE, position=Position(x=2, y=4))
        aircraft = PieceState(piece_id="r_air", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=2, y=6))
        allied_navy = PieceState(piece_id="r_navy_sea", side=Side.RED, type=PieceType.NAVY, position=Position(x=1, y=6))

        state = GameState(
            game_id="test_sea_restr",
            mode="HUMAN_VS_HUMAN",
            status="IN_PROGRESS",
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase="NORMAL",
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[missile, aircraft, allied_navy],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )
        actions = default_engine_adapter.get_legal_actions(state)

        # Tên lửa không thể di chuyển vào ô biển (x <= 1)
        msl_moves = [a for a in actions if a.piece_id == "r_msl" and a.action_type == ActionType.MOVE]
        for m in msl_moves:
            self.assertGreaterEqual(m.to_pos.x, 2, f"Missile moved to sea {m.to_pos}")

        # Máy bay không thể MOVE đến ô biển trống
        air_moves = [a for a in actions if a.piece_id == "r_air" and a.action_type == ActionType.MOVE]
        for m in air_moves:
            self.assertGreaterEqual(m.to_pos.x, 2, f"Aircraft moved to empty sea square {m.to_pos}")

        # Nhưng Máy bay có quyền BOARD lên tàu chiến đồng minh trên biển (x=1, y=6)
        board_act = next((a for a in actions if a.piece_id == "r_air" and a.action_type == ActionType.BOARD and a.target_piece_id == "r_navy_sea"), None)
        self.assertIsNotNone(board_act, "Aircraft should be able to BOARD allied Navy on sea")

    def test_artillery_captures_replace_on_land_and_bombs_sea_rule_5(self):
        # Rule 5: Pháo binh chỉ có thể ăn thế chỗ, không thể thả bom trên đất liền.
        # Nhưng bắn tàu chiến địch ngoài biển sâu thì bắn tại chỗ (CAPTURE_STAND).
        art = PieceState(piece_id="r_art", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=2, y=4))
        enemy_inf_land = PieceState(piece_id="b_inf", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=3, y=4))
        enemy_navy_sea = PieceState(piece_id="b_navy", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=0, y=4))

        state = GameState(
            game_id="test_art_rules",
            mode="HUMAN_VS_HUMAN",
            status="IN_PROGRESS",
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase="NORMAL",
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[art, enemy_inf_land, enemy_navy_sea],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )
        actions = default_engine_adapter.get_legal_actions(state)
        art_attacks_land = [a for a in actions if a.piece_id == "r_art" and a.target_piece_id == "b_inf"]
        art_attacks_sea = [a for a in actions if a.piece_id == "r_art" and a.target_piece_id == "b_navy"]

        # Mục tiêu đất liền: CHỈ CÓ CAPTURE_REPLACE (không có CAPTURE_STAND)
        self.assertTrue(len(art_attacks_land) == 1)
        self.assertEqual(art_attacks_land[0].action_type, ActionType.CAPTURE_REPLACE)

        # Mục tiêu tàu biển sâu: BẮT BUỘC CAPTURE_STAND
        self.assertTrue(len(art_attacks_sea) == 1)
        self.assertEqual(art_attacks_sea[0].action_type, ActionType.CAPTURE_STAND)

    def test_aircraft_air_defense_rules_rule_3(self):
        # Rule 3: Máy bay khi di chuyển vào vùng phòng không bị tiêu diệt ngay lập tức.
        # Khi ăn quân trong vùng phòng không thì 1 đổi 1.
        enemy_aa = PieceState(piece_id="b_aa", side=Side.BLUE, type=PieceType.ANTI_AIR, position=Position(x=5, y=5))
        aircraft = PieceState(piece_id="r_air", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=5, y=2))
        enemy_inf_in_aa = PieceState(piece_id="b_inf", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=5, y=4))

        # (x=5, y=4) nằm trong vùng phòng không của Cao xạ tại (5, 5)
        state = GameState(
            game_id="test_aa_effect",
            mode="HUMAN_VS_HUMAN",
            status="IN_PROGRESS",
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase="NORMAL",
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[aircraft, enemy_aa, enemy_inf_in_aa],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # 1. Test di chuyển vào vùng phòng không trống (x=5, y=6)
        # (x=5, y=6) là vùng phòng không của b_aa
        move_req = ActionRequest(
            piece_id="r_air",
            action_type=ActionType.MOVE,
            to_pos=Position(x=5, y=6),
            state_version=1,
        )
        new_state, evt_move = default_engine_adapter.apply_action(state, move_req)
        actor_after_move = next(p for p in new_state.pieces if p.piece_id == "r_air")
        self.assertFalse(actor_after_move.is_alive, "Aircraft must be shot down immediately when entering AA zone")
        self.assertEqual(new_state.scores[Side.BLUE], 40, "Blue should be awarded 40 points for shooting down aircraft")
        self.assertEqual(evt_move.event_type, EventType.AIR_SHOT_DOWN)
        self.assertIn('@"', evt_move.notation)

        # 2. Test ăn quân trong vùng phòng không (1 đổi 1)
        attack_req = ActionRequest(
            piece_id="r_air",
            action_type=ActionType.CAPTURE_REPLACE,
            to_pos=Position(x=5, y=4),
            target_piece_id="b_inf",
            state_version=1,
        )
        new_state_atk, evt_atk = default_engine_adapter.apply_action(state, attack_req)
        actor_after_atk = next(p for p in new_state_atk.pieces if p.piece_id == "r_air")
        target_after_atk = next(p for p in new_state_atk.pieces if p.piece_id == "b_inf")
        self.assertFalse(actor_after_atk.is_alive, "Aircraft must die in 1-for-1 exchange in AA zone")
        self.assertFalse(target_after_atk.is_alive, "Target must die in 1-for-1 exchange in AA zone")
        self.assertEqual(new_state_atk.scores[Side.BLUE], 40, "Blue gains 40 pts for aircraft")
        self.assertEqual(new_state_atk.scores[Side.RED], 10, "Red gains 10 pts for infantry")
        self.assertEqual(evt_atk.event_type, EventType.AIR_EXCHANGE)
        self.assertIn("><", evt_atk.notation)

        # 3. Test bay xuyên qua vùng phòng không đến ô bên ngoài (AIR-01, Q11)
        # Điểm đến (5, 7) nằm ngoài tầm AA (chỉ bảo vệ 1 đoạn tại 5,6), nhưng đường bay cắt qua (5, 6)
        fly_through_req = ActionRequest(
            piece_id="r_air",
            action_type=ActionType.MOVE,
            to_pos=Position(x=5, y=7),
            state_version=1,
        )
        new_state_through, _ = default_engine_adapter.apply_action(state, fly_through_req)
        actor_through = next(p for p in new_state_through.pieces if p.piece_id == "r_air")
        self.assertFalse(actor_through.is_alive, "Aircraft must be shot down when flying across AA zone")

        # 4. Test tấn công trực tiếp đơn vị phòng không từ góc chéo (tâm vành đai lửa)
        diag_air = PieceState(piece_id="r_air_diag", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=4, y=4))
        state_diag = state.model_copy(update={"pieces": [diag_air, enemy_aa]})
        diag_attack_req = ActionRequest(
            piece_id="r_air_diag",
            action_type=ActionType.CAPTURE_REPLACE,
            to_pos=Position(x=5, y=5),
            target_piece_id="b_aa",
            state_version=1,
        )
        new_state_diag, evt_diag = default_engine_adapter.apply_action(state_diag, diag_attack_req)
        actor_diag = next(p for p in new_state_diag.pieces if p.piece_id == "r_air_diag")
        target_diag = next(p for p in new_state_diag.pieces if p.piece_id == "b_aa")
        self.assertFalse(actor_diag.is_alive, "Aircraft attacking AA directly must die in 1-for-1 exchange")
        self.assertFalse(target_diag.is_alive, "AA unit must be destroyed in 1-for-1 exchange")
        self.assertEqual(evt_diag.event_type, EventType.AIR_EXCHANGE)

    def test_commander_carrier_unloading_rule_2(self):
        # Rule 2: Quân cõng triển khai/di chuyển ra ngoài thì phương tiện phải cập nhật carrying_piece_ids
        tank = PieceState(piece_id="r_tank", side=Side.RED, type=PieceType.TANK, position=Position(x=4, y=4), carrying_piece_ids=["r_inf"])
        inf = PieceState(piece_id="r_inf", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=4, y=4), carried_by_id="r_tank")

        state = GameState(
            game_id="test_unload",
            mode="HUMAN_VS_HUMAN",
            status="IN_PROGRESS",
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase="NORMAL",
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[tank, inf],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Bộ binh triển khai ra ngoài đến (x=4, y=5)
        deploy_req = ActionRequest(
            piece_id="r_inf",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=5),
            state_version=1,
        )
        new_state, _ = default_engine_adapter.apply_action(state, deploy_req)
        tank_after = next(p for p in new_state.pieces if p.piece_id == "r_tank")
        inf_after = next(p for p in new_state.pieces if p.piece_id == "r_inf")

        self.assertIsNone(inf_after.carried_by_id, "Infantry should no longer be carried")
        self.assertNotIn("r_inf", tank_after.carrying_piece_ids, "Tank should no longer list infantry in carrying_piece_ids")

    def test_compound_action_turn_management(self):
        tank = PieceState(
            piece_id="r_tank",
            side=Side.RED,
            type=PieceType.TANK,
            position=Position(x=4, y=4),
            carrying_piece_ids=["r_inf"],
        )
        inf = PieceState(
            piece_id="r_inf",
            side=Side.RED,
            type=PieceType.INFANTRY,
            position=Position(x=4, y=4),
            carried_by_id="r_tank",
        )
        cmd_blue = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=6, y=10),
        )
        cmd_red = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=6, y=0),
        )
        from apps.api.src.models.enums import GameMode, GameStatus, TurnPhase
        state = GameState(
            game_id="test_compound",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[tank, inf, cmd_blue, cmd_red],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Nước đi 1 của tổ hợp: Xe tăng đi trước với is_compound_action=True
        req1 = ActionRequest(
            piece_id="r_tank",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=5),
            state_version=1,
            is_compound_action=True,
        )
        state2, _ = default_engine_adapter.apply_action(state, req1)
        self.assertEqual(state2.side_to_move, Side.RED, "side_to_move phải giữ nguyên là RED khi is_compound_action=True")
        self.assertEqual(state2.turn_phase, TurnPhase.STACK_ACTIVE)
        self.assertTrue(state2.can_end_turn)
        self.assertEqual(state2.action_index, 2)

        # Nước đi 2 của tổ hợp: Bộ binh đi tiếp với is_compound_action=False (kết thúc lượt tổ hợp)
        req2 = ActionRequest(
            piece_id="r_inf",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=6),
            state_version=2,
            is_compound_action=False,
        )
        state3, _ = default_engine_adapter.apply_action(state2, req2)
        self.assertEqual(state3.side_to_move, Side.BLUE, "side_to_move phải chuyển sang BLUE khi tổ hợp hoàn tất")
        self.assertEqual(state3.turn_phase, TurnPhase.NORMAL)
        self.assertFalse(state3.can_end_turn)
        self.assertEqual(state3.action_index, 1)

    def test_passenger_moves_first_then_carrier_moves(self):
        """Kiểm tra kịch bản quân được chở (dân quân) di chuyển trước, sau đó quân chở (xe tăng) di chuyển"""
        tank = PieceState(
            piece_id="r_tank",
            side=Side.RED,
            type=PieceType.TANK,
            position=Position(x=4, y=4),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=["r_militia"],
            carried_by_id=None,
        )
        militia = PieceState(
            piece_id="r_militia",
            side=Side.RED,
            type=PieceType.MILITIA,
            position=Position(x=4, y=4),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=[],
            carried_by_id="r_tank",
        )
        cmd_blue = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=10),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=[],
            carried_by_id=None,
        )
        cmd_red = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=0),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=[],
            carried_by_id=None,
        )
        state = GameState(
            game_id="g_compound_passenger_first",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[tank, militia, cmd_blue, cmd_red],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Bước 1: Dân quân rời xe tăng di chuyển đến (4, 5) với is_compound_action=True
        req1 = ActionRequest(
            piece_id="r_militia",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=5),
            state_version=1,
            is_compound_action=True,
        )
        state2, _ = default_engine_adapter.apply_action(state, req1)
        self.assertEqual(state2.side_to_move, Side.RED)
        self.assertEqual(state2.turn_phase, TurnPhase.STACK_ACTIVE)
        m2 = next(p for p in state2.pieces if p.piece_id == "r_militia")
        t2 = next(p for p in state2.pieces if p.piece_id == "r_tank")
        self.assertEqual(m2.position, Position(x=4, y=5))
        self.assertIsNone(m2.carried_by_id)
        self.assertEqual(t2.position, Position(x=4, y=4))
        self.assertEqual(t2.carrying_piece_ids, [])

        # Bước 2: Xe tăng di chuyển đến (5, 4) với is_compound_action=False
        req2 = ActionRequest(
            piece_id="r_tank",
            action_type=ActionType.MOVE,
            to_pos=Position(x=5, y=4),
            state_version=2,
            is_compound_action=False,
        )
        state3, _ = default_engine_adapter.apply_action(state2, req2)
        self.assertEqual(state3.side_to_move, Side.BLUE)
        self.assertEqual(state3.turn_phase, TurnPhase.NORMAL)
        m3 = next(p for p in state3.pieces if p.piece_id == "r_militia")
        t3 = next(p for p in state3.pieces if p.piece_id == "r_tank")
        self.assertEqual(m3.position, Position(x=4, y=5))
        self.assertEqual(t3.position, Position(x=5, y=4))
        self.assertEqual(t3.carrying_piece_ids, [])

    def test_hero_promotion_on_check(self):
        # Thiết lập: Xe tăng đỏ di chuyển đến chiếu Tư lệnh xanh
        tank = PieceState(
            piece_id="r_tank",
            side=Side.RED,
            type=PieceType.TANK,
            position=Position(x=4, y=5),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=[],
            carried_by_id=None,
        )
        inf = PieceState(
            piece_id="r_inf",
            side=Side.RED,
            type=PieceType.INFANTRY,
            position=Position(x=2, y=2),
            is_alive=True,
            is_hero=False,
        )
        cmd_blue = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=4, y=8),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=[],
            carried_by_id=None,
        )
        cmd_red = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=0),
            is_alive=True,
            is_hero=False,
            carrying_piece_ids=[],
            carried_by_id=None,
        )
        state = GameState(
            game_id="g_hero_check",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[tank, inf, cmd_blue, cmd_red],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Xe tăng di chuyển từ (4, 5) đến (4, 7), trực tiếp chiếu Tư lệnh xanh tại (4, 8)
        req = ActionRequest(
            piece_id="r_tank",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=7),
            state_version=1,
        )
        next_state, event = default_engine_adapter.apply_action(state, req)

        # Kiểm tra: Xe tăng được phong Anh hùng
        hero_tank = next(p for p in next_state.pieces if p.piece_id == "r_tank")
        self.assertTrue(hero_tank.is_hero, "Xe tăng phải được phong Anh hùng khi chiếu Tư lệnh")
        self.assertIn("> **T**", event.notation, f"Ký pháp phải có dấu chiếu và phong Anh hùng > **T**, got: {event.notation}")
        self.assertEqual(event.event_type, EventType.HERO_PROMOTION)

        # Khi đến lượt Xe tăng Anh hùng di chuyển tiếp, nó phải có đường chéo và tầm 1-3
        hero_state = next_state.model_copy(update={"side_to_move": Side.RED})
        legal_actions = default_engine_adapter.get_legal_actions(hero_state)
        tank_actions = [a for a in legal_actions if a.piece_id == "r_tank"]
        # Phải có nước đi chéo, ví dụ (5, 8) hoặc (3, 6)
        diag_targets = {(a.to_pos.x, a.to_pos.y) for a in tank_actions}
        self.assertIn((5, 8), diag_targets, "Xe tăng Anh hùng phải đi được đường chéo")
        self.assertIn((3, 6), diag_targets, "Xe tăng Anh hùng phải đi được đường chéo")

    def test_heroic_stealth_aircraft_immune_to_aa(self):
        # Máy bay Anh hùng lột xác thành máy bay tàng hình: miễn nhiễm vành đai lửa
        hero_aircraft = PieceState(
            piece_id="r_plane",
            side=Side.RED,
            type=PieceType.AIRCRAFT,
            position=Position(x=4, y=2),
            is_alive=True,
            is_hero=True,
        )
        cmd_red = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=0),
            is_alive=True,
        )
        blue_aa = PieceState(
            piece_id="b_aa",
            side=Side.BLUE,
            type=PieceType.ANTI_AIR,
            position=Position(x=4, y=5),
            is_alive=True,
        )
        cmd_blue = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=4, y=10),
            is_alive=True,
        )
        state = GameState(
            game_id="g_stealth_plane",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[hero_aircraft, cmd_red, blue_aa, cmd_blue],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Máy bay Anh hùng tấn công Cao xạ tại (4, 5)
        req = ActionRequest(
            piece_id="r_plane",
            action_type=ActionType.CAPTURE_REPLACE,
            to_pos=Position(x=4, y=5),
            target_piece_id="b_aa",
            state_version=1,
        )
        next_state, event = default_engine_adapter.apply_action(state, req)

        # Máy bay Anh hùng sống sót, không bị 1 đổi 1
        plane = next(p for p in next_state.pieces if p.piece_id == "r_plane")
        self.assertTrue(plane.is_alive, "Máy bay Anh hùng tàng hình không bị tiêu diệt 1 đổi 1")
        self.assertEqual(event.event_type, EventType.PIECE_CAPTURED)

    def test_hq_hero_promotion_when_only_hq_and_cmd(self):
        # Khi chỉ còn Tư lệnh và Sở chỉ huy -> Sở chỉ huy phong thành Bộ binh Anh hùng
        red_hq = PieceState(
            piece_id="r_hq",
            side=Side.RED,
            type=PieceType.HEADQUARTERS,
            position=Position(x=5, y=1),
            is_alive=True,
            is_hero=False,
        )
        red_cmd = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=0),
            is_alive=True,
        )
        blue_cmd = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=10),
            is_alive=True,
        )
        state = GameState(
            game_id="g_hq_hero",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_hq, red_cmd, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Thực hiện 1 nước đi bất kỳ (Tư lệnh đi sang ngang 4, 0)
        req = ActionRequest(
            piece_id="r_cmd",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=0),
            state_version=1,
        )
        next_state, _ = default_engine_adapter.apply_action(state, req)

        # Sở chỉ huy được phong thành Anh hùng
        hq = next(p for p in next_state.pieces if p.piece_id == "r_hq")
        self.assertTrue(hq.is_hero, "Sở chỉ huy phải được phong Anh hùng khi phe chỉ còn Tư lệnh và HQ")

        # Sở chỉ huy Anh hùng có thể di chuyển 8 hướng 1-2 đoạn như Bộ binh Anh hùng
        hq_state = next_state.model_copy(update={"side_to_move": Side.RED})
        legal_actions = default_engine_adapter.get_legal_actions(hq_state)
        hq_actions = [a for a in legal_actions if a.piece_id == "r_hq"]
        self.assertTrue(len(hq_actions) > 0, "Sở chỉ huy Anh hùng phải có nước đi")

    def test_no_hq_hero_promotion_when_two_hqs_and_cmd(self):
        # Yêu cầu DEC-015: Chỉ khi còn 1 Sở chỉ huy thì mới được phong Anh hùng.
        # Nếu còn 2 Sở chỉ huy và Tư lệnh thì Sở chỉ huy KHÔNG được phong Anh hùng.
        red_hq1 = PieceState(
            piece_id="r_hq1",
            side=Side.RED,
            type=PieceType.HEADQUARTERS,
            position=Position(x=5, y=1),
            is_alive=True,
            is_hero=False,
        )
        red_hq2 = PieceState(
            piece_id="r_hq2",
            side=Side.RED,
            type=PieceType.HEADQUARTERS,
            position=Position(x=7, y=1),
            is_alive=True,
            is_hero=False,
        )
        red_cmd = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=0),
            is_alive=True,
        )
        blue_cmd = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=3, y=10),
            is_alive=True,
        )
        state = GameState(
            game_id="g_two_hqs_no_hero",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_hq1, red_hq2, red_cmd, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Nước đi 1: Tư lệnh Đỏ di chuyển sang (4, 0)
        req = ActionRequest(
            piece_id="r_cmd",
            action_type=ActionType.MOVE,
            to_pos=Position(x=4, y=0),
            state_version=1,
        )
        next_state, _ = default_engine_adapter.apply_action(state, req)

        # Khi còn 2 Sở chỉ huy: KHÔNG có Sở chỉ huy nào được phong Anh hùng
        hq1 = next(p for p in next_state.pieces if p.piece_id == "r_hq1")
        hq2 = next(p for p in next_state.pieces if p.piece_id == "r_hq2")
        self.assertFalse(hq1.is_hero, "Sở chỉ huy 1 không được phong Anh hùng khi còn 2 HQ")
        self.assertFalse(hq2.is_hero, "Sở chỉ huy 2 không được phong Anh hùng khi còn 2 HQ")

        # Cả 2 HQ đều bất động (không có nước đi nào)
        hq_state = next_state.model_copy(update={"side_to_move": Side.RED})
        legal_actions = default_engine_adapter.get_legal_actions(hq_state)
        hq1_actions = [a for a in legal_actions if a.piece_id == "r_hq1"]
        hq2_actions = [a for a in legal_actions if a.piece_id == "r_hq2"]
        self.assertEqual(len(hq1_actions), 0, "HQ1 thường không thể di chuyển")
        self.assertEqual(len(hq2_actions), 0, "HQ2 thường không thể di chuyển")

        # Nước đi 2: Khi 1 HQ bị tiêu diệt (chỉ còn lại đúng 1 HQ) -> HQ còn lại được phong Anh hùng!
        # Giả lập hq1 bị tiêu diệt:
        remaining_pieces = [
            p.model_copy(update={"is_alive": False}) if p.piece_id == "r_hq1" else p
            for p in next_state.pieces
        ]
        state_one_hq = next_state.model_copy(update={
            "pieces": remaining_pieces,
            "side_to_move": Side.RED,
            "state_version": 2,
        })
        # Tư lệnh di chuyển sang (5, 0)
        req2 = ActionRequest(
            piece_id="r_cmd",
            action_type=ActionType.MOVE,
            to_pos=Position(x=5, y=0),
            state_version=2,
        )
        state_after_req2, _ = default_engine_adapter.apply_action(state_one_hq, req2)
        hq2_promoted = next(p for p in state_after_req2.pieces if p.piece_id == "r_hq2")
        self.assertTrue(hq2_promoted.is_hero, "Sở chỉ huy duy nhất còn lại PHẢI được phong Anh hùng")

    def test_navy_cannot_move_diagonal_through_land(self):
        # Kiểm tra theo yêu cầu Project Owner:
        # Tàu chiến ở vị trí (7, 2) không thể di chuyển đến vị trí (6, 3) hoặc (5, 4) theo đường chéo vì vướng đất liền.
        blue_navy = PieceState(
            piece_id="b_navy",
            side=Side.BLUE,
            type=PieceType.NAVY,
            position=Position(x=2, y=7),
            is_alive=True,
        )
        cmd_blue = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=4, y=10),
            is_alive=True,
        )
        cmd_red = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=5, y=0),
            is_alive=True,
        )
        state = GameState(
            game_id="g_navy_land_diag",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.BLUE,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[blue_navy, cmd_blue, cmd_red],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        legal_actions = default_engine_adapter.get_legal_actions(state)
        destinations = {(a.to_pos.x, a.to_pos.y) for a in legal_actions if a.piece_id == "b_navy"}

        # CẤM tuyệt đối di chuyển chéo vào (x=3, y=6) và (x=4, y=5) vì đường chéo (7, 2) và (6, 3) thuộc đất liền
        self.assertNotIn((3, 6), destinations, "Tàu chiến tại (7, 2) không được đi chéo vào (6, 3)")
        self.assertNotIn((4, 5), destinations, "Tàu chiến tại (7, 2) không được đi chéo vào (5, 4)")

        # Phải đi được dọc bờ biển (x=2, y=6), (x=2, y=8) và ra biển sâu (x=1, y=7)
        self.assertIn((2, 6), destinations, "Tàu chiến tại (7, 2) phải đi được dọc bờ biển xuống (6, 2)")
        self.assertIn((2, 8), destinations, "Tàu chiến tại (7, 2) phải đi được dọc bờ biển lên (8, 2)")
        self.assertIn((1, 7), destinations, "Tàu chiến tại (7, 2) phải đi được ra biển (7, 1)")

    def test_carrier_can_move_to_pick_up_passenger(self):
        # Kiểm tra tính năng: Phương tiện có thể di chuyển đến vị trí quân được cõng để cõng quân đó lên
        red_tank = PieceState(
            piece_id="r_tank",
            side=Side.RED,
            type=PieceType.TANK,
            position=Position(x=5, y=5),
            is_alive=True,
            carrying_piece_ids=[],
        )
        red_inf = PieceState(
            piece_id="r_inf",
            side=Side.RED,
            type=PieceType.INFANTRY,
            position=Position(x=5, y=7),  # 2 bước thẳng về phía trước
            is_alive=True,
        )
        red_cmd = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=6, y=0),
            is_alive=True,
        )
        blue_cmd = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=3, y=10),
            is_alive=True,
        )
        state = GameState(
            game_id="g_carrier_pickup",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_tank, red_inf, red_cmd, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        legal_actions = default_engine_adapter.get_legal_actions(state)
        tank_actions = [a for a in legal_actions if a.piece_id == "r_tank"]
        pickup_action = next(
            (a for a in tank_actions if a.action_type == ActionType.BOARD and a.target_piece_id == "r_inf"),
            None
        )
        self.assertIsNotNone(pickup_action, "Xe tăng phải có nước đi đón cõng Bộ binh tại (5, 7)")
        self.assertEqual(pickup_action.to_pos.x, 5)
        self.assertEqual(pickup_action.to_pos.y, 7)
        self.assertIn("^", pickup_action.notation)

        # Thực hiện nước đi đón cõng quân
        req = ActionRequest(
            piece_id="r_tank",
            action_type=ActionType.BOARD,
            to_pos=Position(x=5, y=7),
            target_piece_id="r_inf",
            state_version=1,
        )
        next_state, event = default_engine_adapter.apply_action(state, req)

        # Xe tăng di chuyển tới (5, 7) và đang cõng Bộ binh
        tank_after = next(p for p in next_state.pieces if p.piece_id == "r_tank")
        inf_after = next(p for p in next_state.pieces if p.piece_id == "r_inf")

        self.assertEqual(tank_after.position.x, 5)
        self.assertEqual(tank_after.position.y, 7)
        self.assertIn("r_inf", tank_after.carrying_piece_ids, "Xe tăng phải có r_inf trong danh sách cõng")

        self.assertEqual(inf_after.position.x, 5)
        self.assertEqual(inf_after.position.y, 7)
        self.assertEqual(inf_after.carried_by_id, "r_tank", "Bộ binh phải có carried_by_id là r_tank")

    def test_coast_pieces_can_board_navy_at_sea(self):
        # Kiểm tra quân ở bờ biển (x=2) có thể lên Tàu chiến đang đậu ngoài biển (x=1)
        red_navy = PieceState(
            piece_id="r_navy",
            side=Side.RED,
            type=PieceType.NAVY,
            position=Position(x=1, y=6),
            is_alive=True,
            carrying_piece_ids=[],
        )
        red_inf = PieceState(
            piece_id="r_inf",
            side=Side.RED,
            type=PieceType.INFANTRY,
            position=Position(x=2, y=6),
            is_alive=True,
        )
        red_cmd = PieceState(
            piece_id="r_cmd",
            side=Side.RED,
            type=PieceType.COMMANDER,
            position=Position(x=6, y=0),
            is_alive=True,
        )
        blue_cmd = PieceState(
            piece_id="b_cmd",
            side=Side.BLUE,
            type=PieceType.COMMANDER,
            position=Position(x=3, y=10),
            is_alive=True,
        )
        state = GameState(
            game_id="g_coast_board_navy",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_navy, red_inf, red_cmd, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        legal_actions = default_engine_adapter.get_legal_actions(state)
        inf_actions = [a for a in legal_actions if a.piece_id == "r_inf"]
        board_action = next(
            (a for a in inf_actions if a.action_type == ActionType.BOARD and a.target_piece_id == "r_navy"),
            None,
        )
        self.assertIsNotNone(board_action, "Bộ binh ở bờ biển (2, 6) phải lên được Tàu chiến ở biển (1, 6)")
        self.assertEqual(board_action.to_pos.x, 1)
        self.assertEqual(board_action.to_pos.y, 6)

    def test_all_five_carriers_passenger_matrix(self):
        # Kiểm tra đầy đủ 5 loại quân chở và danh sách quân được chở
        from apps.api.src.services.engine_adapter import can_board_carrier

        # 1. Xe tăng (TANK): chở Bộ binh, Dân quân, Tư lệnh (tối đa 2)
        tank = PieceState(piece_id="t", side=Side.RED, type=PieceType.TANK, position=Position(x=4, y=4), is_alive=True)
        inf = PieceState(piece_id="i", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=4, y=4), is_alive=True)
        militia = PieceState(piece_id="m", side=Side.RED, type=PieceType.MILITIA, position=Position(x=4, y=4), is_alive=True)
        cmd = PieceState(piece_id="c", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=4, y=4), is_alive=True)
        air = PieceState(piece_id="a", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=4, y=4), is_alive=True)
        art = PieceState(piece_id="art", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=4, y=4), is_alive=True)
        aa = PieceState(piece_id="aa", side=Side.RED, type=PieceType.ANTI_AIR, position=Position(x=4, y=4), is_alive=True)
        msl = PieceState(piece_id="msl", side=Side.RED, type=PieceType.MISSILE, position=Position(x=4, y=4), is_alive=True)

        self.assertTrue(can_board_carrier(inf, tank))
        self.assertTrue(can_board_carrier(militia, tank))
        self.assertTrue(can_board_carrier(cmd, tank))
        self.assertFalse(can_board_carrier(air, tank))
        self.assertFalse(can_board_carrier(art, tank))

        # 2. Không quân (AIRCRAFT): chở Bộ binh, Dân quân, Tư lệnh, Xe tăng (tối đa 2)
        self.assertTrue(can_board_carrier(inf, air))
        self.assertTrue(can_board_carrier(militia, air))
        self.assertTrue(can_board_carrier(cmd, air))
        self.assertTrue(can_board_carrier(tank, air))
        self.assertFalse(can_board_carrier(art, air))

        # 3. Hải quân (NAVY): chở Bộ binh, Dân quân, Tư lệnh, Xe tăng, Máy bay (tối đa 2)
        navy = PieceState(piece_id="n", side=Side.RED, type=PieceType.NAVY, position=Position(x=1, y=4), is_alive=True)
        self.assertTrue(can_board_carrier(inf, navy))
        self.assertTrue(can_board_carrier(militia, navy))
        self.assertTrue(can_board_carrier(cmd, navy))
        self.assertTrue(can_board_carrier(tank, navy))
        self.assertTrue(can_board_carrier(air, navy))
        self.assertFalse(can_board_carrier(art, navy))

        # 4. Công binh (ENGINEER): chở Pháo binh, Cao xạ, Tên lửa khi ở bờ sông (y=5 hoặc y=6)
        eng_river = PieceState(piece_id="e1", side=Side.RED, type=PieceType.ENGINEER, position=Position(x=4, y=5), is_alive=True)
        eng_land = PieceState(piece_id="e2", side=Side.RED, type=PieceType.ENGINEER, position=Position(x=4, y=3), is_alive=True)
        self.assertTrue(can_board_carrier(art, eng_river))
        self.assertTrue(can_board_carrier(aa, eng_river))
        self.assertTrue(can_board_carrier(msl, eng_river))
        self.assertFalse(can_board_carrier(inf, eng_river))
        self.assertFalse(can_board_carrier(art, eng_land), "Công binh không ở bờ sông không được cõng pháo")

        # 5. Sở chỉ huy (HEADQUARTERS): che chở Tư lệnh
        hq = PieceState(piece_id="hq", side=Side.RED, type=PieceType.HEADQUARTERS, position=Position(x=5, y=1), is_alive=True)
        hq_hero = PieceState(piece_id="hqh", side=Side.RED, type=PieceType.HEADQUARTERS, position=Position(x=5, y=1), is_alive=True, is_hero=True)
        self.assertTrue(can_board_carrier(cmd, hq))
        self.assertFalse(can_board_carrier(inf, hq))
        self.assertFalse(can_board_carrier(cmd, hq_hero), "Sở chỉ huy Anh hùng không còn cho ẩn nấp")

    def test_commander_cannot_move_into_attacked_square_dec_019(self):
        """Tư lệnh không được di chuyển vào ô bị đối phương ăn (chặn nước đi tự sát - DEC-019)"""
        # Red Commander tại (4, 1). Blue Tank tại (4, 4) đang kiểm soát cột 4.
        # Blue Commander ở (0, 11) xa xôi không cản.
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=4, y=1), is_alive=True)
        blue_tank = PieceState(piece_id="b_tank", side=Side.BLUE, type=PieceType.TANK, position=Position(x=4, y=4), is_alive=True)
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=0, y=11), is_alive=True)

        state = GameState(
            game_id="test_suicide",
            mode=GameMode.HUMAN_VS_HUMAN,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_cmd, blue_tank, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        actions = default_engine_adapter.get_legal_actions(state)
        cmd_actions = [a for a in actions if a.piece_id == "r_cmd"]

        # Ô (4, 2) và (4, 3) nằm trong tầm bắn thẳng của Xe tăng (4, 4) (Xe tăng tầm 2: (4, 3), (4, 2))
        hit_squares = {(a.to_pos.x, a.to_pos.y) for a in cmd_actions}
        self.assertNotIn((4, 2), hit_squares, "Tư lệnh không được phép đi vào ô (4, 2) bị Xe tăng đối phương kiểm soát!")
        # Các ô an toàn sang ngang như (3, 1), (5, 1) phải đi được
        self.assertIn((3, 1), hit_squares)
        self.assertIn((5, 1), hit_squares)

    def test_pinned_piece_cannot_expose_commander(self):
        """Quân đang chắn đường tấn công vào Tư lệnh không được di chuyển khiến Tư lệnh bị chiếu (Pinning)"""
        # Red Commander tại (4, 1). Red Infantry tại (4, 2). Blue Tank tại (4, 3) (tầm 2 đến (4, 1)).
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=4, y=1), is_alive=True)
        red_inf = PieceState(piece_id="r_inf", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=4, y=2), is_alive=True)
        blue_tank = PieceState(piece_id="b_tank", side=Side.BLUE, type=PieceType.TANK, position=Position(x=4, y=3), is_alive=True)
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=0, y=11), is_alive=True)

        state = GameState(
            game_id="test_pin",
            mode=GameMode.HUMAN_VS_HUMAN,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[red_cmd, red_inf, blue_tank, blue_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        actions = default_engine_adapter.get_legal_actions(state)
        inf_actions = [a for a in actions if a.piece_id == "r_inf"]

        # Bộ binh đi sang (3, 2) hoặc (5, 2) sẽ làm lộ Tư lệnh cho Xe tăng bắn -> bị cấm tuyệt đối
        inf_destinations = {(a.to_pos.x, a.to_pos.y) for a in inf_actions}
        self.assertNotIn((3, 2), inf_destinations, "Bộ binh không được rời cột khiến Tư lệnh bị chiếu!")
        self.assertNotIn((5, 2), inf_destinations, "Bộ binh không được rời cột khiến Tư lệnh bị chiếu!")
        # Nhưng ăn Xe tăng tại (4, 3) để hóa giải chiếu thì được
        self.assertIn((4, 3), inf_destinations)

    def test_checkmate_ends_game_with_winner_and_bonus(self):
        """Thắng trận khi chiếu hết Tư lệnh đối phương (DEC-019 & CHECKMATE)"""
        # Blue Commander ở góc (10, 11).
        # Red Tank 1 tại (9, 9), Red Tank 2 tại (10, 9), Red Infantry tại (8, 11) bảo vệ (9, 11).
        # Red Tank 1 di chuyển tới (9, 11), chiếu Blue Commander.
        # Blue Commander không thể đi đâu vì (9, 11) có bảo vệ, (10, 10) bị Tank 2 khống chế.
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=10, y=11), is_alive=True)
        red_tank1 = PieceState(piece_id="r_t1", side=Side.RED, type=PieceType.TANK, position=Position(x=9, y=9), is_alive=True)
        red_tank2 = PieceState(piece_id="r_t2", side=Side.RED, type=PieceType.TANK, position=Position(x=10, y=9), is_alive=True)
        red_inf = PieceState(piece_id="r_inf", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=8, y=11), is_alive=True)
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=0, y=0), is_alive=True)

        state = GameState(
            game_id="test_checkmate",
            mode=GameMode.HUMAN_VS_HUMAN,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=5,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[blue_cmd, red_tank1, red_tank2, red_inf, red_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Red Tank 1 di chuyển từ (9, 9) đến (9, 11) chiếu ngang Blue Commander tại (10, 11)
        req = ActionRequest(
            action_type=ActionType.MOVE,
            piece_id="r_t1",
            to_pos=Position(x=9, y=11),
            target_piece_id=None,
            state_version=1,
            is_compound_action=False,
        )

        next_state, event = default_engine_adapter.apply_action(state, req)

        self.assertEqual(next_state.status, GameStatus.GAME_OVER)
        self.assertIsNotNone(next_state.result)
        self.assertEqual(next_state.result.winner, "RED")
        self.assertEqual(next_state.result.reason, TerminationReason.CHECKMATE)
        self.assertEqual(next_state.scores["RED"], 50, "Thắng do chiếu hết phải được cộng 50 điểm thưởng")
        self.assertIn("#", event.notation, "Ký hiệu biên bản phải có dấu # khi chiếu hết")
        self.assertTrue(event.details.get("is_checkmate"), "Event details phải có is_checkmate == True")

    def test_ai_does_not_move_commander_into_danger_when_tactical_pieces_available(self):
        """AI không di chuyển Tư lệnh hiến mạng khi còn quân tác chiến (DEC-019 & AI King Safety)"""
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=5, y=11), is_alive=True)
        blue_inf = PieceState(piece_id="b_inf", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=4, y=10), is_alive=True)
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=0, y=0), is_alive=True)
        red_tank = PieceState(piece_id="r_tank", side=Side.RED, type=PieceType.TANK, position=Position(x=5, y=5), is_alive=True)

        state = GameState(
            game_id="test_ai_safety",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.BLUE,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[blue_cmd, blue_inf, red_cmd, red_tank],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        # Lựa chọn nước đi thông minh cho AI Blue
        chosen_action = select_smart_ai_action(state, Side.BLUE)
        self.assertIsNotNone(chosen_action)
        # Vì còn quân tác chiến (Bộ binh) nên AI không bao giờ chọn đi Tư lệnh
        self.assertEqual(chosen_action.piece_id, "b_inf")

    def test_ai_blocks_check_or_resolves_when_in_check(self):
        """Khi bị chiếu, AI bắt buộc phải chọn nước đi hóa giải chiếu (chặn, ăn quân hoặc chạy)"""
        # Blue Commander ở (5, 11). Red Tank ở (5, 9) chiếu thẳng vào (5, 11).
        # Blue Infantry ở (4, 10) có thể bước tới (5, 10) để chắn đường chiếu.
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=5, y=11), is_alive=True)
        blue_inf = PieceState(piece_id="b_inf", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=4, y=10), is_alive=True)
        red_tank = PieceState(piece_id="r_tank", side=Side.RED, type=PieceType.TANK, position=Position(x=5, y=9), is_alive=True)
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=0, y=0), is_alive=True)

        pieces = [blue_cmd, blue_inf, red_tank, red_cmd]
        self.assertTrue(is_commander_in_check(pieces, Side.BLUE), "Ban đầu Blue Commander phải đang bị chiếu!")

        state = GameState(
            game_id="test_ai_check_resolve",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.BLUE,
            turn_index=2,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=pieces,
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        chosen_action = select_smart_ai_action(state, Side.BLUE)
        self.assertIsNotNone(chosen_action)

        # Mô phỏng nước đi được AI chọn
        next_state, _ = default_engine_adapter.apply_action(
            state,
            ActionRequest(
                action_type=chosen_action.action_type,
                piece_id=chosen_action.piece_id,
                to_pos=chosen_action.to_pos,
                target_piece_id=chosen_action.target_piece_id,
                state_version=state.state_version,
            )
        )
        # Nước đi của AI phải hóa giải hoàn toàn trạng thái bị chiếu
        self.assertFalse(is_commander_in_check(next_state.pieces, Side.BLUE), "Sau nước đi của AI, Tư lệnh không còn bị chiếu!")

    def test_ai_commander_never_moves_into_attacked_square(self):
        """Khi chỉ còn Tư lệnh, Tư lệnh chỉ được đi vào ô an toàn tuyệt đối không bị đối phương ăn"""
        # Blue Commander ở (5, 11).
        # Red Tank ở (4, 9) kiểm soát cột 4 và các ô lân cận.
        # Blue chỉ còn duy nhất Tư lệnh.
        blue_cmd = PieceState(piece_id="b_cmd", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=5, y=11), is_alive=True)
        red_tank = PieceState(piece_id="r_tank", side=Side.RED, type=PieceType.TANK, position=Position(x=4, y=9), is_alive=True)
        red_cmd = PieceState(piece_id="r_cmd", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=0, y=0), is_alive=True)

        state = GameState(
            game_id="test_ai_king_only",
            mode=GameMode.HUMAN_VS_AI,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.BLUE,
            turn_index=3,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1000, "BLUE": 1000},
            pieces=[blue_cmd, red_tank, red_cmd],
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )

        chosen_action = select_smart_ai_action(state, Side.BLUE)
        self.assertIsNotNone(chosen_action)
        self.assertEqual(chosen_action.piece_id, "b_cmd")

        # Ô được chọn không bị kiểm soát bởi quân đối phương
        next_state, _ = default_engine_adapter.apply_action(
            state,
            ActionRequest(
                action_type=chosen_action.action_type,
                piece_id=chosen_action.piece_id,
                to_pos=chosen_action.to_pos,
                state_version=state.state_version,
            )
        )
        self.assertFalse(
            is_square_attacked_by_enemy(next_state.pieces, chosen_action.to_pos.x, chosen_action.to_pos.y, Side.RED),
            f"Ô {chosen_action.to_pos} AI chọn cho Tư lệnh không được là ô bị đối phương ăn!"
        )


if __name__ == "__main__":
    unittest.main()
