"""Chạy một ván đấu đầy đủ giữa hai tác tử AI qua Game Engine chính thức."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import time
from typing import Any

from .config import DEFAULT_SEED
from .imports import (
    AtomicAction,
    BaseAgent,
    GameState,
    GameStatus,
    Player,
    TurnCommand,
    apply_action,
    create_initial_state,
    generate_legal_actions,
)
from agents.base import format_action_str


def compute_state_hash(state: GameState) -> str:
    """Tính mã băm tất định rút gọn của GameState để định danh thế cờ trong `moves.csv`."""
    piece_tokens = tuple(
        sorted(
            (
                p.id,
                p.piece_type.value,
                p.owner.value,
                p.position[0] if p.position is not None else -1,
                p.position[1] if p.position is not None else -1,
                p.carried_by or "",
                tuple(p.cargo),
                int(p.is_heroic),
            )
            for p in state.pieces.values()
        )
    )
    ct = state.compound_turn
    ct_token = (
        (ct.root_transport_id, ct.origin, ct.actions_used, tuple(sorted(ct.acted_piece_ids)))
        if ct is not None
        else None
    )
    status_val = getattr(state.game_status, "value", str(state.game_status))
    payload = repr((state.current_player.value, status_val, ct_token, piece_tokens)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


@dataclass
class MoveRecord:
    """Thông tin chi tiết một lần ra quyết định trong biên bản ván đấu."""

    step_index: int
    turn_number: int
    player: str
    action_type: str
    piece_id: str | None
    start: tuple[int, int] | None
    end: tuple[int, int] | None
    target_piece_id: str | None
    carry_cargo: bool | None
    decision_time_ms: float
    events: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    agent_name: str = ""
    agent_config_id: str = ""
    state_hash: str = ""
    legal_action_count: int = 0
    selected_action: str = ""
    rule_triggered: str | None = None
    heuristic_score: float | None = None
    heuristic_components: dict[str, float] | None = None
    nodes_visited: int | None = None
    simulations: int | None = None
    valid_action: bool = True
    over_budget: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MatchResult:
    """Kết quả đầy đủ của một ván đấu giữa hai tác tử."""

    match_id: str
    red_agent: str
    blue_agent: str
    seed: int | None
    winner: str | None  # "red" | "blue" | "draw" | None (chưa hoàn tất / truncated / timeout / error)
    reason: str         # CHECKMATE | STALEMATE | COMMANDER_CAPTURED | MAX_MOVES_EXCEEDED | TIMEOUT | RULE_VIOLATION
    completed: bool
    turn_count: int
    action_count: int
    final_scores: dict[str, int]
    duration_ms: float
    red_decision_times_ms: list[float] = field(default_factory=list)
    blue_decision_times_ms: list[float] = field(default_factory=list)
    red_nodes_searched: list[int] = field(default_factory=list)
    blue_nodes_searched: list[int] = field(default_factory=list)
    red_simulations: list[int] = field(default_factory=list)
    blue_simulations: list[int] = field(default_factory=list)
    error: str | None = None
    error_side: str | None = None
    moves: list[MoveRecord] = field(default_factory=list)
    run_id: str | None = None
    budget_mode: str = "default"
    red_config_id: str | None = None
    blue_config_id: str | None = None
    result_status: str = "completed"  # "completed" | "truncated" | "timeout" | "error"
    total_decisions: int = 0
    total_atomic_actions: int = 0
    duration_sec: float = 0.0
    red_game_points: float | None = None
    blue_game_points: float | None = None
    red_budget_exceeded: int = 0
    blue_budget_exceeded: int = 0
    slot_a_side: str | None = None
    game_record_path: str | None = None

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "match_id": self.match_id,
            "seed": self.seed,
            "budget_mode": self.budget_mode,
            "red_agent": self.red_agent,
            "blue_agent": self.blue_agent,
            "red_config_id": self.red_config_id,
            "blue_config_id": self.blue_config_id,
            "winner": self.winner,
            "result_status": self.result_status,
            "reason": self.reason,
            "completed": self.completed,
            "turn_count": self.turn_count,
            "action_count": self.action_count,
            "total_decisions": self.total_decisions,
            "total_atomic_actions": self.total_atomic_actions,
            "score_red": self.final_scores.get("red", 0),
            "score_blue": self.final_scores.get("blue", 0),
            "red_game_points": self.red_game_points,
            "blue_game_points": self.blue_game_points,
            "duration_ms": self.duration_ms,
            "duration_sec": self.duration_sec,
            "red_budget_exceeded": self.red_budget_exceeded,
            "blue_budget_exceeded": self.blue_budget_exceeded,
            "game_record_path": self.game_record_path,
            "error": self.error,
            "error_side": self.error_side,
        }


def _describe_action(
    action: AtomicAction | TurnCommand,
) -> tuple[str, str | None, tuple[int, int] | None, tuple[int, int] | None, str | None, bool | None]:
    if isinstance(action, TurnCommand):
        return (action.command_type.value, None, None, None, None, None)
    return (
        action.action_type.value,
        action.piece_id,
        action.start,
        action.end,
        action.target_piece_id,
        action.carry_cargo,
    )


def _extract_agent_config_id(agent: BaseAgent, explicit_id: str | None) -> str:
    if explicit_id:
        return explicit_id
    cfg = getattr(agent, "config", None) or {}
    for key in ("agent_config_id", "weight_config_id", "ruleset_name"):
        val = cfg.get(key)
        if val:
            return str(val)
    return getattr(agent, "weight_config_id", None) or getattr(agent, "ruleset_name", None) or agent.name


def run_match(
    agent_red: BaseAgent,
    agent_blue: BaseAgent,
    *,
    seed: int | None = DEFAULT_SEED,
    max_turns: int = 200,
    move_timeout_ms: float | None = None,
    strict_timeout: bool = False,
    draw_on_max_turns: bool = False,
    record_moves: bool = True,
    initial_state: GameState | None = None,
    match_id: str | None = None,
    run_id: str | None = None,
    budget_mode: str = "default",
    red_config_id: str | None = None,
    blue_config_id: str | None = None,
    slot_a_side: str | None = None,
) -> MatchResult:
    """Chạy trọn vẹn một ván Cờ Tư Lệnh giữa hai agent bằng Game Engine chính thức."""
    t_match_start = time.perf_counter()
    state = initial_state.copy() if initial_state is not None else create_initial_state()
    mid = match_id or f"{agent_red.name}_vs_{agent_blue.name}_{int(t_match_start * 1000)}"
    agents = {Player.RED: agent_red, Player.BLUE: agent_blue}
    cfg_ids = {
        Player.RED: _extract_agent_config_id(agent_red, red_config_id),
        Player.BLUE: _extract_agent_config_id(agent_blue, blue_config_id),
    }

    red_times: list[float] = []
    blue_times: list[float] = []
    red_nodes: list[int] = []
    blue_nodes: list[int] = []
    red_sims: list[int] = []
    blue_sims: list[int] = []
    moves: list[MoveRecord] = []

    winner: str | None = None
    reason = "UNKNOWN"
    completed = True
    result_status = "completed"
    error_msg: str | None = None
    error_side: str | None = None
    max_steps = max(max_turns * 6, 50)
    step_idx = 0
    atomic_actions_count = 0
    red_over_budget = 0
    blue_over_budget = 0

    while state.game_status == GameStatus.ONGOING:
        if state.turn_number > max_turns or step_idx >= max_steps:
            reason = "MAX_MOVES_EXCEEDED"
            if draw_on_max_turns:
                winner = "draw"
                completed = True
                result_status = "completed"
            else:
                winner = None
                completed = False
                result_status = "truncated"
            break

        player = state.current_player
        legal_actions = generate_legal_actions(state)
        if not legal_actions:
            reason = "STALEMATE"
            winner = "draw"
            completed = True
            result_status = "completed"
            break

        step_idx += 1
        state_hash = compute_state_hash(state) if record_moves else ""
        t0 = time.perf_counter()
        try:
            decision = agents[player].select_action(state, legal_actions)
        except Exception as exc:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            (red_times if player == Player.RED else blue_times).append(dt_ms)
            completed = False
            result_status = "error"
            error_side = player.value
            winner = None
            reason = "RULE_VIOLATION"
            error_msg = f"Agent error ({player.value}): {exc}"
            if record_moves:
                moves.append(
                    MoveRecord(
                        step_index=step_idx,
                        turn_number=state.turn_number,
                        player=player.value,
                        action_type="error",
                        piece_id=None,
                        start=None,
                        end=None,
                        target_piece_id=None,
                        carry_cargo=None,
                        decision_time_ms=dt_ms,
                        events=[],
                        metadata={},
                        agent_name=agents[player].name,
                        agent_config_id=cfg_ids[player],
                        state_hash=state_hash,
                        legal_action_count=len(legal_actions),
                        selected_action="",
                        valid_action=False,
                        over_budget=False,
                        error=error_msg,
                    )
                )
            break

        dt_ms = decision.metadata.get("decision_time_ms")
        elapsed_ms = float(dt_ms) if isinstance(dt_ms, (int, float)) else (time.perf_counter() - t0) * 1000.0
        (red_times if player == Player.RED else blue_times).append(elapsed_ms)

        over_budget = (move_timeout_ms is not None) and (elapsed_ms > move_timeout_ms)
        if over_budget:
            if player == Player.RED:
                red_over_budget += 1
            else:
                blue_over_budget += 1

        meta = decision.metadata or {}
        raw_nodes = meta.get("nodes_searched", meta.get("nodes_visited"))
        raw_sims = meta.get("simulations_run", meta.get("simulations"))
        nodes_val = int(raw_nodes) if isinstance(raw_nodes, int) and not isinstance(raw_nodes, bool) else None
        sims_val = int(raw_sims) if isinstance(raw_sims, int) and not isinstance(raw_sims, bool) else None

        if nodes_val is not None:
            (red_nodes if player == Player.RED else blue_nodes).append(nodes_val)
        if sims_val is not None:
            (red_sims if player == Player.RED else blue_sims).append(sims_val)

        if strict_timeout and over_budget:
            completed = False
            result_status = "timeout"
            error_side = player.value
            winner = None
            reason = "TIMEOUT"
            error_msg = f"Move timeout ({elapsed_ms:.2f}ms > {move_timeout_ms}ms)"
            if record_moves:
                atype, pid, start, end, target_id, carry = _describe_action(decision.action)
                moves.append(
                    MoveRecord(
                        step_index=step_idx,
                        turn_number=state.turn_number,
                        player=player.value,
                        action_type=atype,
                        piece_id=pid,
                        start=start,
                        end=end,
                        target_piece_id=target_id,
                        carry_cargo=carry,
                        decision_time_ms=elapsed_ms,
                        events=[],
                        metadata={k: v for k, v in meta.items() if k not in ("agent_name", "algorithm", "version")},
                        agent_name=agents[player].name,
                        agent_config_id=cfg_ids[player],
                        state_hash=state_hash,
                        legal_action_count=len(legal_actions),
                        selected_action=format_action_str(decision.action),
                        rule_triggered=meta.get("rule_triggered"),
                        heuristic_score=meta.get("heuristic_score"),
                        heuristic_components=meta.get("heuristic_components"),
                        nodes_visited=nodes_val,
                        simulations=sims_val,
                        valid_action=True,
                        over_budget=True,
                        error=error_msg,
                    )
                )
            break

        engine_res = apply_action(state, decision.action)
        if not engine_res.accepted:
            completed = False
            result_status = "error"
            error_side = player.value
            winner = None
            reason = "RULE_VIOLATION"
            error_msg = f"Engine rejected action ({player.value}): {engine_res.verdict.reason}"
            if record_moves:
                atype, pid, start, end, target_id, carry = _describe_action(decision.action)
                moves.append(
                    MoveRecord(
                        step_index=step_idx,
                        turn_number=state.turn_number,
                        player=player.value,
                        action_type=atype,
                        piece_id=pid,
                        start=start,
                        end=end,
                        target_piece_id=target_id,
                        carry_cargo=carry,
                        decision_time_ms=elapsed_ms,
                        events=[],
                        metadata={k: v for k, v in meta.items() if k not in ("agent_name", "algorithm", "version")},
                        agent_name=agents[player].name,
                        agent_config_id=cfg_ids[player],
                        state_hash=state_hash,
                        legal_action_count=len(legal_actions),
                        selected_action=format_action_str(decision.action),
                        rule_triggered=meta.get("rule_triggered"),
                        heuristic_score=meta.get("heuristic_score"),
                        heuristic_components=meta.get("heuristic_components"),
                        nodes_visited=nodes_val,
                        simulations=sims_val,
                        valid_action=False,
                        over_budget=over_budget,
                        error=error_msg,
                    )
                )
            break

        if not isinstance(decision.action, TurnCommand):
            atomic_actions_count += 1

        if record_moves:
            atype, pid, start, end, target_id, carry = _describe_action(decision.action)
            moves.append(
                MoveRecord(
                    step_index=step_idx,
                    turn_number=state.turn_number,
                    player=player.value,
                    action_type=atype,
                    piece_id=pid,
                    start=start,
                    end=end,
                    target_piece_id=target_id,
                    carry_cargo=carry,
                    decision_time_ms=elapsed_ms,
                    events=[e.event_type.value for e in engine_res.events],
                    metadata={
                        k: v for k, v in meta.items()
                        if k not in ("agent_name", "algorithm", "version")
                    },
                    agent_name=agents[player].name,
                    agent_config_id=cfg_ids[player],
                    state_hash=state_hash,
                    legal_action_count=len(legal_actions),
                    selected_action=format_action_str(decision.action),
                    rule_triggered=meta.get("rule_triggered"),
                    heuristic_score=meta.get("heuristic_score"),
                    heuristic_components=meta.get("heuristic_components"),
                    nodes_visited=nodes_val,
                    simulations=sims_val,
                    valid_action=True,
                    over_budget=over_budget,
                    error=None,
                )
            )

        state = engine_res.state
        if engine_res.terminal:
            if engine_res.winner == Player.RED:
                winner = "red"
            elif engine_res.winner == Player.BLUE:
                winner = "blue"
            else:
                winner = "draw"
            reason = engine_res.terminal_reason or ("STALEMATE" if winner == "draw" else "CHECKMATE")
            completed = True
            result_status = "completed"
            break

    if result_status == "completed" and winner is None and state.game_status != GameStatus.ONGOING:
        if state.game_status == GameStatus.RED_WIN:
            winner = "red"
            reason = reason if reason != "UNKNOWN" else "CHECKMATE"
        elif state.game_status == GameStatus.BLUE_WIN:
            winner = "blue"
            reason = reason if reason != "UNKNOWN" else "CHECKMATE"
        elif state.game_status == GameStatus.DRAW:
            winner = "draw"
            reason = reason if reason != "UNKNOWN" else "STALEMATE"

    if result_status == "completed" and winner in ("red", "blue", "draw"):
        if winner == "red":
            red_pts, blue_pts = 1.0, 0.0
        elif winner == "blue":
            red_pts, blue_pts = 0.0, 1.0
        else:
            red_pts, blue_pts = 0.5, 0.5
    else:
        red_pts, blue_pts = None, None

    duration_ms = (time.perf_counter() - t_match_start) * 1000.0
    duration_sec = duration_ms / 1000.0
    scores_dict = {
        "red": int(state.scores.get(Player.RED, state.scores.get("red", 0))),
        "blue": int(state.scores.get(Player.BLUE, state.scores.get("blue", 0))),
    }
    return MatchResult(
        match_id=mid,
        red_agent=agent_red.name,
        blue_agent=agent_blue.name,
        seed=seed,
        winner=winner,
        reason=reason,
        completed=completed,
        turn_count=state.turn_number,
        action_count=step_idx,
        final_scores=scores_dict,
        duration_ms=duration_ms,
        red_decision_times_ms=red_times,
        blue_decision_times_ms=blue_times,
        red_nodes_searched=red_nodes,
        blue_nodes_searched=blue_nodes,
        red_simulations=red_sims,
        blue_simulations=blue_sims,
        error=error_msg,
        error_side=error_side,
        moves=moves,
        run_id=run_id,
        budget_mode=budget_mode,
        red_config_id=cfg_ids[Player.RED],
        blue_config_id=cfg_ids[Player.BLUE],
        result_status=result_status,
        total_decisions=step_idx,
        total_atomic_actions=atomic_actions_count,
        duration_sec=duration_sec,
        red_game_points=red_pts,
        blue_game_points=blue_pts,
        red_budget_exceeded=red_over_budget,
        blue_budget_exceeded=blue_over_budget,
        slot_a_side=slot_a_side,
    )


__all__ = [
    "MatchResult",
    "MoveRecord",
    "compute_state_hash",
    "format_action_str",
    "run_match",
]
