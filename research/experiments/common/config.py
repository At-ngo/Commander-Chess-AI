"""Cấu hình dùng chung cho các thực nghiệm (số ván, seed, giới hạn thời gian, đường dẫn)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

from .imports import COMMON_DIR, DEFAULT_SEED, PROJECT_ROOT, RESULTS_DIR, RUNS_DIR


DEFAULT_CONFIG_PATH = COMMON_DIR / "experiment_config.yaml"

POPULAR_SEEDS: list[int] = [2026, 42, 0, 7, 123, 1337, 2024, 2025, 3407, 9999]

REQUIRED_CONFIG_KEYS = (
    "experiment_id",
    "rules_version",
    "engine_version",
    "agent_a",
    "agent_b",
    "games_per_pair",
    "side_balance",
    "seeds",
    "agent_configs",
    "time_limit",
    "search_budget",
    "metrics",
    "output_location",
)

DEFAULT_EXPERIMENT_SETTINGS: dict[str, Any] = {
    "rules_version": "DEC-020",
    "engine_version": "commander_game_engine-dec020",
    "games_per_pair": 200,
    "side_balance": True,
    "max_turns": 200,
    "draw_on_max_turns": False,
    "seed": DEFAULT_SEED,
    "seeds": list(POPULAR_SEEDS),
    "budget_mode": "default",
    "budget_modes": {
        "default": {
            "move_timeout_ms": None,
            "strict_timeout": False,
            "description": "Chế độ A: cấu hình mặc định minh bạch, không ép ngắt thời gian từng nước.",
        },
        "controlled": {
            "move_timeout_ms": 1000,
            "strict_timeout": True,
            "description": "Chế độ B: ngân sách tính toán kiểm soát (move_timeout_ms = 1000 ms).",
        },
    },
    "time_limit": {
        "move_timeout_ms": 1000,
        "game_timeout_ms": 1800000,
    },
    "search_budget": {
        "max_nodes": 5000,
        "max_simulations": 200,
        "max_depth": 3,
    },
    "metrics": [
        "win_rate",
        "draw_rate",
        "loss_rate",
        "score_ratio",
        "avg_decision_time_ms",
        "p95_decision_time_ms",
        "avg_turns",
        "termination_reasons",
        "nodes_searched",
        "simulations_run",
    ],
    "output_location": str(RESULTS_DIR.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    "wandb_dir": str(RUNS_DIR.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    "allow_overwrite": False,
}

DEFAULT_AGENT_CONFIGS: dict[str, dict[str, Any]] = {
    "random": {
        "algorithm": "random",
        "class_name": "RandomAgent",
        "agent_config_id": "random_v1",
        "seed": DEFAULT_SEED,
    },
    "rules": {
        "algorithm": "rule_based",
        "class_name": "RuleBasedAgent",
        "agent_config_id": "Ruleset_B",
        "ruleset_name": "Ruleset_B",
        "ruleset_version": "1.0.0",
        "enable_check_rule": True,
        "tie_breaking": "random",
        "safe_check_preference": True,
        "safe_capture_preference": True,
        "avoid_losing_captures": True,
        "high_value_threshold": 20,
        "seed": DEFAULT_SEED,
    },
    "heuristic": {
        "algorithm": "heuristic",
        "class_name": "HeuristicAgent",
        "weight_config_id": "default_v1",
        "enabled_components": ["material", "safety", "attack", "position"],
        "weights": {
            "material": 1.0,
            "safety": 0.35,
            "attack": 0.25,
            "position": 0.15,
        },
        "normalization": "none",
        "tie_breaking": "random",
        "seed": DEFAULT_SEED,
    },
    "minimax": {
        "algorithm": "minimax",
        "class_name": "MinimaxAgent",
        "seed": DEFAULT_SEED,
        "depth": 2,
        "search_budget": {"max_nodes": 5000},
    },
    "alphabeta": {
        "algorithm": "alphabeta",
        "class_name": "AlphaBetaAgent",
        "seed": DEFAULT_SEED,
        "depth": 3,
        "move_ordering": True,
        "search_budget": {"max_nodes": 10000},
    },
    "mcts": {
        "algorithm": "mcts",
        "class_name": "MCTSAgent",
        "seed": DEFAULT_SEED,
        "iterations": 200,
        "exploration_c": 1.414,
        "max_rollout_steps": 60,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Gộp đệ quy 2 dict cấu hình mà không sửa dict gốc."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_raw_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Đọc toàn bộ tệp YAML cấu hình thực nghiệm (hoặc dùng mặc định nếu file không tồn tại)."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.is_file():
        if config_path is not None:
            raise FileNotFoundError(f"Không tìm thấy tệp cấu hình: {path}")
        return {
            "defaults": deepcopy(DEFAULT_EXPERIMENT_SETTINGS),
            "agent_configs": deepcopy(DEFAULT_AGENT_CONFIGS),
            "experiments": {},
        }
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Cấu hình YAML không hợp lệ (cần dict ở root): {path}")
    return data


def list_experiments(config_path: Path | str | None = None) -> list[str]:
    """Liệt kê danh sách `experiment_id` đã khai báo."""
    raw = load_raw_config(config_path)
    experiments = raw.get("experiments", {})
    if not isinstance(experiments, dict):
        return []
    return list(experiments.keys())


def validate_experiment_config(config: dict[str, Any]) -> None:
    """Kiểm tra tính hợp lệ của cấu hình thực nghiệm trước khi chạy."""
    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config or config[key] is None]
    if missing:
        raise ValueError(f"Thiếu trường cấu hình bắt buộc: {', '.join(missing)}")

    if not isinstance(config["experiment_id"], str) or not config["experiment_id"].strip():
        raise ValueError("`experiment_id` phải là chuỗi không rỗng.")
    if not isinstance(config["games_per_pair"], int) or config["games_per_pair"] <= 0:
        raise ValueError("`games_per_pair` phải là số nguyên dương.")
    if not isinstance(config["side_balance"], bool):
        raise ValueError("`side_balance` phải là boolean.")
    if not isinstance(config.get("draw_on_max_turns", False), bool):
        raise ValueError("`draw_on_max_turns` phải là boolean.")
    if not isinstance(config["seeds"], list) or not config["seeds"] or not all(
        isinstance(s, int) for s in config["seeds"]
    ):
        raise ValueError("`seeds` phải là danh sách số nguyên không rỗng.")
    if not isinstance(config["agent_configs"], dict) or not config["agent_configs"]:
        raise ValueError("`agent_configs` phải là dict không rỗng.")

    for role_key in ("agent_a", "agent_b"):
        agent_name = config[role_key]
        if agent_name not in config["agent_configs"]:
            raise ValueError(f"Agent `{agent_name}` ({role_key}) chưa được khai báo trong `agent_configs`.")

    roster = config.get("agent_roster")
    if roster is not None:
        if not isinstance(roster, list) or not roster:
            raise ValueError("`agent_roster` phải là danh sách không rỗng.")
        unknown = [name for name in roster if name not in config["agent_configs"]]
        if unknown:
            raise ValueError(f"`agent_roster` chứa agent chưa khai báo: {', '.join(unknown)}")

    if not isinstance(config["metrics"], list) or not config["metrics"]:
        raise ValueError("`metrics` phải là danh sách chỉ số không rỗng.")
    if not isinstance(config["time_limit"], dict) or not isinstance(config["search_budget"], dict):
        raise ValueError("`time_limit` và `search_budget` phải là dict.")
    budget_modes = config.get("budget_modes")
    if budget_modes is not None and not isinstance(budget_modes, dict):
        raise ValueError("`budget_modes` phải là dict.")


def load_experiment_config(
    experiment_id: str,
    *,
    overrides: dict[str, Any] | None = None,
    config_path: Path | str | None = None,
) -> dict[str, Any]:
    """Nạp và kiểm tra cấu hình thực nghiệm đã gộp defaults + experiment + overrides."""
    raw = load_raw_config(config_path)
    defaults = deep_merge(DEFAULT_EXPERIMENT_SETTINGS, raw.get("defaults", {}))
    all_agent_configs = deep_merge(DEFAULT_AGENT_CONFIGS, raw.get("agent_configs", {}))
    experiments = raw.get("experiments", {})

    if experiment_id not in experiments:
        available = ", ".join(experiments.keys())
        raise KeyError(
            f"Không tìm thấy `{experiment_id}` trong `experiments`. Hiện có: {available}"
        )

    resolved = deep_merge(defaults, experiments[experiment_id])
    resolved["agent_configs"] = deep_merge(all_agent_configs, resolved.get("agent_configs", {}))
    if overrides:
        resolved = deep_merge(resolved, overrides)

    validate_experiment_config(resolved)

    output_base = Path(resolved["output_location"])
    resolved_output = output_base if output_base.is_absolute() else (PROJECT_ROOT / output_base)
    resolved["resolved_output_dir"] = str(resolved_output / resolved["experiment_id"])

    wandb_base = Path(resolved.get("wandb_dir") or RUNS_DIR)
    resolved_wandb = wandb_base if wandb_base.is_absolute() else (PROJECT_ROOT / wandb_base)
    resolved["resolved_wandb_dir"] = str(resolved_wandb)
    return resolved


def prepare_run_directory(
    config: dict[str, Any],
    *,
    run_tag: str | None = None,
    create: bool = True,
) -> Path:
    """Tạo thư mục lưu kết quả riêng cho mỗi run trong `research/results/`, tránh ghi đè kết quả cũ."""
    base_dir = Path(config.get("resolved_output_dir") or (RESULTS_DIR / str(config.get("experiment_id", "run"))))
    tag = run_tag or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base_dir / tag
    if run_dir.exists() and not config.get("allow_overwrite", False):
        raise FileExistsError(
            f"Thư mục kết quả đã tồn tại (`allow_overwrite=false`): {run_dir}"
        )
    if create:
        run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


__all__ = [
    "COMMON_DIR",
    "DEFAULT_AGENT_CONFIGS",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_EXPERIMENT_SETTINGS",
    "DEFAULT_SEED",
    "POPULAR_SEEDS",
    "PROJECT_ROOT",
    "REQUIRED_CONFIG_KEYS",
    "RESULTS_DIR",
    "RUNS_DIR",
    "deep_merge",
    "list_experiments",
    "load_experiment_config",
    "load_raw_config",
    "prepare_run_directory",
    "validate_experiment_config",
]
