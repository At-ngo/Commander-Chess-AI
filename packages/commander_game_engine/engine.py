# packages/commander_game_engine/engine.py
"""Bộ chuyển trạng thái (transition engine) cho Cờ Tư Lệnh.

Nguyên tắc kiến trúc:
* ``rules.py`` kiểm tra hình học, địa hình, vật cản, vận chuyển, vùng phòng không,
  đối mặt Tư lệnh và quy tắc an toàn Tư lệnh.
* ``engine.py`` thực thi trên BẢN SAO GameState, không sửa trạng thái nguồn.
* Hỗ trợ đầy đủ: 11 loại quân (kể cả Không quân & Sở chỉ huy), BOARD/PICKUP/DEPLOY,
  lượt ghép tổ hợp (tối đa 3 hành động + TurnCommand.END_TURN), vùng phòng không
  (bắn hạ / 1 đổi 1 cả quân ngồi trên máy bay), phong Anh hùng (khi chiếu, quân
  cuối cùng, và phong trễ cho Sở chỉ huy duy nhất), Chiếu hết (CHECKMATE +50)
  và Hòa cờ bí (STALEMATE DRAW).
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .actions import ActionType, AtomicAction, TurnCommand, TurnCommandType
from .game_state import CompoundTurnState, GameState, GameStatus, PieceType, Player
from . import rules


PIECE_POINTS: dict[PieceType, int] = {
    PieceType.COMMANDER: 100,
    PieceType.HEADQUARTERS: 100,
    PieceType.INFANTRY: 10,
    PieceType.MILITIA: 10,
    PieceType.TANK: 20,
    PieceType.ARTILLERY: 30,
    PieceType.ANTI_AIRCRAFT: 10,
    PieceType.MISSILE: 20,
    PieceType.AIRCRAFT: 40,
    PieceType.NAVY: 80,
    PieceType.ENGINEER: 10,
}


class EngineEventType(Enum):
    """Các sự kiện giúp frontend và notebook giải thích diễn biến ván."""
    MOVED = "moved"                    # Quân thay đổi tọa độ
    CAPTURED = "captured"              # Quân đối phương bị tiêu diệt
    CARGO_LOST = "cargo_lost"          # Quân chở bị tiêu diệt theo phương tiện
    POINTS_AWARDED = "points_awarded"  # Ghi điểm từ quân bị tiêu diệt
    HERO_PROMOTED = "hero_promoted"    # Phong Anh hùng
    AIR_SHOT_DOWN = "air_shot_down"    # Máy bay bị phòng không bắn hạ
    AIR_EXCHANGE = "air_exchange"      # Máy bay 1 đổi 1 trong vùng phòng không
    HQ_DESTROYED = "hq_destroyed"      # Sở chỉ huy bị phá hủy, Tư lệnh lộ diện
    TURN_CHANGED = "turn_changed"      # Đổi phe đến lượt
    GAME_WON = "game_won"              # Kết thúc ván có phe thắng
    GAME_DRAW = "game_draw"            # Kết thúc ván hòa (ví dụ Stalemate)


@dataclass(frozen=True)
class EngineEvent:
    """Một sự kiện sau khi engine áp dụng thành công hành động."""
    event_type: EngineEventType             # Loại sự kiện
    piece_id: str | None = None             # ID quân liên quan
    detail: str = ""                        # Diễn giải tiếng Việt
    points: int = 0                         # Điểm cộng bởi sự kiện này


@dataclass
class EngineResult:
    """Kết quả áp dụng hành động (luôn chứa trạng thái độc lập)."""
    accepted: bool                         # Hành động được chấp nhận?
    state: GameState                       # Bản sao trạng thái sau xử lý
    verdict: rules.RuleResult              # Kết quả kiểm tra luật
    events: list[EngineEvent] = field(default_factory=list)
    winner: Player | None = None           # Phe thắng nếu có
    terminal: bool = False                 # Trận đã kết thúc chưa?
    terminal_reason: str | None = None     # CHECKMATE | STALEMATE | COMMANDER_CAPTURED


def _opponent(player: Player) -> Player:
    return Player.BLUE if player == Player.RED else Player.RED


def _fail(state: GameState, code: rules.RuleCode, reason: str) -> EngineResult:
    return EngineResult(False, deepcopy(state), rules.reject(code, reason))


def _children(state: GameState, parent_id: str) -> set[str]:
    """Lấy toàn bộ quân con/cháu đang được chở, có phát hiện chu trình."""
    collected: set[str] = set()
    visiting: set[str] = set()

    def walk(pid: str) -> None:
        if pid in visiting:
            raise ValueError("Phát hiện chu trình chở quân trong GameState.")
        visiting.add(pid)
        p = state.pieces[pid]
        direct_from_parent = {q.id for q in state.pieces.values() if q.carried_by == pid}
        direct_from_cargo = set(p.cargo)
        if len(p.cargo) != len(direct_from_cargo) or direct_from_parent != direct_from_cargo:
            raise ValueError(f"Quan hệ cargo/carried_by không nhất quán tại {pid}.")
        for child_id in p.cargo:
            if child_id not in state.pieces:
                raise ValueError(f"Không tìm thấy quân được chở: {child_id}.")
            if child_id in collected or child_id == parent_id:
                raise ValueError("Phát hiện quân xuất hiện lặp trong tổ hợp vận chuyển.")
            collected.add(child_id)
            walk(child_id)
        visiting.remove(pid)

    walk(parent_id)
    return collected


def _casualties(state: GameState, target_id: str) -> tuple[str, ...]:
    """Tính danh sách quân bị loại: phương tiện cùng toàn bộ quân con cháu."""
    return (target_id, *sorted(_children(state, target_id)))


def _award_points(state: GameState, winner: Player, points: int) -> None:
    scores = getattr(state, "scores", None)
    if isinstance(scores, dict):
        key: Any = winner if winner in scores or not scores else winner.value
        if key not in scores and scores and all(isinstance(k, str) for k in scores):
            key = winner.value
        scores[key] = scores.get(key, 0) + points


def _mark_ended(state: GameState, winner: Player | None) -> None:
    status = getattr(state, "game_status", None)
    enum_cls = type(status)
    if not issubclass(enum_cls, Enum):
        return
    if winner is None:
        if "DRAW" in enum_cls.__members__:
            state.game_status = enum_cls["DRAW"]
        return
    for name in ("RED_WINS", "BLUE_WINS", "RED_WIN", "BLUE_WIN", "FINISHED", "GAME_OVER"):
        if name.startswith("RED") and winner != Player.RED:
            continue
        if name.startswith("BLUE") and winner != Player.BLUE:
            continue
        if name in enum_cls.__members__:
            state.game_status = enum_cls[name]
            break


def _promote_last_survivor(state: GameState, events: list[EngineEvent]) -> None:
    """Q10 Anh hùng:
    - Quân bảo vệ cuối cùng (ngoại trừ Sở chỉ huy) được phong Anh hùng.
    - Khi chỉ còn đúng 1 Sở chỉ huy và Tư lệnh:
      + Nếu Tư lệnh KHÔNG trú trong Sở chỉ huy đó -> phong Anh hùng ngay lập tức.
      + Nếu Tư lệnh ĐANG trú trong Sở chỉ huy đó -> giữ nguyên chưa phong;
        ngay khi Tư lệnh rời khỏi Sở chỉ huy thì phong Anh hùng ngay lập tức.
    - Nếu còn 2 Sở chỉ huy thì không phong Anh hùng cho Sở chỉ huy nào (DEC-015).
    """
    for player in (Player.RED, Player.BLUE):
        alive = [p for p in state.pieces.values() if p.owner == player]
        non_cmd_non_hq = [p for p in alive if p.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)]
        hq_pieces = [p for p in alive if p.piece_type == PieceType.HEADQUARTERS]
        cmd = next((p for p in alive if p.piece_type == PieceType.COMMANDER), None)

        if len(non_cmd_non_hq) == 1 and not non_cmd_non_hq[0].is_heroic:
            hero = non_cmd_non_hq[0]
            hero.is_heroic = True
            events.append(EngineEvent(
                EngineEventType.HERO_PROMOTED, hero.id,
                "Tự phong Anh hùng cho quân bảo vệ cuối cùng (ngoại trừ Sở chỉ huy)."
            ))
        elif len(non_cmd_non_hq) == 0 and len(hq_pieces) == 1 and not hq_pieces[0].is_heroic:
            sole_hq = hq_pieces[0]
            if cmd is not None and cmd.carried_by == sole_hq.id:
                continue  # Phong trễ: chờ Tư lệnh bước ra khỏi Sở chỉ huy
            sole_hq.is_heroic = True
            events.append(EngineEvent(
                EngineEventType.HERO_PROMOTED, sole_hq.id,
                "Tự phong Sở chỉ huy duy nhất thành Bộ binh Anh hùng khi chỉ còn 1 Sở chỉ huy và Tư lệnh."
            ))


def _promote_checkers(state: GameState, attacker_player: Player, events: list[EngineEvent]) -> None:
    """Phong Anh hùng cho quân vừa đặt Tư lệnh đối phương vào thế bị chiếu."""
    defender = _opponent(attacker_player)
    if not rules.is_commander_in_check(state, defender):
        return
    enemy_cmd = next(
        (p for p in state.pieces.values() if p.owner == defender and p.piece_type == PieceType.COMMANDER),
        None,
    )
    if enemy_cmd is None:
        return
    cmd_origin = rules._origin(state, enemy_cmd)
    if cmd_origin is None:
        return
    occ_map = {
        p.position: p
        for p in state.pieces.values()
        if p.carried_by is None and p.position is not None
    }
    for p in list(state.pieces.values()):
        if p.owner != attacker_player or p.piece_type == PieceType.COMMANDER or p.is_heroic:
            continue
        if rules._piece_threatens_square(state, p, cmd_origin, occ_map):
            p.is_heroic = True
            events.append(EngineEvent(
                EngineEventType.HERO_PROMOTED, p.id,
                "Phong Anh hùng cho quân chiếu Tư lệnh đối phương."
            ))


def _leave_cargo_behind(state: GameState, carrier: Any, origin: tuple[int, int]) -> None:
    """Giải phóng quân đang cõng ở lại vị trí xuất phát `origin` khi carrier tách lẻ."""
    direct_ids = list(carrier.cargo)
    carrier.cargo.clear()
    if not direct_ids:
        return
    if len(direct_ids) == 1:
        root_cid = direct_ids[0]
        other_cids: list[str] = []
    else:
        p1 = state.pieces[direct_ids[0]]
        p2 = state.pieces[direct_ids[1]]
        p1_can_carry_p2 = (
            rules.can_carry(p1, p2).valid
            and (p1.piece_type != PieceType.ENGINEER or origin[0] in (5, 6))
        )
        if p1_can_carry_p2:
            root_cid, other_cids = p1.id, [p2.id]
        else:
            root_cid, other_cids = p2.id, [p1.id]

    root_survivor = state.pieces[root_cid]
    root_survivor.carried_by = None
    root_survivor.position = origin
    for ocid in other_cids:
        other_p = state.pieces[ocid]
        other_p.carried_by = root_survivor.id
        other_p.position = None
        if other_p.id not in root_survivor.cargo:
            root_survivor.cargo.append(other_p.id)


def _execute_atomic_transition(
    state: GameState,
    action: AtomicAction,
    *,
    run_check_promotions: bool = True,
) -> tuple[GameState, list[EngineEvent], bool, bool, rules.RuleResult | None]:
    """Thực thi biến đổi vật lý trên bản sao trạng thái và kiểm tra an toàn Tư lệnh.

    Trả về: (next_state, events, commander_killed, is_in_aa, safety_rejection_or_None).
    """
    actor = state.pieces[action.piece_id]
    player = state.current_player
    enemy = _opponent(player)
    start_origin = rules._origin(state, actor)
    assert start_origin is not None

    had_own_cmd = any(
        p.owner == player and p.piece_type == PieceType.COMMANDER
        for p in state.pieces.values()
    )

    is_capture_like = action.action_type in (ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD)
    target = (
        state.get_piece_at(action.end)
        if action.action_type in (ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD, ActionType.BOARD, ActionType.PICKUP)
        else None
    )

    is_in_aa = False
    if actor.piece_type == PieceType.AIRCRAFT and not actor.is_heroic:
        danger = rules.aa_danger_positions(state, enemy)
        flight_path = (start_origin, *rules.path_points(start_origin, action.end), action.end)
        is_in_aa = any(pos in danger for pos in flight_path)

    next_state = deepcopy(state)
    events: list[EngineEvent] = []
    commander_killed = False

    # 1. Xử lý tiêu diệt mục tiêu
    if is_capture_like and target is not None:
        if target.piece_type == PieceType.HEADQUARTERS:
            hq_pos = target.position
            next_hq = next_state.pieces[target.id]
            for cid in list(next_hq.cargo):
                if cid in next_state.pieces:
                    sheltered = next_state.pieces[cid]
                    sheltered.carried_by = None
                    sheltered.position = hq_pos
            pts = PIECE_POINTS[PieceType.HEADQUARTERS] + (10 if target.is_heroic else 0)
            del next_state.pieces[target.id]
            _award_points(next_state, player, pts)
            events.append(EngineEvent(EngineEventType.HQ_DESTROYED, target.id, "Phá hủy Sở chỉ huy."))
            events.append(EngineEvent(EngineEventType.POINTS_AWARDED, detail="Cộng điểm phá Sở chỉ huy.", points=pts))
        else:
            try:
                to_remove = _casualties(state, target.id)
            except ValueError as exc:
                return (deepcopy(state), [], False, False, rules.reject(rules.RuleCode.INVALID_TRANSPORT, str(exc)))
            total = 0
            for pid in to_remove:
                victim = next_state.pieces[pid]
                total += PIECE_POINTS[victim.piece_type] + (10 if victim.is_heroic else 0)
                if victim.piece_type == PieceType.COMMANDER:
                    total += 50
                    commander_killed = True
                kind = EngineEventType.CAPTURED if pid == target.id else EngineEventType.CARGO_LOST
                events.append(EngineEvent(kind, pid, "Bị ăn quân." if pid == target.id else "Bị loại theo phương tiện."))
            for pid in to_remove:
                del next_state.pieces[pid]
            _award_points(next_state, player, total)
            events.append(EngineEvent(EngineEventType.POINTS_AWARDED, detail="Cộng điểm tiêu diệt.", points=total))

    next_actor = next_state.pieces[actor.id]

    # 2. Nếu quân thực hiện vừa tách ra từ phương tiện đang cõng mình
    if next_actor.carried_by is not None:
        old_cid = next_actor.carried_by
        if old_cid in next_state.pieces and actor.id in next_state.pieces[old_cid].cargo:
            next_state.pieces[old_cid].cargo.remove(actor.id)
        next_actor.carried_by = None

    # 3. Rời bỏ cargo ở lại gốc trước khi cất cánh/di chuyển nếu carry_cargo=False hoặc HQ Anh hùng
    if (
        action.action_type in (ActionType.MOVE, ActionType.CAPTURE)
        and (not action.carry_cargo or next_actor.piece_type == PieceType.HEADQUARTERS)
        and next_actor.cargo
    ):
        _leave_cargo_behind(next_state, next_actor, start_origin)

    # 4. Hệ quả phòng không hoặc di chuyển/cõng bình thường
    if is_in_aa:
        aa_victims = _casualties(next_state, next_actor.id)
        aa_total = 0
        for pid in aa_victims:
            v = next_state.pieces[pid]
            aa_total += PIECE_POINTS[v.piece_type] + (10 if v.is_heroic else 0)
            kind = EngineEventType.AIR_EXCHANGE if (pid == next_actor.id and is_capture_like) else (
                EngineEventType.AIR_SHOT_DOWN if pid == next_actor.id else EngineEventType.CARGO_LOST
            )
            events.append(EngineEvent(kind, pid, "Máy bay rơi trong vùng phòng không."))
        for pid in aa_victims:
            del next_state.pieces[pid]
        _award_points(next_state, enemy, aa_total)
        events.append(EngineEvent(EngineEventType.POINTS_AWARDED, detail="Đối phương cộng điểm phòng không.", points=aa_total))
    else:
        if action.action_type == ActionType.BOARD:
            dest_carrier = next_state.pieces[target.id]
            next_actor.position = None
            next_actor.carried_by = dest_carrier.id
            if next_actor.id not in dest_carrier.cargo:
                dest_carrier.cargo.append(next_actor.id)
            events.append(EngineEvent(EngineEventType.MOVED, next_actor.id, f"Lên {dest_carrier.id} tại {action.end}."))
        elif action.action_type == ActionType.PICKUP:
            next_actor.position = action.end
            passenger = next_state.pieces[target.id]
            passenger.position = None
            passenger.carried_by = next_actor.id
            if passenger.id not in next_actor.cargo:
                next_actor.cargo.append(passenger.id)
            events.append(EngineEvent(EngineEventType.MOVED, next_actor.id, f"Đón {passenger.id} tại {action.end}."))
        elif action.action_type in (ActionType.MOVE, ActionType.CAPTURE):
            next_actor.position = action.end
            events.append(EngineEvent(EngineEventType.MOVED, next_actor.id, f"Tới tọa độ {action.end}."))
        else:
            # BOMB / BOMBARD đứng tại chỗ
            next_actor.position = start_origin

    # 5. Tự phong Anh hùng (quân cuối cùng & Sở chỉ huy duy nhất có kiểm tra trễ)
    _promote_last_survivor(next_state, events)

    # 6. Kiểm tra an toàn Tư lệnh phe đi nước (TUYỆT ĐỐI không tự sát / lộ mặt / để bị chiếu)
    if had_own_cmd:
        own_cmd_alive = any(
            p.owner == player and p.piece_type == PieceType.COMMANDER
            for p in next_state.pieces.values()
        )
        if not own_cmd_alive:
            return (
                deepcopy(state), [], False, is_in_aa,
                rules.reject(rules.RuleCode.COMMANDER_IN_CHECK, "Hành động khiến Tư lệnh phe mình bị tiêu diệt."),
            )
        if rules.commanders_face(rules._visible_occupancy(next_state)):
            return (
                deepcopy(state), [], False, is_in_aa,
                rules.reject(rules.RuleCode.COMMANDERS_FACING, "Hành động khiến hai Tư lệnh đối mặt trực tiếp."),
            )
        if rules.is_commander_in_check(next_state, player):
            return (
                deepcopy(state), [], False, is_in_aa,
                rules.reject(rules.RuleCode.COMMANDER_IN_CHECK, "Nước đi để lộ Tư lệnh cho đối phương tấn công/ăn."),
            )

    if run_check_promotions:
        _promote_checkers(next_state, player, events)

    return next_state, events, commander_killed, is_in_aa, None


def preview_action_safety(state: GameState, action: AtomicAction) -> rules.RuleResult:
    """Kiểm tra an toàn Tư lệnh sau mô phỏng (bao gồm AA, tách cargo, phong Anh hùng hậu nước đi)."""
    _, _, _, _, rejection = _execute_atomic_transition(state, action, run_check_promotions=False)
    if rejection is not None:
        return rejection
    return rules.accept()


def _finalize_turn_and_check_end(
    next_state: GameState,
    player_who_moved: Player,
    events: list[EngineEvent],
    verdict: rules.RuleResult,
    *,
    check_terminal: bool = True,
) -> EngineResult:
    """Chuyển lượt sang đối phương và kiểm tra Chiếu hết (CHECKMATE) / Hòa cờ bí (STALEMATE)."""
    next_player = _opponent(player_who_moved)
    next_state.compound_turn = None
    next_state.current_player = next_player
    if hasattr(next_state, "turn_number"):
        next_state.turn_number += 1
    if hasattr(next_state, "action_count"):
        next_state.action_count += 1
    events.append(EngineEvent(EngineEventType.TURN_CHANGED, detail=f"Đến lượt {next_player.value}."))

    if check_terminal:
        enemy_has_cmd = any(
            p.owner == next_player and p.piece_type == PieceType.COMMANDER
            for p in next_state.pieces.values()
        )
        if enemy_has_cmd:
            from .move_generator import has_legal_action
            if not has_legal_action(next_state):
                if rules.is_commander_in_check(next_state, next_player):
                    _award_points(next_state, player_who_moved, 50)
                    next_state._engine_terminal = True
                    next_state._engine_winner = player_who_moved
                    _mark_ended(next_state, player_who_moved)
                    events.append(EngineEvent(
                        EngineEventType.GAME_WON,
                        detail=f"Phe {player_who_moved.value} chiếu hết Tư lệnh đối phương!",
                        points=50,
                    ))
                    return EngineResult(
                        True, next_state, verdict, events,
                        winner=player_who_moved, terminal=True, terminal_reason="CHECKMATE",
                    )
                else:
                    next_state._engine_terminal = True
                    next_state._engine_winner = None
                    _mark_ended(next_state, None)
                    events.append(EngineEvent(
                        EngineEventType.GAME_DRAW,
                        detail=f"Hòa cờ bí (Stalemate): phe {next_player.value} hết nước đi hợp lệ nhưng không bị chiếu.",
                    ))
                    return EngineResult(
                        True, next_state, verdict, events,
                        winner=None, terminal=True, terminal_reason="STALEMATE",
                    )

    return EngineResult(True, next_state, verdict, events)


def apply_turn_command(
    state: GameState,
    command: TurnCommand,
    *,
    check_terminal: bool = True,
) -> EngineResult:
    """Thực thi lệnh kết thúc lượt tổ hợp (END_TURN / CONFIRM_DEPLOYMENT)."""
    if getattr(state, "_engine_terminal", False) or getattr(state.game_status, "value", "ongoing") != "ongoing":
        return _fail(state, rules.RuleCode.GAME_OVER, "Ván đấu đã kết thúc.")
    if command.command_type not in (TurnCommandType.CONFIRM_DEPLOYMENT, TurnCommandType.END_TURN):
        return _fail(state, rules.RuleCode.INVALID_ACTION, "Lệnh điều khiển lượt không hợp lệ.")
    if state.compound_turn is None:
        return _fail(state, rules.RuleCode.INVALID_COMPOUND, "Không có lượt ghép tổ hợp nào đang diễn ra.")

    next_state = deepcopy(state)
    player = next_state.current_player
    events: list[EngineEvent] = []
    return _finalize_turn_and_check_end(next_state, player, events, rules.accept(), check_terminal=check_terminal)


def apply_action(
    state: GameState,
    action: AtomicAction | TurnCommand,
    *,
    check_terminal: bool = True,
) -> EngineResult:
    """Kiểm tra và áp dụng hành động đơn hoặc lệnh kết thúc lượt ghép."""
    if isinstance(action, TurnCommand):
        return apply_turn_command(state, action, check_terminal=check_terminal)

    if getattr(state, "_engine_terminal", False) or getattr(state.game_status, "value", "ongoing") != "ongoing":
        return _fail(state, rules.RuleCode.GAME_OVER, "Ván đấu đã kết thúc.")

    verdict = rules.validate_structural_action(state, action)
    if not verdict.valid:
        return EngineResult(False, deepcopy(state), verdict)

    next_state, events, commander_killed, _, safety_rej = _execute_atomic_transition(
        state, action, run_check_promotions=True
    )
    if safety_rej is not None:
        return EngineResult(False, deepcopy(state), safety_rej)

    player = state.current_player
    actor_before = state.pieces[action.piece_id]
    start_origin = rules._origin(state, actor_before)
    assert start_origin is not None

    # Tình huống ngoại lệ trên thế cờ thử nghiệm: Tư lệnh đối phương bị bắt trực tiếp
    if commander_killed:
        next_state.compound_turn = None
        next_state._engine_terminal = True
        next_state._engine_winner = player
        _mark_ended(next_state, player)
        events.append(EngineEvent(EngineEventType.GAME_WON, detail=f"Phe {player.value} tiêu diệt Tư lệnh."))
        return EngineResult(
            True, next_state, verdict, events,
            winner=player, terminal=True, terminal_reason="COMMANDER_CAPTURED",
        )

    # Cập nhật trạng thái lượt ghép tổ hợp (Compound Turn)
    next_ct: CompoundTurnState | None = None
    if action.action_type in (ActionType.BOARD, ActionType.PICKUP):
        next_ct = None
    elif state.compound_turn is not None:
        ct = deepcopy(state.compound_turn)
        ct.actions_used += 1
        ct.acted_piece_ids.add(action.piece_id)
        root_at_origin = next_state.get_piece_at(ct.origin)
        if root_at_origin is not None and root_at_origin.owner == player:
            stack_ids = {root_at_origin.id, *rules.all_carried_ids(next_state, root_at_origin.id)}
            unacted = [pid for pid in stack_ids if pid not in ct.acted_piece_ids]
            if ct.actions_used < 3 and len(unacted) > 0:
                ct.root_transport_id = root_at_origin.id
                next_ct = ct
    else:
        old_root = rules._root_piece(state, actor_before)
        # Case 1: Quân được chở triển khai rời khỏi phương tiện gốc (không phải Sở chỉ huy)
        if (
            actor_before.carried_by is not None
            and old_root is not None
            and old_root.piece_type != PieceType.HEADQUARTERS
            and old_root.id in next_state.pieces
            and next_state.pieces[old_root.id].position == start_origin
        ):
            next_ct = CompoundTurnState(
                root_transport_id=old_root.id,
                origin=start_origin,
                actions_used=1,
                acted_piece_ids={actor_before.id},
            )
        # Case 2: Phương tiện gốc di chuyển nhưng để lại quân cõng tại vị trí xuất phát (carry_cargo=False)
        elif (
            actor_before.carried_by is None
            and actor_before.piece_type != PieceType.HEADQUARTERS
            and actor_before.cargo
            and action.action_type in (ActionType.MOVE, ActionType.CAPTURE)
            and not action.carry_cargo
        ):
            new_root = next_state.get_piece_at(start_origin)
            if new_root is not None and new_root.owner == player:
                next_ct = CompoundTurnState(
                    root_transport_id=new_root.id,
                    origin=start_origin,
                    actions_used=1,
                    acted_piece_ids={actor_before.id},
                )
        # Case 3: Phương tiện gốc đứng tại chỗ bắn pháo/thả bom (BOMB / BOMBARD) và vẫn còn sống với cargo
        elif (
            actor_before.carried_by is None
            and actor_before.piece_type != PieceType.HEADQUARTERS
            and actor_before.cargo
            and action.action_type in (ActionType.BOMB, ActionType.BOMBARD)
            and actor_before.id in next_state.pieces
            and next_state.pieces[actor_before.id].cargo
        ):
            next_ct = CompoundTurnState(
                root_transport_id=actor_before.id,
                origin=start_origin,
                actions_used=1,
                acted_piece_ids={actor_before.id},
            )

    if next_ct is not None:
        next_state.compound_turn = next_ct
        if hasattr(next_state, "action_count"):
            next_state.action_count += 1
        return EngineResult(True, next_state, verdict, events)

    return _finalize_turn_and_check_end(next_state, player, events, verdict, check_terminal=check_terminal)


def preview_action(state: GameState, action: AtomicAction | TurnCommand) -> EngineResult:
    """Mô phỏng một hành động mà không thay đổi trạng thái gốc (tính cả Chiếu hết/Hòa bí)."""
    return apply_action(state, action, check_terminal=False)


__all__ = [
    "PIECE_POINTS", "EngineEventType", "EngineEvent", "EngineResult",
    "apply_action", "apply_turn_command", "preview_action", "preview_action_safety",
]
