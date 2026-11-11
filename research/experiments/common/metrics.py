"""Tính các chỉ số đánh giá tác tử: Win Rate, Score, thời gian trung bình, p95 và khoảng tin cậy."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Sequence

from .config import DEFAULT_SEED
from .imports import np, pd
from .match_runner import MatchResult
from .statistics import bootstrap_confidence_interval, wilson_confidence_interval
from .tournament import TournamentResult


@dataclass
class AgentMetricsSummary:
    """Bảng tổng hợp chỉ số hiệu năng và thành tích của một tác tử."""

    agent: str
    total_games: int
    completed_games: int
    truncated_games: int
    timeout_games: int
    error_games: int
    wins: int
    draws: int
    losses: int
    win_rate: float
    draw_rate: float
    loss_rate: float
    score_ratio: float
    avg_decision_time_ms: float
    p95_decision_time_ms: float
    max_decision_time_ms: float
    avg_turns: float
    avg_actions: float
    budget_exceeded_moves: int = 0
    avg_nodes_searched: float | None = None
    avg_simulations: float | None = None
    termination_reasons: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "total_games": self.total_games,
            "completed_games": self.completed_games,
            "truncated_games": self.truncated_games,
            "timeout_games": self.timeout_games,
            "error_games": self.error_games,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "draw_rate": self.draw_rate,
            "loss_rate": self.loss_rate,
            "score_ratio": self.score_ratio,
            "avg_decision_time_ms": self.avg_decision_time_ms,
            "p95_decision_time_ms": self.p95_decision_time_ms,
            "max_decision_time_ms": self.max_decision_time_ms,
            "avg_turns": self.avg_turns,
            "avg_actions": self.avg_actions,
            "budget_exceeded_moves": self.budget_exceeded_moves,
            "avg_nodes_searched": self.avg_nodes_searched,
            "avg_simulations": self.avg_simulations,
            "termination_reasons": dict(self.termination_reasons),
        }


def _match_status(m: MatchResult) -> str:
    status = getattr(m, "result_status", None)
    if status in ("completed", "truncated", "timeout", "error"):
        return status
    if m.completed and m.winner in ("red", "blue", "draw"):
        return "completed"
    if m.reason == "MAX_MOVES_EXCEEDED":
        return "truncated"
    if m.reason == "TIMEOUT":
        return "timeout"
    return "error"


def _compute_side_perspective(
    agent_name: str,
    matches: Sequence[MatchResult],
    *,
    side_filter: str | None = None,
) -> AgentMetricsSummary:
    wins = 0
    draws = 0
    losses = 0
    completed_games = 0
    truncated_games = 0
    timeout_games = 0
    error_games = 0
    budget_exceeded = 0

    times_ms: list[float] = []
    nodes: list[int] = []
    sims: list[int] = []
    turns: list[int] = []
    actions: list[int] = []
    reasons: Counter[str] = Counter()

    for m in matches:
        participated_sides: list[str] = []
        if m.red_agent == agent_name and side_filter in (None, "red"):
            participated_sides.append("red")
        if m.blue_agent == agent_name and side_filter in (None, "blue"):
            participated_sides.append("blue")
        if not participated_sides:
            continue

        # Với tự đấu (`random vs random`) khi không lọc màu, ưu tiên góc nhìn Đỏ cho thắng/thua/hòa
        role = participated_sides[0]
        reasons[m.reason] += 1
        turns.append(m.turn_count)
        actions.append(m.action_count)

        for s in participated_sides:
            if s == "red":
                times_ms.extend(m.red_decision_times_ms)
                nodes.extend(m.red_nodes_searched)
                sims.extend(m.red_simulations)
                budget_exceeded += int(getattr(m, "red_budget_exceeded", 0))
            else:
                times_ms.extend(m.blue_decision_times_ms)
                nodes.extend(m.blue_nodes_searched)
                sims.extend(m.blue_simulations)
                budget_exceeded += int(getattr(m, "blue_budget_exceeded", 0))

        status = _match_status(m)
        if status != "completed" or m.winner is None:
            if status == "truncated":
                truncated_games += 1
            elif status == "timeout":
                timeout_games += 1
            else:
                error_games += 1
            continue

        completed_games += 1
        if m.winner == "draw":
            draws += 1
        elif m.winner == role:
            wins += 1
        else:
            losses += 1

    total_games = completed_games + truncated_games + timeout_games + error_games
    denom = completed_games if completed_games > 0 else 1
    win_rate = wins / denom if completed_games > 0 else 0.0
    draw_rate = draws / denom if completed_games > 0 else 0.0
    loss_rate = losses / denom if completed_games > 0 else 0.0
    score_ratio = (wins + 0.5 * draws) / denom if completed_games > 0 else 0.0

    avg_time = float(np.mean(times_ms)) if times_ms else 0.0
    p95_time = float(np.percentile(times_ms, 95)) if times_ms else 0.0
    max_time = float(np.max(times_ms)) if times_ms else 0.0

    return AgentMetricsSummary(
        agent=agent_name,
        total_games=total_games,
        completed_games=completed_games,
        truncated_games=truncated_games,
        timeout_games=timeout_games,
        error_games=error_games,
        wins=wins,
        draws=draws,
        losses=losses,
        win_rate=win_rate,
        draw_rate=draw_rate,
        loss_rate=loss_rate,
        score_ratio=score_ratio,
        avg_decision_time_ms=avg_time,
        p95_decision_time_ms=p95_time,
        max_decision_time_ms=max_time,
        avg_turns=float(np.mean(turns)) if turns else 0.0,
        avg_actions=float(np.mean(actions)) if actions else 0.0,
        budget_exceeded_moves=budget_exceeded,
        avg_nodes_searched=float(np.mean(nodes)) if nodes else None,
        avg_simulations=float(np.mean(sims)) if sims else None,
        termination_reasons=dict(reasons),
    )


def summarize_agent_matches(
    agent_name: str,
    matches: Sequence[MatchResult],
    *,
    side_filter: str | None = None,
) -> AgentMetricsSummary:
    """Tính toán toàn bộ chỉ số của một tác tử từ danh sách kết quả trận đấu."""
    return _compute_side_perspective(agent_name, matches, side_filter=side_filter)


def summarize_red_blue_splits(
    agent_name: str,
    matches: Sequence[MatchResult],
) -> pd.DataFrame:
    """So sánh kết quả của `agent_name` khi cầm quân Đỏ (đi trước) và quân Xanh (đi sau)."""
    rows: list[dict[str, Any]] = []
    for side in ("red", "blue"):
        s = summarize_agent_matches(agent_name, matches, side_filter=side)
        ci_win = wilson_confidence_interval(s.wins, s.completed_games)
        rows.append(
            {
                "agent": agent_name,
                "side": side,
                "total_games": s.total_games,
                "completed_games": s.completed_games,
                "truncated_games": s.truncated_games,
                "wins": s.wins,
                "draws": s.draws,
                "losses": s.losses,
                "win_rate": s.win_rate,
                "draw_rate": s.draw_rate,
                "loss_rate": s.loss_rate,
                "score_ratio": s.score_ratio,
                "win_rate_ci_low": ci_win["lower"],
                "win_rate_ci_high": ci_win["upper"],
                "avg_decision_time_ms": s.avg_decision_time_ms,
                "p95_decision_time_ms": s.p95_decision_time_ms,
            }
        )
    return pd.DataFrame(rows)


def _resolve_role_a(m: MatchResult, agent_a: str, agent_b: str) -> str:
    """Xác định `agent_a` cầm bên 'red' hay 'blue' trong một ván."""
    if m.slot_a_side in ("red", "blue"):
        return m.slot_a_side
    if agent_a != agent_b:
        if m.red_agent == agent_a:
            return "red"
        if m.blue_agent == agent_a:
            return "blue"
    return "red"


def summarize_pair_results(
    matches: Sequence[MatchResult],
    *,
    run_id: str = "",
    agent_a: str | None = None,
    agent_b: str | None = None,
    budget_mode: str | None = None,
    bootstrap_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """Tạo bảng tổng hợp cấp cặp đấu chuẩn `pair_results.csv` kèm Bootstrap/Wilson 95% CI."""
    if not matches:
        return pd.DataFrame(
            columns=[
                "run_id",
                "agent_a",
                "agent_b",
                "budget_mode",
                "total_games",
                "games_completed",
                "truncated_games",
                "timeout_games",
                "error_games",
                "wins_a",
                "draws",
                "losses_a",
                "win_rate_a",
                "draw_rate",
                "loss_rate_a",
                "score_a",
                "score_ci_low",
                "score_ci_high",
                "win_rate_ci_low",
                "win_rate_ci_high",
                "ci_method",
                "bootstrap_resamples",
                "mean_decision_ms_a",
                "p95_decision_ms_a",
                "mean_decision_ms_b",
                "p95_decision_ms_b",
                "avg_turns",
                "avg_decisions",
                "budget_exceeded_a",
                "budget_exceeded_b",
            ]
        )

    first = matches[0]
    label_a = agent_a or first.red_agent
    label_b = agent_b or first.blue_agent
    resolved_mode = budget_mode or getattr(first, "budget_mode", "default")
    resolved_run_id = run_id or getattr(first, "run_id", "") or ""

    wins_a = 0
    draws = 0
    losses_a = 0
    games_completed = 0
    truncated_games = 0
    timeout_games = 0
    error_games = 0

    times_a: list[float] = []
    times_b: list[float] = []
    exceeded_a = 0
    exceeded_b = 0
    turns: list[int] = []
    decisions: list[int] = []

    game_scores: list[float] = []
    seed_clusters: dict[int, list[float]] = defaultdict(list)

    for m in matches:
        role_a = _resolve_role_a(m, label_a, label_b)
        turns.append(m.turn_count)
        decisions.append(getattr(m, "total_decisions", m.action_count))

        if role_a == "red":
            times_a.extend(m.red_decision_times_ms)
            times_b.extend(m.blue_decision_times_ms)
            exceeded_a += int(getattr(m, "red_budget_exceeded", 0))
            exceeded_b += int(getattr(m, "blue_budget_exceeded", 0))
        else:
            times_a.extend(m.blue_decision_times_ms)
            times_b.extend(m.red_decision_times_ms)
            exceeded_a += int(getattr(m, "blue_budget_exceeded", 0))
            exceeded_b += int(getattr(m, "red_budget_exceeded", 0))

        status = _match_status(m)
        if status != "completed" or m.winner is None:
            if status == "truncated":
                truncated_games += 1
            elif status == "timeout":
                timeout_games += 1
            else:
                error_games += 1
            continue

        games_completed += 1
        if m.winner == "draw":
            draws += 1
            g_score = 0.5
        elif m.winner == role_a:
            wins_a += 1
            g_score = 1.0
        else:
            losses_a += 1
            g_score = 0.0

        game_scores.append(g_score)
        if m.seed is not None:
            seed_clusters[m.seed].append(g_score)

    denom = games_completed if games_completed > 0 else 1
    win_rate_a = wins_a / denom if games_completed > 0 else 0.0
    draw_rate = draws / denom if games_completed > 0 else 0.0
    loss_rate_a = losses_a / denom if games_completed > 0 else 0.0
    score_a = (wins_a + 0.5 * draws) / denom if games_completed > 0 else 0.0

    wilson = wilson_confidence_interval(wins_a, games_completed, confidence=confidence)

    # Nếu các cặp ván được ghép đôi theo cùng seed Đỏ/Xanh, ưu tiên Bootstrap theo cluster seed
    paired_clusters = [vals for vals in seed_clusters.values() if len(vals) >= 2]
    if len(paired_clusters) >= 5 and sum(len(v) for v in paired_clusters) == len(game_scores):
        cluster_means = [float(np.mean(vals)) for vals in seed_clusters.values()]
        boot = bootstrap_confidence_interval(
            cluster_means,
            n_resamples=bootstrap_resamples,
            confidence=confidence,
            seed=seed,
        )
        ci_method = "paired_cluster_bootstrap+wilson"
    else:
        boot = bootstrap_confidence_interval(
            game_scores,
            n_resamples=bootstrap_resamples,
            confidence=confidence,
            seed=seed,
        )
        ci_method = "game_bootstrap+wilson"

    row = {
        "run_id": resolved_run_id,
        "agent_a": label_a,
        "agent_b": label_b,
        "budget_mode": resolved_mode,
        "total_games": len(matches),
        "games_completed": games_completed,
        "truncated_games": truncated_games,
        "timeout_games": timeout_games,
        "error_games": error_games,
        "wins_a": wins_a,
        "draws": draws,
        "losses_a": losses_a,
        "win_rate_a": win_rate_a,
        "draw_rate": draw_rate,
        "loss_rate_a": loss_rate_a,
        "score_a": score_a,
        "score_ci_low": float(boot["lower"]),
        "score_ci_high": float(boot["upper"]),
        "win_rate_ci_low": float(wilson["lower"]),
        "win_rate_ci_high": float(wilson["upper"]),
        "ci_method": ci_method,
        "bootstrap_resamples": bootstrap_resamples,
        "mean_decision_ms_a": float(np.mean(times_a)) if times_a else 0.0,
        "p95_decision_ms_a": float(np.percentile(times_a, 95)) if times_a else 0.0,
        "mean_decision_ms_b": float(np.mean(times_b)) if times_b else 0.0,
        "p95_decision_ms_b": float(np.percentile(times_b, 95)) if times_b else 0.0,
        "avg_turns": float(np.mean(turns)) if turns else 0.0,
        "avg_decisions": float(np.mean(decisions)) if decisions else 0.0,
        "budget_exceeded_a": exceeded_a,
        "budget_exceeded_b": exceeded_b,
    }
    return pd.DataFrame([row])


def summarize_tournament(tournament: TournamentResult) -> pd.DataFrame:
    """Tổng hợp bảng xếp hạng và chỉ số của tất cả tác tử trong giải đấu."""
    rows = [
        _compute_side_perspective(name, tournament.matches).to_dict()
        for name in tournament.agent_names
    ]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(
            by=["score_ratio", "win_rate", "avg_decision_time_ms"],
            ascending=[False, False, True],
        ).reset_index(drop=True)
    return df


def build_matchup_matrix(
    tournament: TournamentResult,
    *,
    metric: str = "score_ratio",
) -> pd.DataFrame:
    """Tạo ma trận đối đầu NxN giữa các tác tử theo `score_ratio` hoặc `win_rate`."""
    names = tournament.agent_names
    matrix = pd.DataFrame(np.nan, index=names, columns=names, dtype=float)

    for (a_name, b_name), matches in tournament.pair_matches.items():
        summary_a = _compute_side_perspective(a_name, matches)
        summary_b = _compute_side_perspective(b_name, matches)
        val_a = getattr(summary_a, metric)
        val_b = getattr(summary_b, metric)
        matrix.loc[a_name, b_name] = float(val_a)
        matrix.loc[b_name, a_name] = float(val_b)

    return matrix


__all__ = [
    "AgentMetricsSummary",
    "build_matchup_matrix",
    "summarize_agent_matches",
    "summarize_pair_results",
    "summarize_red_blue_splits",
    "summarize_tournament",
]
