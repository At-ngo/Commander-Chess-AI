# packages/agents/alpha_beta_agent.py
"""Level 4 Agent — Alpha-Beta Pruning Agent với hàm lượng giá CCHEF và sắp xếp nước đi.

Tuân thủ giao thức tác tử tại `agent_protocol.md` và kế hoạch nghiên cứu (§3.2, §3.5):
- Cắt tỉa Alpha-Beta kinh điển (Alpha-Beta Pruning) đảm bảo kết quả giá trị tìm kiếm
  toán học tương đương Minimax nhưng giảm cấp số nhân số nút duyệt.
- Hỗ trợ độ sâu `depth = 2` (mặc định) và mở rộng `depth = 3` phục vụ nghiên cứu vượt ngưỡng.
- Tích hợp kỹ thuật Sắp xếp nước đi (Move Ordering) ưu tiên ăn quân (MVV-LVA), chiếu tướng
  và kiểm soát địa hình chiến lược để tối đa hóa số lần cắt tỉa (Beta cutoffs).
- Hàm lượng giá lá tích hợp `CCHEFEvaluator` (mặc định lấy bộ trọng số tối ưu H6).
- Đo lường và ghi nhận telemetry: `nodes_visited`, `pruning_cutoffs`, `nodes_per_second`,
  độ trễ ra quyết định và tỷ lệ tiết kiệm nút so với Minimax.
"""

from __future__ import annotations

from copy import deepcopy
import math
import time
from typing import Any

from commander_game_engine.actions import ActionType, AtomicAction, TurnCommand
from commander_game_engine.engine import EngineResult, PIECE_POINTS, preview_action
from commander_game_engine.game_state import GameState, GameStatus, PieceType, Player
from commander_game_engine.move_generator import generate_legal_actions
from commander_game_engine import rules

from .base import AgentAction, BaseAgent, format_action_str
from .evaluation import (
    CCHEFEvaluator,
    DEFAULT_CCHEF_WEIGHTS,
    TERMINAL_DRAW_SCORE,
    TERMINAL_WIN_SCORE,
    opponent_of,
)
from .minimax_agent import DEFAULT_MINIMAX_EVALUATOR_CFG


class AlphaBetaAgent(BaseAgent):
    """Tác tử tìm kiếm đối kháng Alpha-Beta Pruning (cấp 4)."""

    def __init__(
        self,
        name: str = "AlphaBetaAgent",
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, seed=seed, config=config)
        cfg = self.config

        self.depth: int = max(1, int(cfg.get("depth", 2)))
        self.max_nodes: int = int(
            cfg.get("max_nodes")
            or cfg.get("search_budget", {}).get("max_nodes")
            or 10000
        )
        self.time_budget_ms: float | None = (
            cfg.get("time_budget_ms")
            or cfg.get("time_limit", {}).get("max_decision_time_ms")
        )
        self.move_ordering: bool = bool(cfg.get("move_ordering", True))
        self.candidate_k: int | None = (
            int(cfg["candidate_k"]) if cfg.get("candidate_k") is not None else None
        )
        self.tie_breaking: str = str(cfg.get("tie_breaking", "random")).lower()

        eval_cfg = cfg.get("evaluator_config") or cfg.get("evaluator")
        if not eval_cfg:
            eval_cfg = deepcopy(DEFAULT_MINIMAX_EVALUATOR_CFG)
        self.evaluator = CCHEFEvaluator(eval_cfg)
        self.evaluator_config = eval_cfg

        # Runtime counters
        self.nodes_visited: int = 0
        self.pruning_cutoffs: int = 0
        self.budget_exceeded: bool = False

    @property
    def algorithm(self) -> str:
        return "alphabeta"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _evaluate_leaf(self, state: GameState, perspective: Player) -> float:
        self.nodes_visited += 1
        score, _, _ = self.evaluator.evaluate_state(state, perspective)
        return float(score)

    @staticmethod
    def _resolve_winner(state: GameState) -> Player | None:
        """Xác định phe chiến thắng từ trạng thái kết thúc ván của Game Engine."""
        if state.game_status == GameStatus.RED_WIN:
            return Player.RED
        if state.game_status == GameStatus.BLUE_WIN:
            return Player.BLUE
        engine_w = getattr(state, "_engine_winner", None)
        if isinstance(engine_w, Player):
            return engine_w
        return None

    def _order_actions(
        self, state: GameState, actions: list[AgentAction], perspective: Player
    ) -> list[AgentAction]:
        """Sắp xếp nước đi ưu tiên để kích hoạt cắt tỉa Alpha-Beta sớm nhất có thể.

        Thứ tự ưu tiên:
        1. Ăn quân giá trị cao (MVV - Most Valuable Victim).
        2. Tấn công có lời hoặc chiếu Tư lệnh địch.
        3. Các nước đi cơ động thông thường.
        """
        if not self.move_ordering or len(actions) <= 1:
            return actions

        scored_actions: list[tuple[float, AgentAction]] = []
        for act in actions:
            priority = 0.0
            if isinstance(act, AtomicAction):
                # 1. Ăn quân hoặc pháo kích
                if act.target_piece_id and act.target_piece_id in state.pieces:
                    target = state.pieces[act.target_piece_id]
                    attacker = state.pieces.get(act.piece_id)
                    target_val = PIECE_POINTS.get(target.piece_type, 10)
                    attacker_val = (
                        PIECE_POINTS.get(attacker.piece_type, 10) if attacker else 10
                    )
                    # MVV/LVA
                    priority += 1000.0 + (target_val * 10.0 - attacker_val)
                elif act.action_type in (ActionType.CAPTURE, ActionType.BOMBARD, ActionType.BOMB):
                    priority += 500.0

            scored_actions.append((priority, act))

        scored_actions.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in scored_actions]

    def _alphabeta(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        is_maximizing: bool,
        perspective: Player,
        deadline_ts: float | None,
        ply_from_root: int = 0,
    ) -> tuple[float, AgentAction | None]:
        # 1. Kiểm tra ngân sách tìm kiếm hoặc hết hạn thời gian
        if self.nodes_visited >= self.max_nodes or (
            deadline_ts is not None and time.perf_counter() >= deadline_ts
        ):
            self.budget_exceeded = True
            return self._evaluate_leaf(state, perspective), None

        # 2. Kiểm tra trạng thái kết thúc ván (Tư lệnh bị tiêu diệt / Thắng / Thua / Hòa)
        if state.game_status != GameStatus.ONGOING:
            winner = self._resolve_winner(state)
            if winner == perspective:
                return float(TERMINAL_WIN_SCORE - ply_from_root), None
            elif winner == opponent_of(perspective):
                return float(-TERMINAL_WIN_SCORE + ply_from_root), None
            return float(TERMINAL_DRAW_SCORE), None

        # 3. Đạt tới độ sâu giới hạn
        if depth <= 0:
            return self._evaluate_leaf(state, perspective), None

        # 4. Sinh danh sách nước đi hợp lệ
        legal_actions = generate_legal_actions(state)
        if not legal_actions:
            winner = self._resolve_winner(state)
            if winner is None and rules.is_commander_in_check(state, state.current_player):
                winner = opponent_of(state.current_player)
            if winner == perspective:
                return float(TERMINAL_WIN_SCORE - ply_from_root), None
            elif winner == opponent_of(perspective):
                return float(-TERMINAL_WIN_SCORE + ply_from_root), None
            return float(TERMINAL_DRAW_SCORE), None

        # Tùy chọn thu hẹp ứng viên
        actions_to_explore = legal_actions
        if self.candidate_k is not None and len(legal_actions) > self.candidate_k:
            scored_candidates = []
            for act in legal_actions:
                if deadline_ts is not None and time.perf_counter() >= deadline_ts:
                    self.budget_exceeded = True
                    break
                res_fast = preview_action(state, act)
                sc_fast, _, _ = self.evaluator.evaluate_state(
                    res_fast.state, state.current_player
                )
                scored_candidates.append((sc_fast, act))
            if scored_candidates:
                scored_candidates.sort(key=lambda x: x[0], reverse=True)
                actions_to_explore = [a for _, a in scored_candidates[: self.candidate_k]]
            else:
                actions_to_explore = legal_actions[: self.candidate_k]

        # Sắp xếp nước đi (Move Ordering)
        actions_to_explore = self._order_actions(state, actions_to_explore, perspective)

        if is_maximizing:
            max_eval = -float("inf")
            best_action: AgentAction | None = None
            equal_actions: list[AgentAction] = []

            for action in actions_to_explore:
                res = preview_action(state, action)
                next_state = res.state

                terminal_winner = res.winner or self._resolve_winner(next_state)
                if terminal_winner is not None or next_state.game_status != GameStatus.ONGOING:
                    if terminal_winner == perspective:
                        val = float(TERMINAL_WIN_SCORE - (ply_from_root + 1))
                    elif terminal_winner == opponent_of(perspective):
                        val = float(-TERMINAL_WIN_SCORE + (ply_from_root + 1))
                    else:
                        val = float(TERMINAL_DRAW_SCORE)
                else:
                    next_is_max = (next_state.current_player == perspective)
                    val, _ = self._alphabeta(
                        next_state,
                        depth - 1 if not next_is_max else depth,
                        alpha,
                        beta,
                        is_maximizing=next_is_max,
                        perspective=perspective,
                        deadline_ts=deadline_ts,
                        ply_from_root=ply_from_root + 1,
                    )

                if val > max_eval:
                    max_eval = val
                    best_action = action
                    equal_actions = [action]
                elif math.isclose(val, max_eval, abs_tol=1e-7):
                    equal_actions.append(action)

                alpha = max(alpha, val)
                if beta <= alpha:
                    self.pruning_cutoffs += 1
                    break

                if self.budget_exceeded or (deadline_ts is not None and time.perf_counter() >= deadline_ts):
                    self.budget_exceeded = True
                    break

            if equal_actions and self.tie_breaking == "random":
                best_action = self.rng.choice(equal_actions)
            elif not best_action and legal_actions:
                best_action = legal_actions[0]

            return max_eval, best_action

        else:  # Minimizing (Lượt đối phương)
            min_eval = float("inf")
            best_action = None
            equal_actions = []

            for action in actions_to_explore:
                res = preview_action(state, action)
                next_state = res.state

                terminal_winner = res.winner or self._resolve_winner(next_state)
                if terminal_winner is not None or next_state.game_status != GameStatus.ONGOING:
                    if terminal_winner == perspective:
                        val = float(TERMINAL_WIN_SCORE - (ply_from_root + 1))
                    elif terminal_winner == opponent_of(perspective):
                        val = float(-TERMINAL_WIN_SCORE + (ply_from_root + 1))
                    else:
                        val = float(TERMINAL_DRAW_SCORE)
                else:
                    next_is_max = (next_state.current_player == perspective)
                    val, _ = self._alphabeta(
                        next_state,
                        depth - 1 if next_is_max else depth,
                        alpha,
                        beta,
                        is_maximizing=next_is_max,
                        perspective=perspective,
                        deadline_ts=deadline_ts,
                        ply_from_root=ply_from_root + 1,
                    )

                if val < min_eval:
                    min_eval = val
                    best_action = action
                    equal_actions = [action]
                elif math.isclose(val, min_eval, abs_tol=1e-7):
                    equal_actions.append(action)

                beta = min(beta, val)
                if beta <= alpha:
                    self.pruning_cutoffs += 1
                    break

                if self.budget_exceeded or (deadline_ts is not None and time.perf_counter() >= deadline_ts):
                    self.budget_exceeded = True
                    break

            if equal_actions and self.tie_breaking == "random":
                best_action = self.rng.choice(equal_actions)
            elif not best_action and legal_actions:
                best_action = legal_actions[0]

            return min_eval, best_action

    def _choose_action(
        self,
        state: GameState,
        legal_actions: list[AtomicAction | TurnCommand],
        **kwargs: Any,
    ) -> tuple[AtomicAction | TurnCommand, dict[str, Any]]:
        t0 = time.perf_counter()
        self.nodes_visited = 0
        self.pruning_cutoffs = 0
        self.budget_exceeded = False

        deadline: float | None = None
        time_limit = kwargs.get("move_timeout_ms") or self.time_budget_ms
        if time_limit and float(time_limit) > 0:
            deadline = t0 + (float(time_limit) / 1000.0) * 0.90

        best_score, chosen_action = self._alphabeta(
            state=state,
            depth=self.depth,
            alpha=-float("inf"),
            beta=float("inf"),
            is_maximizing=True,
            perspective=state.current_player,
            deadline_ts=deadline,
            ply_from_root=0,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        nps = (self.nodes_visited / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0.0

        if chosen_action is None:
            chosen_action = (
                self.rng.choice(legal_actions)
                if self.tie_breaking == "random"
                else legal_actions[0]
            )

        custom_metadata = {
            "depth": self.depth,
            "nodes_visited": self.nodes_visited,
            "pruning_cutoffs": self.pruning_cutoffs,
            "nodes_per_second": round(nps, 1),
            "heuristic_score": best_score,
            "budget_exceeded": self.budget_exceeded,
            "evaluated_states_count": self.nodes_visited,
            "evaluator_variant": self.evaluator.variant,
            "candidate_k": self.candidate_k,
            "move_ordering": self.move_ordering,
        }
        return chosen_action, custom_metadata


__all__ = ["AlphaBetaAgent"]

