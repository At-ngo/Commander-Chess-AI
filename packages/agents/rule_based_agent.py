# packages/agents/rule_based_agent.py
"""Level 2 Agent — Rule-based Agent cho Cờ Tư Lệnh.

Thứ tự ưu tiên luật minh bạch (Laws 1 -> 6):
1. WIN_IMMEDIATE       (priority 1): Nước thắng ngay (bắt Tư lệnh / Chiếu hết hợp lệ từ Game Engine).
2. DEFEND_COMMANDER    (priority 2): Bảo vệ Tư lệnh khi đang bị chiếu hoặc Sở chỉ huy che chở bị đe dọa.
3. CHECK_COMMANDER     (priority 3): Chiếu Tư lệnh đối phương (chỉ kích hoạt khi `enable_check_rule=True`).
4. CAPTURE_HIGH_VALUE  (priority 4): Ăn/pháo kích/ném bom quân có giá trị cao theo bảng `PIECE_POINTS`.
5. ESCAPE_THREAT       (priority 5): Di tản quân giá trị cao đang bị đe dọa tới vị trí an toàn.
6. FALLBACK            (priority 6): Chọn ngẫu nhiên (hoặc tất định theo cấu hình) trong các nước hợp lệ.

Tác tử KHÔNG tự suy diễn luật hợp lệ và KHÔNG sửa đổi GameState gốc;
mọi xác thực hành động và chuyển trạng thái mô phỏng đều gọi qua Game Engine.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from commander_game_engine import rules
from commander_game_engine.actions import (
    ActionType,
    AtomicAction,
    TurnCommand,
    TurnCommandType,
)
from commander_game_engine.engine import PIECE_POINTS, preview_action
from commander_game_engine.game_state import GameState, Piece, PieceType, Player
from commander_game_engine.move_generator import has_legal_action

from .base import AgentAction, BaseAgent


RULE_PRIORITIES: dict[str, int] = {
    "WIN_IMMEDIATE": 1,
    "DEFEND_COMMANDER": 2,
    "CHECK_COMMANDER": 3,
    "CAPTURE_HIGH_VALUE": 4,
    "ESCAPE_THREAT": 5,
    "FALLBACK": 6,
}

# Hệ số thưởng nhỏ nội bộ trong tie-break chiến thuật (không vượt qua giá trị quân)
_CHECK_CAP_TYPES = frozenset({ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD})


def format_action_str(action: AgentAction) -> str:
    """Chuyển hành động sang chuỗi chuẩn phục vụ log, tie-break tất định và replay."""
    if isinstance(action, TurnCommand):
        return f"CMD:{action.command_type.value}"
    parts = [f"{action.action_type.value.upper()}:{action.piece_id}"]
    if action.start is not None:
        parts.append(f"@({action.start[0]},{action.start[1]})")
    if action.end is not None:
        parts.append(f"->({action.end[0]},{action.end[1]})")
    if action.target_piece_id is not None:
        parts.append(f"#target={action.target_piece_id}")
    if action.carrier_id is not None:
        parts.append(f"#carrier={action.carrier_id}")
    if action.passenger_id is not None:
        parts.append(f"#passenger={action.passenger_id}")
    if not action.carry_cargo:
        parts.append(";carry=0")
    return "".join(parts)


def _piece_effective_value(state: GameState, piece: Piece) -> int:
    """Giá trị bản thân quân cờ cộng thêm phần thưởng Anh hùng và quân đang cõng (nếu có)."""
    base = PIECE_POINTS[piece.piece_type] + (10 if piece.is_heroic else 0)
    if piece.cargo:
        for cid in rules.all_carried_ids(state, piece.id):
            c = state.pieces.get(cid)
            if c is not None:
                base += PIECE_POINTS[c.piece_type] + (10 if c.is_heroic else 0)
    return base


def _score_value(scores: dict[Any, int], player: Player) -> int:
    if player in scores:
        return int(scores[player])
    return int(scores.get(player.value, 0))


def _collinear_or_near(a: tuple[int, int] | None, b: tuple[int, int] | None, max_range: int = 5) -> bool:
    """Kiểm tra nhanh khả năng tương tác dọc/ngang/chéo hoặc tầm gần."""
    if a is None or b is None:
        return True
    dy, dx = abs(a[0] - b[0]), abs(a[1] - b[1])
    if dy == 0 or dx == 0 or dy == dx:
        return True
    return max(dy, dx) <= max_range


class RuleBasedAgent(BaseAgent):
    """Tác tử Level 2 ra quyết định theo thứ tự ưu tiên luật Ruleset A / Ruleset B."""

    UNSAFE_CHECK_CRITERION = "attacker_lost_or_attacked_after_with_negative_gain"

    def __init__(
        self,
        name: str = "RuleBasedAgent",
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        cfg = deepcopy(config) if config else {}
        super().__init__(name=name, seed=seed, config=cfg)

        self.enable_check_rule = bool(
            cfg.get("enable_check_rule", cfg.get("prioritize_check", True))
        )
        default_ruleset = "Ruleset_B" if self.enable_check_rule else "Ruleset_A"
        self.ruleset_name = str(cfg.get("ruleset_name", default_ruleset))
        self.ruleset_version = str(cfg.get("ruleset_version", "1.0.0"))
        self.tie_breaking = str(cfg.get("tie_breaking", "random")).strip().lower()
        if self.tie_breaking not in ("random", "deterministic", "first"):
            raise ValueError(
                f"tie_breaking không hợp lệ '{self.tie_breaking}'. "
                "Chỉ hỗ trợ: 'random', 'deterministic', 'first'."
            )
        self.safe_check_preference = bool(cfg.get("safe_check_preference", True))
        self.safe_capture_preference = bool(cfg.get("safe_capture_preference", True))
        self.avoid_losing_captures = bool(cfg.get("avoid_losing_captures", True))
        self.high_value_threshold = int(cfg.get("high_value_threshold", 20))
        self.agent_config_id = str(cfg.get("agent_config_id", self.ruleset_name))

    @property
    def algorithm(self) -> str:
        return "rule_based"

    @property
    def version(self) -> str:
        return self.ruleset_version

    def _select_among_tied(
        self,
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]],
    ) -> tuple[AgentAction, dict[str, Any]]:
        """Chọn một ứng viên đạt khóa xếp hạng cao nhất theo chính sách tie-breaking."""
        best_rank = max(rank for rank, _ in candidates)
        best_items = [info for rank, info in candidates if rank == best_rank]
        if len(best_items) == 1:
            chosen = best_items[0]
        elif self.tie_breaking == "random":
            chosen = self.rng.choice(best_items)
        elif self.tie_breaking == "deterministic":
            best_items.sort(key=lambda item: item["action_str"])
            chosen = best_items[0]
        else:  # "first"
            chosen = best_items[0]
        return chosen["action"], chosen

    def _choose_action(
        self,
        state: GameState,
        legal_actions: list[AgentAction],
        **kwargs: Any,
    ) -> tuple[AgentAction, dict[str, Any]]:
        player = state.current_player
        enemy = Player.BLUE if player == Player.RED else Player.RED

        own_cmd = next(
            (p for p in state.pieces.values() if p.owner == player and p.piece_type == PieceType.COMMANDER),
            None,
        )
        enemy_cmd = next(
            (p for p in state.pieces.values() if p.owner == enemy and p.piece_type == PieceType.COMMANDER),
            None,
        )
        enemy_cmd_origin = rules._origin(state, enemy_cmd) if enemy_cmd is not None else None

        own_in_check = rules.is_commander_in_check(state, player)
        own_hq_sheltering: Piece | None = None
        hq_under_threat = False
        if own_cmd is not None and own_cmd.carried_by is not None:
            carrier = state.pieces.get(own_cmd.carried_by)
            if carrier is not None and carrier.piece_type == PieceType.HEADQUARTERS:
                own_hq_sheltering = carrier
                if carrier.position is not None:
                    hq_under_threat = rules.is_square_attacked_by_enemy(state, carrier.position, enemy)

        urgent_cmd_defense = own_in_check or hq_under_threat

        # Tiền tính tập quân mình giá trị cao đang bị địch đe dọa (cho Luật 5)
        occ_map: dict[tuple[int, int], Piece] = {
            p.position: p
            for p in state.pieces.values()
            if p.carried_by is None and p.position is not None
        }
        enemy_pieces = [p for p in state.pieces.values() if p.owner == enemy]
        threatened_allies: dict[str, int] = {}
        for piece in state.pieces.values():
            if piece.owner != player or piece.carried_by is not None or piece.position is None:
                continue
            if piece.piece_type == PieceType.COMMANDER:
                continue
            eff_val = _piece_effective_value(state, piece)
            if eff_val < self.high_value_threshold and not piece.is_heroic:
                continue
            if any(rules._piece_threatens_square(state, ep, piece.position, occ_map) for ep in enemy_pieces):
                threatened_allies[piece.id] = eff_val

        # Ngưỡng quân sắp hết nước -> có thể kích hoạt phong Anh hùng cuối cùng
        own_non_cmd_count = sum(
            1 for p in state.pieces.values()
            if p.owner == player and p.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)
        )
        enemy_non_cmd_count = sum(
            1 for p in state.pieces.values()
            if p.owner == enemy and p.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)
        )
        few_pieces_edge = own_non_cmd_count <= 2 or enemy_non_cmd_count <= 2

        law1_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        law2_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        law3_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        law4_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        law5_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        all_action_infos: list[dict[str, Any]] = []
        check_opportunities: list[dict[str, Any]] = []
        risky_captures_skipped = 0

        for action in legal_actions:
            astr = format_action_str(action)

            if isinstance(action, TurnCommand):
                res = preview_action(state, action)
                if not res.accepted:
                    continue
                next_state = res.state
                # Đảm bảo không kết thúc lượt khi Tư lệnh mình bất hợp lệ
                if rules.is_commander_in_check(next_state, player):
                    continue
                gives_check = rules.is_commander_in_check(next_state, enemy)
                is_checkmate = gives_check and (not has_legal_action(next_state))
                info = {
                    "action": action,
                    "action_str": astr,
                    "action_type": action.command_type.value,
                    "gives_check": gives_check,
                    "is_checkmate": is_checkmate,
                    "unsafe_check": False,
                    "attacker_attacked_after": False,
                    "own_pts_gained": 0,
                    "own_pts_lost": 0,
                    "net_gain": 0,
                    "net_exchange": 0,
                    "threat_val_saved": 0,
                }
                all_action_infos.append(info)
                if is_checkmate:
                    law1_candidates.append(((1, 0), info))
                elif gives_check:
                    check_opportunities.append(info)
                    if self.enable_check_rule:
                        law3_candidates.append(((1, 0, 0), info))
                continue

            actor = state.pieces.get(action.piece_id)
            if actor is None:
                continue

            # Bộ lọc nhanh: những nước MOVE/BOARD/PICKUP thuần túy không liên quan chiến thuật/chiếu/đe dọa
            # không cần deep copy + preview_action để tối ưu độ trễ thực thi.
            needs_preview = (
                urgent_cmd_defense
                or state.compound_turn is not None
                or action.action_type in _CHECK_CAP_TYPES
                or action.piece_id in threatened_allies
                or (actor.piece_type == PieceType.AIRCRAFT and not actor.is_heroic)
                or actor.carried_by is not None
                or bool(actor.cargo)
                or few_pieces_edge
                or _collinear_or_near(action.start, enemy_cmd_origin)
                or _collinear_or_near(action.end, enemy_cmd_origin)
            )
            # Bổ sung trường hợp BOARD lên sở chỉ huy bị đe dọa hoặc rời đi
            if own_hq_sheltering is not None and action.target_piece_id == own_hq_sheltering.id:
                needs_preview = True

            if not needs_preview:
                all_action_infos.append(
                    {
                        "action": action,
                        "action_str": astr,
                        "action_type": action.action_type.value,
                        "gives_check": False,
                        "is_checkmate": False,
                        "unsafe_check": False,
                        "attacker_attacked_after": False,
                        "own_pts_gained": 0,
                        "own_pts_lost": 0,
                        "net_gain": 0,
                        "net_exchange": 0,
                        "threat_val_saved": 0,
                    }
                )
                continue

            res = preview_action(state, action)
            if not res.accepted:
                continue
            next_state = res.state

            # Bảo vệ thêm nếu test truyền nước đi giả trong danh sách
            own_cmd_alive = any(
                p.owner == player and p.piece_type == PieceType.COMMANDER
                for p in next_state.pieces.values()
            )
            if not own_cmd_alive or rules.is_commander_in_check(next_state, player):
                continue

            enemy_cmd_alive = any(
                p.owner == enemy and p.piece_type == PieceType.COMMANDER
                for p in next_state.pieces.values()
            )
            own_pts_gained = _score_value(next_state.scores, player) - _score_value(state.scores, player)
            own_pts_lost = _score_value(next_state.scores, enemy) - _score_value(state.scores, enemy)
            net_gain = own_pts_gained - own_pts_lost

            gives_check = False
            is_checkmate = False
            if not enemy_cmd_alive or res.terminal_reason == "COMMANDER_CAPTURED":
                is_checkmate = True
            else:
                gives_check = rules.is_commander_in_check(next_state, enemy)
                if gives_check and next_state.compound_turn is None:
                    # Chỉ gọi has_legal_action (tốn thời gian) trên các nước thực sự đang chiếu
                    is_checkmate = not has_legal_action(next_state)

            actor_after = next_state.pieces.get(action.piece_id)
            attacker_attacked_after = False
            attacker_exposure = 0
            if actor_after is not None and actor_after.carried_by is None and actor_after.position is not None:
                attacker_exposure = _piece_effective_value(next_state, actor_after)
                # Chỉ kiểm tra bị đánh lại nếu hành động có tính chiến thuật (ăn quân / chiếu / phòng thủ / cứu quân)
                if gives_check or net_gain > 0 or urgent_cmd_defense or (action.piece_id in threatened_allies):
                    attacker_attacked_after = rules.is_square_attacked_by_enemy(
                        next_state, actor_after.position, enemy
                    )

            net_exchange = net_gain - (attacker_exposure if attacker_attacked_after else 0)
            unsafe_check = False
            if gives_check:
                # Quân thực hiện chiếu mất ngay bởi phòng không hoặc bị đe dọa ăn lại mà không bù đủ giá trị
                unsafe_check = (actor_after is None) or (
                    attacker_attacked_after and own_pts_gained < attacker_exposure
                )

            info = {
                "action": action,
                "action_str": astr,
                "action_type": action.action_type.value,
                "gives_check": gives_check,
                "is_checkmate": is_checkmate,
                "unsafe_check": unsafe_check,
                "attacker_attacked_after": attacker_attacked_after,
                "own_pts_gained": own_pts_gained,
                "own_pts_lost": own_pts_lost,
                "net_gain": net_gain,
                "net_exchange": net_exchange,
                "threat_val_saved": 0,
            }
            all_action_infos.append(info)

            # Luật 1: Thắng ngay (Bắt Tư lệnh địch hoặc Chiếu hết hợp lệ trên Engine)
            if is_checkmate:
                win_key = (
                    1 if not enemy_cmd_alive else 0,
                    net_gain,
                    1 if not unsafe_check else 0,
                )
                law1_candidates.append((win_key, info))
                continue

            # Luật 2: Bảo vệ Tư lệnh (khi Tư lệnh bị chiếu hoặc Sở chỉ huy che chở đang bị đe dọa)
            if urgent_cmd_defense:
                still_cmd_check = rules.is_commander_in_check(next_state, player)
                still_hq_threat = False
                next_cmd = next(
                    (p for p in next_state.pieces.values() if p.owner == player and p.piece_type == PieceType.COMMANDER),
                    None,
                )
                if next_cmd is not None and next_cmd.carried_by is not None:
                    nc = next_state.pieces.get(next_cmd.carried_by)
                    if nc is not None and nc.piece_type == PieceType.HEADQUARTERS and nc.position is not None:
                        still_hq_threat = rules.is_square_attacked_by_enemy(next_state, nc.position, enemy)

                if not still_cmd_check:
                    resolved_all = not still_hq_threat
                    if own_in_check or resolved_all:
                        def_key = (
                            1 if resolved_all else 0,
                            1 if net_exchange >= 0 else 0,
                            net_exchange,
                            1 if own_pts_gained > 0 else 0,
                            1 if not attacker_attacked_after else 0,
                            1 if (action.action_type == ActionType.BOARD and action.carrier_id is not None) else 0,
                        )
                        law2_candidates.append((def_key, info))

            # Luật 3: Chiếu Tư lệnh đối phương (Ruleset B)
            if gives_check:
                check_opportunities.append(info)
                if self.enable_check_rule:
                    safe_bonus = 1 if (not self.safe_check_preference or not unsafe_check) else 0
                    chk_key = (
                        safe_bonus,
                        1 if net_gain > 0 else 0,
                        net_exchange,
                        net_gain,
                        1 if actor_after is not None else 0,
                    )
                    law3_candidates.append((chk_key, info))

            # Luật 4: Ăn quân có giá trị cao (CAPTURE / BOMB / BOMBARD)
            if action.action_type in _CHECK_CAP_TYPES and net_gain > 0:
                if self.avoid_losing_captures and net_exchange < 0:
                    risky_captures_skipped += 1
                else:
                    safe_cap = (not self.safe_capture_preference) or (not attacker_attacked_after)
                    cap_key = (
                        1 if net_exchange >= 0 else 0,
                        net_gain,
                        1 if safe_cap else 0,
                        net_exchange,
                    )
                    law4_candidates.append((cap_key, info))

            # Luật 5: Chạy quân giá trị cao đang bị đe dọa
            if action.piece_id in threatened_allies and own_pts_lost == 0:
                escaped = False
                if actor_after is not None:
                    if actor_after.carried_by is not None:
                        carrier_after = next_state.pieces.get(actor_after.carried_by)
                        if carrier_after is not None and carrier_after.position is not None:
                            escaped = not rules.is_square_attacked_by_enemy(
                                next_state, carrier_after.position, enemy
                            )
                    elif actor_after.position is not None and actor_after.position != action.start:
                        escaped = not attacker_attacked_after
                if escaped:
                    saved_val = threatened_allies[action.piece_id]
                    info["threat_val_saved"] = saved_val
                    # Thưởng nhẹ nếu giữ được hàng cõng an toàn cùng phương tiện
                    kept_cargo_bonus = 1 if (not actor.cargo or action.carry_cargo) else 0
                    esc_key = (saved_val, kept_cargo_bonus, net_gain)
                    law5_candidates.append((esc_key, info))

        # Tổng hợp danh sách quy tắc thỏa mãn trong cấu hình hiện tại
        tactical_satisfied: list[str] = []
        if law1_candidates:
            tactical_satisfied.append("WIN_IMMEDIATE")
        if law2_candidates:
            tactical_satisfied.append("DEFEND_COMMANDER")
        if law3_candidates:
            tactical_satisfied.append("CHECK_COMMANDER")
        if law4_candidates:
            tactical_satisfied.append("CAPTURE_HIGH_VALUE")
        if law5_candidates:
            tactical_satisfied.append("ESCAPE_THREAT")

        rule_conflicts = list(tactical_satisfied) if len(tactical_satisfied) >= 2 else []

        # Áp dụng thứ tự ưu tiên Luật 1 -> Luật 6
        chosen_rule: str
        chosen_group: list[tuple[tuple[Any, ...], dict[str, Any]]]

        if law1_candidates:
            chosen_rule = "WIN_IMMEDIATE"
            chosen_group = law1_candidates
            chosen_action, chosen_info = self._select_among_tied(chosen_group)
        elif law2_candidates:
            chosen_rule = "DEFEND_COMMANDER"
            chosen_group = law2_candidates
            chosen_action, chosen_info = self._select_among_tied(chosen_group)
        elif law3_candidates:
            chosen_rule = "CHECK_COMMANDER"
            chosen_group = law3_candidates
            chosen_action, chosen_info = self._select_among_tied(chosen_group)
        elif law4_candidates:
            chosen_rule = "CAPTURE_HIGH_VALUE"
            chosen_group = law4_candidates
            chosen_action, chosen_info = self._select_among_tied(chosen_group)
        elif law5_candidates:
            chosen_rule = "ESCAPE_THREAT"
            chosen_group = law5_candidates
            chosen_action, chosen_info = self._select_among_tied(chosen_group)
        else:
            chosen_rule = "FALLBACK"
            fallback_pool = all_action_infos
            if not fallback_pool:
                fallback_pool = [
                    {
                        "action": a,
                        "action_str": format_action_str(a),
                        "action_type": a.command_type.value if isinstance(a, TurnCommand) else a.action_type.value,
                        "gives_check": False,
                        "is_checkmate": False,
                        "unsafe_check": False,
                        "attacker_attacked_after": False,
                        "own_pts_gained": 0,
                        "own_pts_lost": 0,
                        "net_gain": 0,
                        "net_exchange": 0,
                        "threat_val_saved": 0,
                    }
                    for a in legal_actions
                ]
            chosen_group = [((0,), info) for info in fallback_pool]
            if self.tie_breaking == "random":
                chosen_info = self.rng.choice(fallback_pool)
                chosen_action = chosen_info["action"]
            elif self.tie_breaking == "deterministic":
                sorted_pool = sorted(fallback_pool, key=lambda item: item["action_str"])
                chosen_info = sorted_pool[0]
                chosen_action = chosen_info["action"]
            else:
                chosen_info = fallback_pool[0]
                chosen_action = chosen_info["action"]

        candidate_strs = [info["action_str"] for _, info in chosen_group[:12]]
        rule_satisfied = tactical_satisfied if tactical_satisfied else ["FALLBACK"]

        metadata: dict[str, Any] = {
            "agent_config_id": self.agent_config_id,
            "ruleset_name": self.ruleset_name,
            "ruleset_version": self.ruleset_version,
            "enable_check_rule": self.enable_check_rule,
            "tie_breaking": self.tie_breaking,
            "rule_triggered": chosen_rule,
            "rule_priority": RULE_PRIORITIES[chosen_rule],
            "rule_satisfied": rule_satisfied,
            "rule_conflicts": rule_conflicts,
            "has_rule_conflict": bool(rule_conflicts),
            "rule_candidates": candidate_strs,
            "rule_candidate_count": len(chosen_group),
            "fallback_used": chosen_rule == "FALLBACK",
            "is_check_opportunity": len(check_opportunities) > 0,
            "check_opportunity_count": len(check_opportunities),
            "is_check_move": bool(chosen_info["gives_check"]),
            "is_checkmate_move": bool(chosen_info["is_checkmate"]),
            "unsafe_check": bool(chosen_info["unsafe_check"]),
            "unsafe_check_criterion": self.UNSAFE_CHECK_CRITERION,
            "attacker_exposed_after": bool(chosen_info["attacker_attacked_after"]),
            "captured_value": int(chosen_info["net_gain"]),
            "net_exchange": int(chosen_info["net_exchange"]),
            "risky_captures_skipped": risky_captures_skipped,
            "threatened_allies_count": len(threatened_allies),
            "missed_winning_move": bool(law1_candidates and chosen_rule != "WIN_IMMEDIATE"),
            "missed_defensive_move": bool(urgent_cmd_defense and chosen_rule not in ("WIN_IMMEDIATE", "DEFEND_COMMANDER")),
        }
        return chosen_action, metadata


# Bí danh tương thích ngược nếu cấu hình/test tham chiếu `RulesAgent`
RulesAgent = RuleBasedAgent

__all__ = [
    "RULE_PRIORITIES",
    "RuleBasedAgent",
    "RulesAgent",
    "format_action_str",
]

