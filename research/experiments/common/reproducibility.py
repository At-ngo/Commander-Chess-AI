"""Thiết lập seed, ghi phiên bản mã nguồn, môi trường và cấu hình tái lập thực nghiệm."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
from typing import Any

from .imports import DEFAULT_SEED, PROJECT_ROOT, np, torch


def set_global_seed(seed: int = DEFAULT_SEED) -> int:
    """Đặt seed đồng nhất cho Python `random`, `numpy` và `torch` (nếu có)."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    if torch is not None:
        try:
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except Exception:
            pass
    return seed


def _safe_package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def get_git_revision(project_root: Path | None = None) -> dict[str, Any]:
    """Lấy commit hash và trạng thái git hiện tại một cách an toàn."""
    root = project_root or PROJECT_ROOT
    info: dict[str, Any] = {"commit": None, "branch": None, "is_dirty": None}
    try:
        commit_proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if commit_proc.returncode == 0:
            info["commit"] = commit_proc.stdout.strip()

        branch_proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if branch_proc.returncode == 0:
            info["branch"] = branch_proc.stdout.strip()

        status_proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if status_proc.returncode == 0:
            info["is_dirty"] = bool(status_proc.stdout.strip())
    except Exception:
        pass
    return info


def get_environment_info() -> dict[str, Any]:
    """Thu thập phiên bản Python, hệ điều hành và các thư viện nghiên cứu chính."""
    packages = {}
    for pkg in (
        "commander-chess-ai",
        "numpy",
        "pandas",
        "matplotlib",
        "seaborn",
        "scipy",
        "statsmodels",
        "PyYAML",
        "python-dotenv",
        "wandb",
        "psutil",
        "tqdm",
        "ipykernel",
        "pytest",
        "torch",
    ):
        packages[pkg] = _safe_package_version(pkg)

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "packages": packages,
    }


def capture_reproducibility_metadata(
    config: dict[str, Any] | None = None,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tổng hợp metadata đầy đủ (thời điểm UTC, seed, git, môi trường, cấu hình)."""
    cfg = deepcopy(config) if config is not None else {}
    meta: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": cfg.get("seed", DEFAULT_SEED),
        "seeds": cfg.get("seeds", [DEFAULT_SEED]),
        "rules_version": cfg.get("rules_version"),
        "engine_version": cfg.get("engine_version"),
        "git": get_git_revision(),
        "environment": get_environment_info(),
        "config": cfg,
    }
    if extra:
        meta["extra"] = deepcopy(extra)
    return meta


__all__ = [
    "DEFAULT_SEED",
    "capture_reproducibility_metadata",
    "get_environment_info",
    "get_git_revision",
    "set_global_seed",
]

