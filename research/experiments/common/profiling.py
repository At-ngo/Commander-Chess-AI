"""Đo lường tài nguyên phần cứng (RAM, VRAM, CPU) và thời gian xử lý."""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
import tracemalloc
from typing import Any, Callable, TypeVar

from .imports import psutil, torch

_T = TypeVar("_T")


@dataclass
class ProfileResult:
    """Kết quả đo hiệu năng của một khối lệnh hoặc hàm."""

    label: str
    wall_time_ms: float
    cpu_time_ms: float
    python_peak_ram_mb: float
    process_rss_before_mb: float | None
    process_rss_after_mb: float | None
    process_rss_delta_mb: float | None
    vram_available: bool
    vram_peak_mb: float | None


def _read_process_rss_mb() -> float | None:
    if psutil is None:
        return None
    try:
        rss_bytes = psutil.Process(os.getpid()).memory_info().rss
        return rss_bytes / (1024 * 1024)
    except Exception:
        return None


def _read_cuda_vram_mb() -> dict[str, float] | None:
    if torch is None:
        return None
    try:
        if not torch.cuda.is_available():
            return None
        return {
            "allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
            "reserved_mb": torch.cuda.memory_reserved() / (1024 * 1024),
            "max_allocated_mb": torch.cuda.max_memory_allocated() / (1024 * 1024),
        }
    except Exception:
        return None


def capture_memory_snapshot() -> dict[str, Any]:
    """Chụp nhanh trạng thái RAM, CPU và VRAM hiện tại của tiến trình."""
    rss_mb = _read_process_rss_mb()
    cpu_pct = None
    if psutil is not None:
        try:
            cpu_pct = psutil.Process(os.getpid()).cpu_percent(interval=None)
        except Exception:
            cpu_pct = None

    vram = _read_cuda_vram_mb()
    return {
        "process_rss_mb": rss_mb,
        "cpu_count": os.cpu_count(),
        "process_cpu_percent": cpu_pct,
        "vram_available": vram is not None,
        "vram_allocated_mb": vram["allocated_mb"] if vram else None,
        "vram_reserved_mb": vram["reserved_mb"] if vram else None,
    }


class ProfileScope:
    """Context manager đo thời gian thực thi, CPU time, RAM và VRAM (nếu có CUDA)."""

    def __init__(self, label: str = "profile") -> None:
        self.label = label
        self.result: ProfileResult | None = None
        self._start_wall: float = 0.0
        self._start_cpu: float = 0.0
        self._rss_before: float | None = None
        self._started_tracemalloc: bool = False
        self._has_cuda: bool = False

    def __enter__(self) -> "ProfileScope":
        self._rss_before = _read_process_rss_mb()
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._started_tracemalloc = True
        else:
            tracemalloc.reset_peak()

        if torch is not None:
            try:
                if torch.cuda.is_available():
                    self._has_cuda = True
                    torch.cuda.reset_peak_memory_stats()
            except Exception:
                self._has_cuda = False

        self._start_cpu = time.process_time()
        self._start_wall = time.perf_counter()
        return self

    def __exit__(self, *_exc: Any) -> None:
        wall_ms = (time.perf_counter() - self._start_wall) * 1000.0
        cpu_ms = (time.process_time() - self._start_cpu) * 1000.0
        _, peak_bytes = tracemalloc.get_traced_memory()
        if self._started_tracemalloc:
            tracemalloc.stop()

        rss_after = _read_process_rss_mb()
        rss_delta = (
            (rss_after - self._rss_before)
            if (rss_after is not None and self._rss_before is not None)
            else None
        )
        vram_peak = None
        if self._has_cuda and torch is not None:
            try:
                vram_peak = torch.cuda.max_memory_allocated() / (1024 * 1024)
            except Exception:
                vram_peak = None

        self.result = ProfileResult(
            label=self.label,
            wall_time_ms=wall_ms,
            cpu_time_ms=cpu_ms,
            python_peak_ram_mb=peak_bytes / (1024 * 1024),
            process_rss_before_mb=self._rss_before,
            process_rss_after_mb=rss_after,
            process_rss_delta_mb=rss_delta,
            vram_available=self._has_cuda,
            vram_peak_mb=vram_peak,
        )


def profile_callable(
    fn: Callable[..., _T],
    *args: Any,
    label: str | None = None,
    **kwargs: Any,
) -> tuple[_T, ProfileResult]:
    """Chạy một hàm và trả về `(kết quả hàm, ProfileResult)`."""
    scope_label = label or getattr(fn, "__name__", "callable")
    with ProfileScope(scope_label) as prof:
        output = fn(*args, **kwargs)
    assert prof.result is not None
    return output, prof.result


__all__ = [
    "ProfileResult",
    "ProfileScope",
    "capture_memory_snapshot",
    "profile_callable",
]

