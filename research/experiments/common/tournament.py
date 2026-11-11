"""Tổ chức giải đấu đối đầu trực tiếp và Round-robin có cân bằng Đỏ/Xanh và đa tiến trình."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass, field
import multiprocessing
import os
from typing import Any, Sequence
import warnings

from .agent_factory import (
    create_agent,
    is_custom_registered,
    normalize_agent_name,
    resolve_agent_config_id,
)
from .config import DEFAULT_SEED
from .imports import EXPERIMENTS_DIR, PACKAGES_DIR, tqdm
from .match_runner import MatchResult, run_match


@dataclass
class TournamentResult:
    """Tổng hợp kết quả các trận trong giải đấu."""

    agent_names: list[str]
    games_per_pair: int
    side_balance: bool
    base_seed: int
    matches: list[MatchResult] = field(default_factory=list)
    pair_matches: dict[tuple[str, str], list[MatchResult]] = field(default_factory=dict)


def _select_game_seed(idx: int, *, side_balance: bool, base_seed: int, seeds: Sequence[int] | None) -> int:
    """Xác định seed cho ván `idx`; khi `side_balance=True`, mỗi cặp Đỏ/Xanh chia sẻ cùng một seed."""
    slot_idx = idx // 2 if side_balance else idx
    if seeds:
        pool = list(seeds)
        return int(pool[slot_idx % len(pool)]) + (slot_idx // len(pool)) * 1000
    return int(base_seed) + slot_idx


def _run_head_to_head_worker(task: dict[str, Any]) -> tuple[int, MatchResult]:
    """Hàm worker top-level phục vụ chạy song song bằng ProcessPoolExecutor trên Windows/Linux."""
    red_key = task["red_key"]
    blue_key = task["blue_key"]
    game_seed = task["game_seed"]
    same_seed_self_play = task["same_seed_self_play"]

    agent_red = create_agent(
        red_key,
        config=task["red_cfg"],
        seed=game_seed,
        instance_name=task["red_label"],
    )
    blue_seed = game_seed if not same_seed_self_play else game_seed + 10000
    agent_blue = create_agent(
        blue_key,
        config=task["blue_cfg"],
        seed=blue_seed,
        instance_name=task["blue_label"],
    )
    match = run_match(
        agent_red,
        agent_blue,
        seed=game_seed,
        max_turns=task["max_turns"],
        move_timeout_ms=task["move_timeout_ms"],
        strict_timeout=task["strict_timeout"],
        draw_on_max_turns=task["draw_on_max_turns"],
        record_moves=task["record_moves"],
        match_id=task["match_id"],
        run_id=task["run_id"],
        budget_mode=task["budget_mode"],
        red_config_id=task["red_config_id"],
        blue_config_id=task["blue_config_id"],
        slot_a_side=task["slot_a_side"],
    )
    return task["idx"], match


def _ensure_worker_pythonpath() -> None:
    """Bảo đảm tiến trình con `spawn` trên Windows luôn tìm thấy `packages/` và `research/experiments/`."""
    existing = os.environ.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p] if existing else []
    changed = False
    for p in (str(PACKAGES_DIR), str(EXPERIMENTS_DIR)):
        if p not in parts:
            parts.insert(0, p)
            changed = True
    if changed:
        os.environ["PYTHONPATH"] = os.pathsep.join(parts)


def run_head_to_head(
    agent_a_name: str,
    agent_b_name: str,
    *,
    games_per_pair: int = 200,
    side_balance: bool = True,
    base_seed: int = DEFAULT_SEED,
    seeds: Sequence[int] | None = None,
    max_turns: int = 200,
    budget_mode: str = "default",
    move_timeout_ms: float | None = None,
    strict_timeout: bool = False,
    draw_on_max_turns: bool = False,
    agent_configs: dict[str, dict[str, Any]] | None = None,
    config_a: dict[str, Any] | None = None,
    config_b: dict[str, Any] | None = None,
    agent_a_label: str | None = None,
    agent_b_label: str | None = None,
    record_moves: bool = True,
    run_id: str | None = None,
    show_progress: bool = True,
    max_workers: int = 1,
) -> list[MatchResult]:
    """Chạy một cặp đấu gồm `games_per_pair` ván, tự động đảo bên Đỏ/Xanh nếu `side_balance=True`."""
    if games_per_pair <= 0:
        raise ValueError("`games_per_pair` phải lớn hơn 0.")

    name_a = normalize_agent_name(agent_a_name)
    name_b = normalize_agent_name(agent_b_name)
    label_a = agent_a_label or name_a
    label_b = agent_b_label or name_b

    cfg_map = agent_configs or {}
    resolved_cfg_a = deepcopy(config_a if config_a is not None else cfg_map.get(name_a))
    resolved_cfg_b = deepcopy(config_b if config_b is not None else cfg_map.get(name_b))

    cfg_id_a = resolve_agent_config_id(name_a, resolved_cfg_a)
    cfg_id_b = resolve_agent_config_id(name_b, resolved_cfg_b)

    tasks: list[dict[str, Any]] = []
    for idx in range(games_per_pair):
        swap_sides = side_balance and (idx % 2 == 1)
        game_seed = _select_game_seed(idx, side_balance=side_balance, base_seed=base_seed, seeds=seeds)

        if swap_sides:
            red_key, blue_key = name_b, name_a
            red_label, blue_label = label_b, label_a
            red_cfg, blue_cfg = resolved_cfg_b, resolved_cfg_a
            red_cid, blue_cid = cfg_id_b, cfg_id_a
            slot_a_side = "blue"
        else:
            red_key, blue_key = name_a, name_b
            red_label, blue_label = label_a, label_b
            red_cfg, blue_cfg = resolved_cfg_a, resolved_cfg_b
            red_cid, blue_cid = cfg_id_a, cfg_id_b
            slot_a_side = "red"

        tasks.append(
            {
                "idx": idx,
                "red_key": red_key,
                "blue_key": blue_key,
                "red_label": red_label,
                "blue_label": blue_label,
                "red_cfg": red_cfg,
                "blue_cfg": blue_cfg,
                "red_config_id": red_cid,
                "blue_config_id": blue_cid,
                "slot_a_side": slot_a_side,
                "game_seed": game_seed,
                "same_seed_self_play": (red_key == blue_key and red_cid == blue_cid),
                "max_turns": max_turns,
                "budget_mode": budget_mode,
                "move_timeout_ms": move_timeout_ms,
                "strict_timeout": strict_timeout,
                "draw_on_max_turns": draw_on_max_turns,
                "record_moves": record_moves,
                "run_id": run_id,
                "match_id": f"{red_label}_vs_{blue_label}_g{idx + 1:04d}_s{game_seed}",
            }
        )

    use_parallel = max_workers > 1 and not (is_custom_registered(name_a) or is_custom_registered(name_b))
    if max_workers > 1 and not use_parallel:
        warnings.warn(
            "Tác tử tùy biến trong `_CUSTOM_REGISTRY` có thể không pickle được qua `ProcessPoolExecutor`; tự động chuyển về chạy tuần tự.",
            RuntimeWarning,
            stacklevel=2,
        )

    ordered_results: list[MatchResult | None] = [None] * games_per_pair
    desc = f"{label_a} vs {label_b} [{budget_mode}]"

    if use_parallel:
        _ensure_worker_pythonpath()
        worker_count = min(int(max_workers), games_per_pair)
        mp_ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=worker_count, mp_context=mp_ctx) as executor:
            futures = [executor.submit(_run_head_to_head_worker, task) for task in tasks]
            for fut in tqdm(as_completed(futures), total=len(tasks), desc=desc, disable=not show_progress):
                idx, res = fut.result()
                ordered_results[idx] = res
    else:
        for task in tqdm(tasks, total=len(tasks), desc=desc, disable=not show_progress):
            idx, res = _run_head_to_head_worker(task)
            ordered_results[idx] = res

    return [r for r in ordered_results if r is not None]


def run_round_robin(
    agent_names: list[str],
    *,
    games_per_pair: int = 200,
    side_balance: bool = True,
    base_seed: int = DEFAULT_SEED,
    seeds: Sequence[int] | None = None,
    max_turns: int = 200,
    budget_mode: str = "default",
    move_timeout_ms: float | None = None,
    strict_timeout: bool = False,
    draw_on_max_turns: bool = False,
    agent_configs: dict[str, dict[str, Any]] | None = None,
    record_moves: bool = True,
    run_id: str | None = None,
    show_progress: bool = True,
    max_workers: int = 1,
) -> TournamentResult:
    """Tổ chức giải đấu vòng tròn (mỗi cặp đấu đủ `games_per_pair` ván, đảo màu Đỏ/Xanh)."""
    normalized = [normalize_agent_name(n) for n in agent_names]
    if len(set(normalized)) < 2:
        raise ValueError("Round-robin cần ít nhất 2 tác tử phân biệt.")

    all_matches: list[MatchResult] = []
    pair_matches: dict[tuple[str, str], list[MatchResult]] = {}

    pair_offset = 0
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            a_name, b_name = normalized[i], normalized[j]
            matches = run_head_to_head(
                a_name,
                b_name,
                games_per_pair=games_per_pair,
                side_balance=side_balance,
                base_seed=base_seed + pair_offset * 1000,
                seeds=seeds,
                max_turns=max_turns,
                budget_mode=budget_mode,
                move_timeout_ms=move_timeout_ms,
                strict_timeout=strict_timeout,
                draw_on_max_turns=draw_on_max_turns,
                agent_configs=agent_configs,
                record_moves=record_moves,
                run_id=run_id,
                show_progress=show_progress,
                max_workers=max_workers,
            )
            pair_matches[(a_name, b_name)] = matches
            all_matches.extend(matches)
            pair_offset += 1

    return TournamentResult(
        agent_names=normalized,
        games_per_pair=games_per_pair,
        side_balance=side_balance,
        base_seed=base_seed,
        matches=all_matches,
        pair_matches=pair_matches,
    )


__all__ = [
    "TournamentResult",
    "run_head_to_head",
    "run_round_robin",
]
