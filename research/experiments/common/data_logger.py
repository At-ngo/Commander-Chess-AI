"""Lưu biên bản ván đấu, bảng CSV (`moves`, `games`, `pair_results`), cấu hình JSON và hỗ trợ Weights & Biases (wandb)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Sequence
import warnings

from .config import prepare_run_directory
from .imports import HAS_WANDB, PROJECT_ROOT, RUNS_DIR, load_dotenv, pd, wandb
from .match_runner import MatchResult
from .reproducibility import capture_reproducibility_metadata


class ExperimentLogger:
    """Quản lý lưu trữ kết quả thực nghiệm (JSON, JSONL, CSV, game_records, figures) tại `research/results/`."""

    def __init__(
        self,
        run_dir: Path | str,
        *,
        allow_overwrite: bool = False,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.allow_overwrite = allow_overwrite
        self.run_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        *,
        run_tag: str | None = None,
    ) -> "ExperimentLogger":
        run_dir = prepare_run_directory(config, run_tag=run_tag, create=True)
        return cls(run_dir, allow_overwrite=bool(config.get("allow_overwrite", False)))

    def _check_target(self, filename: str) -> Path:
        target = self.run_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not self.allow_overwrite:
            raise FileExistsError(f"Không ghi đè file kết quả đã tồn tại (`allow_overwrite=false`): {target}")
        return target

    def save_json(self, filename: str, payload: Any) -> Path:
        target = self._check_target(filename)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def save_jsonl(self, filename: str, records: Sequence[dict[str, Any]]) -> Path:
        target = self._check_target(filename)
        with target.open("w", encoding="utf-8") as fp:
            for item in records:
                fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        return target

    def save_csv(self, filename: str, rows: Sequence[dict[str, Any]] | pd.DataFrame) -> Path:
        target = self._check_target(filename)
        if isinstance(rows, pd.DataFrame):
            rows.to_csv(target, index=False, encoding="utf-8")
            return target
        rows_list = list(rows)
        if not rows_list:
            target.write_text("", encoding="utf-8")
            return target
        fieldnames = list(rows_list[0].keys())
        with target.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_list)
        return target

    def save_resolved_config(self, config: dict[str, Any], filename: str = "resolved_config.json") -> Path:
        return self.save_json(filename, config)

    def save_config_json(self, config: dict[str, Any], filename: str = "config.json") -> Path:
        return self.save_json(filename, config)

    def save_environment_json(
        self,
        config: dict[str, Any] | None = None,
        filename: str = "environment.json",
        *,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        payload = capture_reproducibility_metadata(config, extra=extra)
        return self.save_json(filename, payload)

    def save_match_summaries(self, matches: Sequence[MatchResult], filename: str = "matches.csv") -> Path:
        rows = [m.to_summary_dict() for m in matches]
        return self.save_csv(filename, rows)

    def save_game_records(
        self,
        matches: Sequence[MatchResult],
        *,
        run_id: str = "",
        subdir: str = "game_records",
    ) -> list[Path]:
        """Lưu biên bản từng ván vào `game_records/game_XXXX.json` kèm thông tin tác tử Đỏ/Xanh."""
        saved_paths: list[Path] = []
        for idx, m in enumerate(matches, start=1):
            rel_path = f"{subdir}/game_{idx:04d}.json"
            m.game_record_path = rel_path
            record = {
                "run_id": run_id or m.run_id or "",
                "game_id": m.match_id,
                "seed": m.seed,
                "budget_mode": m.budget_mode,
                "agent_red": m.red_agent,
                "agent_blue": m.blue_agent,
                "red_config_id": m.red_config_id,
                "blue_config_id": m.blue_config_id,
                "winner": m.winner,
                "result_status": m.result_status,
                "termination_reason": m.reason,
                "turn_count": m.turn_count,
                "total_decisions": m.total_decisions or m.action_count,
                "total_atomic_actions": m.total_atomic_actions,
                "duration_sec": round(float(m.duration_sec or (m.duration_ms / 1000.0)), 6),
                "red_game_points": m.red_game_points,
                "blue_game_points": m.blue_game_points,
                "final_scores": m.final_scores,
                "error": m.error,
                "error_side": m.error_side,
                "moves": [mv.to_dict() for mv in m.moves],
            }
            saved_paths.append(self.save_json(rel_path, record))
        return saved_paths

    def save_games_csv(
        self,
        matches: Sequence[MatchResult],
        *,
        run_id: str = "",
        filename: str = "games.csv",
    ) -> Path:
        """Xuất `games.csv` theo đúng schema chuẩn (phân biệt `result_status` & đường dẫn replay)."""
        rows: list[dict[str, Any]] = []
        for m in matches:
            rows.append(
                {
                    "run_id": run_id or m.run_id or "",
                    "game_id": m.match_id,
                    "seed": m.seed,
                    "budget_mode": m.budget_mode,
                    "agent_red": m.red_agent,
                    "agent_blue": m.blue_agent,
                    "red_config_id": m.red_config_id or "",
                    "blue_config_id": m.blue_config_id or "",
                    "winner": m.winner if m.winner is not None else "",
                    "result_status": m.result_status,
                    "termination_reason": m.reason,
                    "total_decisions": m.total_decisions or m.action_count,
                    "total_atomic_actions": m.total_atomic_actions,
                    "duration_sec": round(float(m.duration_sec or (m.duration_ms / 1000.0)), 6),
                    "red_game_points": "" if m.red_game_points is None else m.red_game_points,
                    "blue_game_points": "" if m.blue_game_points is None else m.blue_game_points,
                    "game_record_path": m.game_record_path or "",
                    "error": m.error or "",
                }
            )
        return self.save_csv(filename, rows)

    def save_moves_csv(
        self,
        matches: Sequence[MatchResult],
        *,
        run_id: str = "",
        filename: str = "moves.csv",
    ) -> Path:
        """Xuất `moves.csv` theo đúng schema; để trống `nodes_visited`/`simulations` khi không áp dụng."""
        columns = [
            "run_id",
            "game_id",
            "decision_index",
            "turn_number",
            "side",
            "agent_name",
            "agent_config_id",
            "state_hash",
            "legal_action_count",
            "action_type",
            "selected_action",
            "decision_time_ms",
            "rule_triggered",
            "heuristic_score",
            "heuristic_components",
            "nodes_visited",
            "simulations",
            "valid_action",
            "over_budget",
            "error",
        ]
        target = self._check_target(filename)
        with target.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=columns)
            writer.writeheader()
            for m in matches:
                resolved_run_id = run_id or m.run_id or ""
                for mv in m.moves:
                    default_agent = m.red_agent if mv.player == "red" else m.blue_agent
                    default_cfg = (m.red_config_id if mv.player == "red" else m.blue_config_id) or ""
                    h_comps = mv.heuristic_components
                    h_comps_str = json.dumps(h_comps, ensure_ascii=False) if isinstance(h_comps, dict) else ""
                    writer.writerow(
                        {
                            "run_id": resolved_run_id,
                            "game_id": m.match_id,
                            "decision_index": mv.step_index,
                            "turn_number": mv.turn_number,
                            "side": mv.player,
                            "agent_name": mv.agent_name or default_agent,
                            "agent_config_id": mv.agent_config_id or default_cfg,
                            "state_hash": mv.state_hash,
                            "legal_action_count": mv.legal_action_count,
                            "action_type": mv.action_type,
                            "selected_action": mv.selected_action,
                            "decision_time_ms": round(float(mv.decision_time_ms), 4),
                            "rule_triggered": mv.rule_triggered or "",
                            "heuristic_score": "" if mv.heuristic_score is None else round(float(mv.heuristic_score), 4),
                            "heuristic_components": h_comps_str,
                            "nodes_visited": "" if mv.nodes_visited is None else mv.nodes_visited,
                            "simulations": "" if mv.simulations is None else mv.simulations,
                            "valid_action": mv.valid_action,
                            "over_budget": mv.over_budget,
                            "error": mv.error or "",
                        }
                    )
        return target

    def save_pair_results_csv(
        self,
        pair_df: pd.DataFrame,
        filename: str = "pair_results.csv",
    ) -> Path:
        return self.save_csv(filename, pair_df)

    def save_match_transcripts(self, matches: Sequence[MatchResult], filename: str = "transcripts.jsonl") -> Path:
        records = []
        for m in matches:
            records.append(
                {
                    **m.to_summary_dict(),
                    "moves": [mv.to_dict() for mv in m.moves],
                }
            )
        return self.save_jsonl(filename, records)


def init_wandb_run(
    config: dict[str, Any] | None = None,
    *,
    project: str = "commander-chess-ai",
    name: str | None = None,
    group: str | None = None,
    job_type: str = "experiment",
    tags: list[str] | None = None,
    mode: str | None = None,
    enabled: bool = True,
    wandb_dir: Path | str | None = None,
) -> Any | None:
    """Khởi tạo phiên theo dõi `wandb` an toàn từ cấu hình thực nghiệm (mặc định lưu log tại `research/runs/`)."""
    if not enabled or mode == "disabled":
        return None

    load_dotenv(PROJECT_ROOT / ".env")
    if not HAS_WANDB or wandb is None:
        warnings.warn(
            "Thư viện `wandb` chưa được cài trong `.venv`. "
            "Hãy thêm `wandb` vào `research/requirements.txt` và cài bằng `pip install wandb`.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None

    cfg = config or {}
    resolved_dir = Path(wandb_dir or cfg.get("resolved_wandb_dir") or RUNS_DIR)
    resolved_dir.mkdir(parents=True, exist_ok=True)

    init_kwargs: dict[str, Any] = {
        "project": project,
        "name": name or cfg.get("experiment_id"),
        "group": group or cfg.get("wandb_group") or cfg.get("agent_a"),
        "job_type": job_type,
        "config": cfg,
        "dir": str(resolved_dir),
    }
    if tags:
        init_kwargs["tags"] = tags
    if mode:
        init_kwargs["mode"] = mode

    return wandb.init(**init_kwargs)


def log_wandb_metrics(run: Any | None, metrics: dict[str, Any], *, step: int | None = None) -> None:
    """Ghi metric lên `wandb` nếu phiên run đang hoạt động."""
    if run is None:
        return
    if step is None:
        run.log(metrics)
    else:
        run.log(metrics, step=step)


def log_wandb_table(run: Any | None, key: str, df: pd.DataFrame) -> None:
    """Đẩy bảng DataFrame kết quả lên `wandb.Table` nếu phiên run đang hoạt động."""
    if run is None or wandb is None:
        return
    run.log({key: wandb.Table(dataframe=df)})


def finish_wandb_run(run: Any | None) -> None:
    """Đóng phiên `wandb` sạch sẽ."""
    if run is not None:
        run.finish()


__all__ = [
    "ExperimentLogger",
    "finish_wandb_run",
    "init_wandb_run",
    "log_wandb_metrics",
    "log_wandb_table",
]
