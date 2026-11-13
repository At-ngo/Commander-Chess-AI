# tests/test_heuristic_cchef.py
"""Bộ kiểm thử bắt buộc HE-01..HE-16 và bất biến hệ thống cho CCHEF Evaluator & HeuristicAgent."""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
import sys
import time

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = PROJECT_ROOT / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

from commander_game_engine import rules
from commander_game_engine.actions import ActionType, AtomicAction, TurnCommand, TurnCommandType
from commander_game_engine.board import Board
from commander_game_engine.engine import apply_action, preview_action
from commander_game_engine.game_state import GameState, Piece, PieceType, Player
from commander_game_engine.initial_setup import create_initial_state
from commander_game_engine.move_generator import generate_legal_actions

from agents import (
    CCHEFEvaluator,
    FEATURE_NAMES,
    HeuristicAgent,
    NoLegalActionsError,
)
from agents.evaluation import (
    EvalContext,
    TERMINAL_WIN_SCORE,
    VARIANT_ENABLED_FEATURES,
    VARIANT_NAMES,
    compute_action_tc,
    compute_observable_phase,
    normalize_weights,
    piece_value,
    side_king_risk,
    side_tr_risk,
)
from agents.evaluation.material_table import CCHEF_BASE_POINTS


def _mk_state(pieces: list[Piece], current_player: Player = Player.RED, turn_number: int = 1) -> GameState:
    st = GameState(
        board=Board(),
        pieces={p.id: p for p in pieces},
        current_player=current_player,
        turn_number=turn_number,
    )
    st.validate_structure()
    return st


def _mirror_y_state(state: GameState) -> GameState:
    """Đảo ngược bàn cờ Bắc <-> Nam và đổi chủ Đỏ <-> Xanh để kiểm chứng đối xứng HE-12."""
    rows = state.board.ROWS
    new_pieces: dict[str, Piece] = {}
    for pid, p in state.pieces.items():
        new_owner = Player.BLUE if p.owner == Player.RED else Player.RED
        new_pos = (rows - 1 - p.position[0], p.position[1]) if p.position is not None else None
        new_pieces[pid] = Piece(
            id=p.id,
            piece_type=p.piece_type,
            owner=new_owner,
            position=new_pos,
            carried_by=p.carried_by,
            cargo=list(p.cargo),
            is_heroic=p.is_heroic,
        )
    opp_player = Player.BLUE if state.current_player == Player.RED else Player.RED
    mirrored = GameState(
        board=Board(),
        pieces=new_pieces,
        current_player=opp_player,
        turn_number=state.turn_number,
    )
    mirrored.validate_structure()
    return mirrored


def test_he01_he02_he03_he04_material_and_stacks() -> None:
    """HE-01, HE-02, HE-03, HE-04: điểm quân chính thức HQ=10, Tư lệnh=0, tổ hợp cõng lồng, Anh hùng."""
    assert CCHEF_BASE_POINTS[PieceType.HEADQUARTERS] == 10.0
    assert CCHEF_BASE_POINTS[PieceType.COMMANDER] == 0.0

    # HE-01: Ăn Xe tăng đơn lẻ (20đ) (giữ >= 2 quân còn lại mỗi bên để không kích hoạt Q10 Anh hùng cuối cùng)
    s1 = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_mil_back", PieceType.MILITIA, Player.RED, (1, 8)),
        Piece("red_inf_back", PieceType.INFANTRY, Player.RED, (1, 9)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (4, 5)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 7)),
        Piece("blue_mil_back", PieceType.MILITIA, Player.BLUE, (10, 8)),
        Piece("blue_inf_back", PieceType.INFANTRY, Player.BLUE, (10, 9)),
        Piece("blue_tank_1", PieceType.TANK, Player.BLUE, (5, 5)),
    ])
    ev = CCHEFEvaluator({"variant": "H6"})
    act1 = AtomicAction(ActionType.CAPTURE, "red_tank_1", (4, 5), (5, 5), target_piece_id="blue_tank_1")
    res1 = preview_action(s1, act1)
    assert res1.accepted
    tc1 = compute_action_tc(s1, res1, Player.RED)
    assert tc1["gain"] == 20.0 and tc1["tc"] == 20.0
    assert ev.compute_raw_components(res1.state, Player.RED)["M"] == 20.0

    # HE-02: Xe tăng 20 chở Dân quân 10 bị diệt -> 30đ
    s2 = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_art_1", PieceType.ARTILLERY, Player.RED, (4, 5)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 7)),
        Piece("blue_tank_1", PieceType.TANK, Player.BLUE, (5, 5), cargo=["blue_mil_1"]),
        Piece("blue_mil_1", PieceType.MILITIA, Player.BLUE, None, carried_by="blue_tank_1"),
    ])
    ctx2 = EvalContext.from_state(s2)
    assert ctx2.stack_value("blue_tank_1") == 30.0
    act2 = AtomicAction(ActionType.CAPTURE, "red_art_1", (4, 5), (5, 5), target_piece_id="blue_tank_1")
    res2 = preview_action(s2, act2)
    assert res2.accepted and compute_action_tc(s2, res2, Player.RED)["gain"] == 30.0

    # HE-03: Máy bay 40 -> Xe tăng 20 -> Dân quân 10 bị diệt -> 70đ (lồng 3 tầng)
    s3 = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_art_1", PieceType.ARTILLERY, Player.RED, (3, 5)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 7)),
        Piece("blue_air_1", PieceType.AIRCRAFT, Player.BLUE, (5, 5), cargo=["blue_tank_1"]),
        Piece("blue_tank_1", PieceType.TANK, Player.BLUE, None, carried_by="blue_air_1", cargo=["blue_mil_1"]),
        Piece("blue_mil_1", PieceType.MILITIA, Player.BLUE, None, carried_by="blue_tank_1"),
    ])
    ctx3 = EvalContext.from_state(s3)
    assert ctx3.stack_value("blue_air_1") == 70.0
    act3 = AtomicAction(ActionType.CAPTURE, "red_art_1", (3, 5), (5, 5), target_piece_id="blue_air_1")
    res3 = preview_action(s3, act3)
    assert res3.accepted and compute_action_tc(s3, res3, Player.RED)["gain"] == 70.0

    # HE-04: Quân Anh hùng +10đ Material và tăng tầm (qua mobility/control)
    s_norm_inf = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_inf_1", PieceType.INFANTRY, Player.RED, (4, 5)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
        Piece("blue_inf_1", PieceType.INFANTRY, Player.BLUE, (7, 5)),
    ])
    s_hero_inf = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_inf_1", PieceType.INFANTRY, Player.RED, (4, 5), is_heroic=True),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
        Piece("blue_inf_1", PieceType.INFANTRY, Player.BLUE, (7, 5)),
    ])
    raw_n = ev.compute_raw_components(s_norm_inf, Player.RED)
    raw_h = ev.compute_raw_components(s_hero_inf, Player.RED)
    assert raw_h["M"] - raw_n["M"] == 10.0
    assert raw_h["C"] > raw_n["C"]


def test_he05_he06_king_safety_and_checkmate() -> None:
    """HE-05: Chiếu nhưng quân chiếu bị ăn hợp lệ & an toàn => Risk ≈ 0.
    HE-06: Chiếu hết hợp lệ => thắng tuyệt đối +TERMINAL_WIN_SCORE.
    """
    # HE-05: Pháo xanh chiếu Tư lệnh đỏ ở (0,6), nhưng Xe tăng đỏ (2,7) / Pháo đỏ (2,6) ăn an toàn không bị bắt lại
    s_safe_check = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (2, 7)),
        Piece("red_art_guard", PieceType.ARTILLERY, Player.RED, (0, 8)),
        Piece("blue_art_chk", PieceType.ARTILLERY, Player.BLUE, (2, 6)),  # Đang chiếu (0,6), bị red_tank_1 ăn kề an toàn
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 3)),
    ])
    ctx_sc = EvalContext.from_state(s_safe_check)
    assert ctx_sc.cmd_in_check[Player.RED]
    risk_safe = side_king_risk(ctx_sc, Player.RED)
    assert risk_safe <= 0.1, f"Ăn quân chiếu an toàn phải có Risk ≈ 0, nhưng nhận được {risk_safe}"

    # So sánh với thế chiếu thật sự nguy hiểm (không ăn lại được, Tư lệnh bị ép chạy vào góc kẹt ít ô thoát)
    s_real_danger = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 10)),
        Piece("blue_art_chk", PieceType.ARTILLERY, Player.BLUE, (3, 10)),   # Đang chiếu thẳng (0,10) ở tầm 3
        Piece("blue_art_cov", PieceType.ARTILLERY, Player.BLUE, (3, 9)),    # Khống chế ô chạy (0,9)
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 3)),
    ])
    ctx_rd = EvalContext.from_state(s_real_danger)
    assert ctx_rd.cmd_in_check[Player.RED]
    risk_danger = side_king_risk(ctx_rd, Player.RED)
    assert risk_danger > risk_safe + 3.0

    # HE-06: Chiếu hết hợp lệ vượt qua mọi trọng số vị trí
    # Tư lệnh Xanh ở (11, 10) bị Xe tăng Đỏ chặn cột 9 và Pháo Đỏ sắp chiếu hết
    s_mate = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 3)),
        Piece("red_art_1", PieceType.ARTILLERY, Player.RED, (9, 8)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (10, 8)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 10)),
        Piece("blue_inf_block", PieceType.INFANTRY, Player.BLUE, (11, 9)),
    ])
    # Đỏ đưa Tank tới (10,9) hoặc Artillery tới (11,8) chiếu/chiếu hết? Kiểm tra bằng agent cực trị vị trí!
    agent_extreme = HeuristicAgent(
        seed=2026,
        config={
            "variant": "H6",
            "weights": {"M": 0.01, "K": 0.01, "Q": 0.01, "P": 100.0, "C": 0.01, "D": 0.01, "T": 0.01},
        },
    )
    # Đặt thế cờ trực tiếp có nước ăn/chiếu hết rõ: Blue CM ở (11,10), bị Đỏ kiểm soát thoát:
    s_mate2 = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 2)),
        Piece("red_tank_guard", PieceType.TANK, Player.RED, (10, 9)),
        Piece("red_art_mate", PieceType.ARTILLERY, Player.RED, (8, 10)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 10)),
    ])
    # Trong s_mate2 Đỏ ăn được (11,10) trực tiếp (hoặc test mate không ăn được ngay nếu Blue vừa di chuyển):
    dec = agent_extreme.select_action(s_mate2, generate_legal_actions(s_mate2))
    assert dec.metadata["is_terminal_candidate"] is True
    assert dec.metadata["heuristic_score"] >= TERMINAL_WIN_SCORE * 0.99


def test_he07_he08_he09_he14_compound_turn_and_co() -> None:
    """HE-07 (không đếm trùng khi Compound diệt 2 quân), HE-08 (mạnh ăn + yếu chiếu),
    HE-09 (cập nhật M/P sau toàn lượt), HE-14 (CompoundAction tính 1 ply).
    """
    # HE-07 & HE-08: Tank(20) Đỏ tại (7, 5) đang chở Bộ binh(10) tại cùng ô;
    # - Trước mặt (8, 5) có Pháo Xanh (30) để Tank ăn.
    # - Bộ binh Đỏ sau khi Tank đang kẹt ở (7, 5) có thể triển khai sang (7, 6) CHIẾU Tư lệnh Xanh tại (8, 6)!
    s_combo = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 3)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (7, 5), cargo=["red_inf_1"]),
        Piece("red_inf_1", PieceType.INFANTRY, Player.RED, None, carried_by="red_tank_1"),
        Piece("blue_art_1", PieceType.ARTILLERY, Player.BLUE, (8, 5)),
        Piece("blue_mil_1", PieceType.MILITIA, Player.BLUE, (7, 6)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (8, 7)),
    ])
    # Cho phép Infantry tách xuống ăn Militia (7,6) và Tank ăn Artillery (8,5) trong CÙNG 1 LƯỢT (1 ply)!
    agent_co_on = HeuristicAgent(
        seed=42,
        config={"variant": "H6", "enable_compound_lookahead": True, "enable_co_synergy": True, "tie_breaking": "deterministic"},
    )
    agent_co_off = HeuristicAgent(
        seed=42,
        config={"variant": "H6", "enable_compound_lookahead": False, "enable_co_synergy": False, "tie_breaking": "deterministic"},
    )
    legal_0 = generate_legal_actions(s_combo)
    dec_on = agent_co_on.select_action(s_combo, legal_0)
    assert dec_on.action in legal_0
    # HE-14: Áp dụng bước 1 (khi tách/tổ hợp) vẫn giữ turn_number = 1 (cùng 1 ply!), chỉ tăng sau END_TURN hoặc bước cuối!
    res_step1 = apply_action(s_combo, dec_on.action)
    assert res_step1.accepted
    if res_step1.state.compound_turn is not None:
        assert res_step1.state.turn_number == 1  # Chưa sang lượt Blue
        legal_1 = generate_legal_actions(res_step1.state)
        dec_step2 = agent_co_on.select_action(res_step1.state, legal_1)
        res_step2 = apply_action(res_step1.state, dec_step2.action)
        assert res_step2.accepted
        # Kiểm tra HE-07: nếu đã ăn cả 2 quân Xanh (Artillery 30 + Militia 10 = 40), delta M(s_eot) đúng bằng 40 + Hero(nếu phong)!
        removed_enemies = (set(s_combo.pieces) - set(res_step2.state.pieces)) & {"blue_art_1", "blue_mil_1"}
        if len(removed_enemies) == 2:
            ev = CCHEFEvaluator({"variant": "H6"})
            m_before = ev.compute_raw_components(s_combo, Player.RED)["M"]
            m_after = ev.compute_raw_components(res_step2.state, Player.RED)["M"]
            # Chỉ tăng đúng phần quân địch bị loại (40) + hero promotion nếu chiếu (10)
            hero_delta = 10.0 * sum(
                1 for pid, p in res_step2.state.pieces.items()
                if p.owner == Player.RED and p.is_heroic and not s_combo.pieces[pid].is_heroic
            )
            assert math.isclose(m_after - m_before, 40.0 + hero_delta, abs_tol=1e-9)

    assert agent_co_on.select_action(s_combo, legal_0).metadata["co_enabled"] is True
    assert agent_co_off.select_action(s_combo, legal_0).metadata["co_enabled"] is False


def test_he10_he11_stack_risk_and_aa_danger() -> None:
    """HE-10: Tổ hợp mình cõng nhau bị đe dọa => TR phản ánh V_stack(u, s).
    HE-11: Máy bay thường đứng trong vùng Phòng không => bị trừ P và tăng TR rõ rệt.
    """
    s_stack_danger = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (5, 5), cargo=["red_mil_1"]),
        Piece("red_mil_1", PieceType.MILITIA, Player.RED, None, carried_by="red_tank_1"),
        Piece("blue_inf_att", PieceType.INFANTRY, Player.BLUE, (6, 5)),  # Nhắm ăn thẳng vào tổ hợp 30đ
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
    ])
    tr_red = side_tr_risk(EvalContext.from_state(s_stack_danger), Player.RED)
    assert tr_red >= 24.0, f"Tổ hợp Tank(20)+Militia(10) bị uy hiếp không người giữ phải có TR lớn (>=24), got {tr_red}"

    # So sánh khi Không cõng (chỉ Tank 20đ bị uy hiếp)
    s_solo = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (5, 5)),
        Piece("blue_inf_att", PieceType.INFANTRY, Player.BLUE, (6, 5)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
    ])
    tr_solo = side_tr_risk(EvalContext.from_state(s_solo), Player.RED)
    assert tr_red > tr_solo

    # HE-11: Máy bay nằm trong lưới Phòng không địch vs ngoài lưới AA
    s_air_in_aa = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 3)),
        Piece("red_air_1", PieceType.AIRCRAFT, Player.RED, (6, 5)),
        Piece("blue_aa_1", PieceType.ANTI_AIRCRAFT, Player.BLUE, (7, 5)),  # Kiểm soát (6,5)
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 8)),
    ])
    s_air_safe = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 3)),
        Piece("red_air_1", PieceType.AIRCRAFT, Player.RED, (6, 5)),
        Piece("blue_aa_1", PieceType.ANTI_AIRCRAFT, Player.BLUE, (9, 9)),  # Xa tầm AA
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 8)),
    ])
    ev = CCHEFEvaluator({"variant": "H6"})
    c_aa = ev.compute_raw_components(s_air_in_aa, Player.RED)
    c_safe = ev.compute_raw_components(s_air_safe, Player.RED)
    assert c_aa["P"] < c_safe["P"]
    assert c_aa["T"] < c_safe["T"]

    # Hồi quy đòn bắn tại chỗ BOMBARD của Hải quân vào đất liền:
    # Tank (4,5) giữ (5,5) nhưng KHÔNG với tới Navy(8,2) -> Air(5,5) vẫn gánh TR lớn!
    s_navy_bombard = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_air_1", PieceType.AIRCRAFT, Player.RED, (5, 5)),
        Piece("red_tank_guard", PieceType.TANK, Player.RED, (4, 5)),
        Piece("blue_navy_2", PieceType.NAVY, Player.BLUE, (8, 2)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
    ])
    tr_bombard = side_tr_risk(EvalContext.from_state(s_navy_bombard), Player.RED)
    assert tr_bombard >= 30.0, f"Máy bay 40đ dưới pháo hạm tại chỗ dù có Tank giữ tại ô phải có TR >= 30, got {tr_bombard}"


def test_he12_he13_symmetry_and_commander_exposure() -> None:
    """HE-12: Đảo góc nhìn E(s, Đỏ) == -E(s, Xanh) trên mọi H1..H7 & đối xứng bàn cờ khởi tạo == 0.
    HE-13: Nước làm lộ mặt Tư lệnh KHÔNG nằm trong legal_actions.
    """
    init_state = create_initial_state()
    asym_state = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_tank_1", PieceType.TANK, Player.RED, (4, 5), cargo=["red_inf_1"]),
        Piece("red_inf_1", PieceType.INFANTRY, Player.RED, None, carried_by="red_tank_1"),
        Piece("red_navy_1", PieceType.NAVY, Player.RED, (3, 1), cargo=["red_air_1"]),
        Piece("red_air_1", PieceType.AIRCRAFT, Player.RED, None, carried_by="red_navy_1"),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
        Piece("blue_art_1", PieceType.ARTILLERY, Player.BLUE, (8, 7)),
        Piece("blue_aa_1", PieceType.ANTI_AIRCRAFT, Player.BLUE, (9, 5)),
    ])
    mirrored = _mirror_y_state(asym_state)

    for var in VARIANT_NAMES:
        ev = CCHEFEvaluator({"variant": var})
        s_init_r, _, _ = ev.evaluate_state(init_state, Player.RED)
        s_init_b, _, _ = ev.evaluate_state(init_state, Player.BLUE)
        assert math.isclose(s_init_r, 0.0, abs_tol=1e-7), f"{var} initial RED != 0: {s_init_r}"
        assert math.isclose(s_init_b, 0.0, abs_tol=1e-7), f"{var} initial BLUE != 0: {s_init_b}"

        sc_r, _, _ = ev.evaluate_state(asym_state, Player.RED)
        sc_b, _, _ = ev.evaluate_state(asym_state, Player.BLUE)
        assert math.isclose(sc_r, -sc_b, abs_tol=1e-9), f"{var}: RED={sc_r} != -BLUE={-sc_b}"

        sc_mir_b, _, _ = ev.evaluate_state(mirrored, Player.BLUE)
        assert math.isclose(sc_r, sc_mir_b, abs_tol=1e-9), f"{var} mirror mismatch: {sc_r} vs {sc_mir_b}"

    # Kiểm tra pha H7 đối xứng hoàn toàn giữa Đỏ và Xanh
    ph_orig = compute_observable_phase(asym_state)
    ph_mir = compute_observable_phase(mirrored)
    assert ph_orig["phase_label"] == ph_mir["phase_label"]
    assert math.isclose(ph_orig["opening"], ph_mir["opening"], abs_tol=1e-9)
    assert math.isclose(ph_orig["endgame"], ph_mir["endgame"], abs_tol=1e-9)

    # HE-13: Hai Tư lệnh đứng cùng cột 6, có 1 Bộ binh đứng chắn tại (5,6) -> nước rời cột 6 KHÔNG hợp lệ
    s_face = _mk_state([
        Piece("red_cmd", PieceType.COMMANDER, Player.RED, (0, 6)),
        Piece("red_inf_shield", PieceType.INFANTRY, Player.RED, (5, 6)),
        Piece("blue_cmd", PieceType.COMMANDER, Player.BLUE, (11, 6)),
    ])
    legal_f = generate_legal_actions(s_face)
    assert not any(
        isinstance(a, AtomicAction) and a.piece_id == "red_inf_shield" and a.end is not None and a.end[1] != 6
        for a in legal_f
    )
    bad_action = AtomicAction(ActionType.MOVE, "red_inf_shield", (5, 6), (5, 5))
    assert not apply_action(s_face, bad_action).accepted


def test_he15_he16_variants_ablation_validation_and_safety() -> None:
    """HE-15 (tái lập theo seed), HE-16 (tắt từng thành phần H6 + kiểm tra trọng số H1..H7),
    cộng không đột biến GameState và lỗi rỗng legal_actions.
    """
    init_state = create_initial_state()
    legal = generate_legal_actions(init_state)

    # HE-15: Tái lập
    cfg_h6 = {"variant": "H6", "tie_breaking": "random"}
    a1 = HeuristicAgent(seed=1337, config=cfg_h6)
    a2 = HeuristicAgent(seed=1337, config=cfg_h6)
    state_before = deepcopy(init_state)
    d1 = a1.select_action(init_state, legal)
    d2 = a2.select_action(init_state, legal)
    assert d1.action == d2.action
    assert d1.metadata["heuristic_components"] == d2.metadata["heuristic_components"]
    # Không đột biến
    assert init_state.current_player == state_before.current_player
    assert len(init_state.pieces) == len(state_before.pieces)

    # HE-16: Bật/tắt từng đặc trưng M..T và tái chuẩn hóa hợp lệ
    for feat in FEATURE_NAMES:
        subset = [f for f in FEATURE_NAMES if f != feat]
        ag = HeuristicAgent(seed=7, config={"variant": "H6", "enabled_features": subset})
        assert ag.effective_weights[feat] == 0.0
        assert math.isclose(sum(ag.effective_weights.values()), 1.0, abs_tol=1e-9)
        dec = ag.select_action(init_state, legal)
        assert dec.action in legal
        assert dec.metadata["heuristic_components"][feat] == 0.0
        assert all(math.isfinite(v) for v in dec.metadata["heuristic_components"].values())

    # Lộ trình H1 -> H7 bật đúng các đặc trưng đặc tả và cờ CO (H1..H5: CO=False, H6..H7: CO=True)
    for var in VARIANT_NAMES:
        ev = CCHEFEvaluator({"variant": var})
        ag_v = HeuristicAgent(config={"variant": var})
        expected_co = var in ("H6", "H7")
        assert set(ev.enabled_features) == set(VARIANT_ENABLED_FEATURES[var])
        assert ag_v.enabled_components == VARIANT_ENABLED_FEATURES[var]
        assert ag_v.enable_compound_lookahead is expected_co
        assert ag_v.enable_co_synergy is expected_co
        assert math.isclose(sum(ev.effective_weights.values()), 1.0, abs_tol=1e-9)

    # Đảm bảo config mặc định trong experiment `09_test_heuristic_agent` không làm rò rỉ H6 sang H1..H5
    exp_dir = PROJECT_ROOT / "research" / "experiments"
    if str(exp_dir) not in sys.path:
        sys.path.insert(0, str(exp_dir))
    from common import create_agent, load_experiment_config  # noqa: E402

    base_heu_cfg = load_experiment_config("09_test_heuristic_agent")["agent_configs"]["heuristic"]
    for var in VARIANT_NAMES:
        expected_co = var in ("H6", "H7")
        ag_cfg = create_agent("heuristic", config={**base_heu_cfg, "variant": var}, seed=2026)
        assert ag_cfg.enabled_components == VARIANT_ENABLED_FEATURES[var]
        assert ag_cfg.enable_compound_lookahead is expected_co
        assert ag_cfg.enable_co_synergy is expected_co

    # Validation lỗi trọng số âm / tổng 0 / rỗng legal actions
    with pytest.raises(ValueError):
        normalize_weights({"M": -0.1, "P": 0.5, "C": 0.6}, ("M", "P", "C"))
    with pytest.raises(NoLegalActionsError):
        a1.select_action(init_state, [])


def test_cchef_latency_under_controlled_budget() -> None:
    """Đảm bảo thời gian quyết định đơn bước trên trạng thái khai cuộc & CompoundTurn dưới ngưỡng 1000 ms."""
    init_state = create_initial_state()
    legal = generate_legal_actions(init_state)
    agent = HeuristicAgent(seed=2026, config={"variant": "H7"})

    t0 = time.perf_counter()
    dec = agent.select_action(init_state, legal)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert dec.action in legal
    assert elapsed_ms < 850.0, f"H7 vượt gần ngân sách 1000 ms: {elapsed_ms:.2f} ms"
