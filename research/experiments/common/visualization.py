"""Vẽ biểu đồ kết quả thực nghiệm, heatmap, ma trận đối đầu, W/D/L và đường độ nhạy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from .imports import np, pd, plt, sns


def _save_if_requested(fig: Any, save_path: Path | str | None, dpi: int = 150) -> None:
    if save_path is None:
        return
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, bbox_inches="tight")


def plot_metric_bar(
    summary_df: pd.DataFrame,
    *,
    label_col: str = "agent",
    metric_col: str = "score_ratio",
    ci_low_col: str | None = None,
    ci_high_col: str | None = None,
    title: str = "So sánh hiệu quả các Agent",
    xlabel: str = "Agent",
    ylabel: str = "Score Ratio",
    ylim: tuple[float, float] | None = (0.0, 1.05),
    save_path: Path | str | None = None,
    figsize: tuple[float, float] = (9.0, 5.0),
) -> tuple[Any, Any]:
    """Vẽ biểu đồ cột cho một chỉ số (hỗ trợ error bar khoảng tin cậy)."""
    fig, ax = plt.subplots(figsize=figsize)
    labels = summary_df[label_col].astype(str).tolist()
    values = summary_df[metric_col].astype(float).to_numpy()
    x = np.arange(len(labels))

    yerr = None
    if ci_low_col and ci_high_col and ci_low_col in summary_df.columns and ci_high_col in summary_df.columns:
        lows = np.clip(values - summary_df[ci_low_col].astype(float).to_numpy(), 0.0, None)
        highs = np.clip(summary_df[ci_high_col].astype(float).to_numpy() - values, 0.0, None)
        yerr = np.vstack([lows, highs])

    bars = ax.bar(x, values, yerr=yerr, capsize=5, color="#2563eb", alpha=0.88, edgecolor="#1e3a8a")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.02,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    _save_if_requested(fig, save_path)
    return fig, ax


def plot_wdl_stacked_bar(
    df: pd.DataFrame,
    *,
    label_col: str = "agent",
    win_col: str = "win_rate",
    draw_col: str = "draw_rate",
    loss_col: str = "loss_rate",
    title: str = "Tỷ lệ Thắng / Hòa / Thua (W/D/L)",
    save_path: Path | str | None = None,
    figsize: tuple[float, float] = (9.0, 5.0),
) -> tuple[Any, Any]:
    """Vẽ biểu đồ cột chồng Win / Draw / Loss kèm nhãn phần trăm."""
    fig, ax = plt.subplots(figsize=figsize)
    labels = df[label_col].astype(str).tolist()
    wins = df[win_col].astype(float).to_numpy() * 100.0
    draws = df[draw_col].astype(float).to_numpy() * 100.0
    losses = df[loss_col].astype(float).to_numpy() * 100.0
    x = np.arange(len(labels))

    ax.bar(x, wins, label="Thắng (Win %)", color="#16a34a", alpha=0.9)
    ax.bar(x, draws, bottom=wins, label="Hòa (Draw %)", color="#94a3b8", alpha=0.9)
    ax.bar(x, losses, bottom=wins + draws, label="Thua (Loss %)", color="#dc2626", alpha=0.88)

    for i in range(len(labels)):
        if wins[i] >= 5:
            ax.text(i, wins[i] / 2.0, f"{wins[i]:.1f}%", ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
        if draws[i] >= 5:
            ax.text(i, wins[i] + draws[i] / 2.0, f"{draws[i]:.1f}%", ha="center", va="center", color="#111827", fontsize=8.5)
        if losses[i] >= 5:
            ax.text(i, wins[i] + draws[i] + losses[i] / 2.0, f"{losses[i]:.1f}%", ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Tỷ lệ (%)")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    _save_if_requested(fig, save_path)
    return fig, ax


def plot_turn_length_distribution(
    turns: Sequence[int],
    *,
    title: str = "Phân phối số lượt mỗi ván",
    xlabel: str = "Số lượt (turn_count)",
    bins: int = 25,
    save_path: Path | str | None = None,
    figsize: tuple[float, float] = (8.5, 4.5),
) -> tuple[Any, Any]:
    """Vẽ histogram phân phối độ dài ván đấu theo số lượt."""
    fig, ax = plt.subplots(figsize=figsize)
    arr = np.asarray(list(turns), dtype=float)
    ax.hist(arr, bins=bins, color="#6366f1", alpha=0.85, edgecolor="#312e81")
    if arr.size > 0:
        mean_val = float(np.mean(arr))
        med_val = float(np.median(arr))
        ax.axvline(mean_val, color="#ef4444", linestyle="--", linewidth=1.8, label=f"Mean = {mean_val:.1f}")
        ax.axvline(med_val, color="#10b981", linestyle=":", linewidth=1.8, label=f"Median = {med_val:.1f}")
        ax.legend()
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Số ván")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    _save_if_requested(fig, save_path)
    return fig, ax


def plot_matchup_heatmap(
    matrix_df: pd.DataFrame,
    *,
    title: str = "Ma trận đối đầu (Hàng vs Cột)",
    fmt: str = ".2f",
    cmap: str = "YlGnBu",
    vmin: float = 0.0,
    vmax: float = 1.0,
    save_path: Path | str | None = None,
    figsize: tuple[float, float] = (8.0, 6.5),
) -> tuple[Any, Any]:
    """Vẽ heatmap ma trận đối đầu giữa các tác tử."""
    fig, ax = plt.subplots(figsize=figsize)

    if sns is not None:
        sns.heatmap(
            matrix_df,
            annot=True,
            fmt=fmt,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            linewidths=0.6,
            linecolor="#e5e7eb",
            ax=ax,
        )
    else:
        data = matrix_df.to_numpy(dtype=float)
        masked = np.ma.masked_invalid(data)
        cmap_obj = plt.get_cmap(cmap).copy()
        cmap_obj.set_bad(color="#f3f4f6")
        im = ax.imshow(masked, cmap=cmap_obj, vmin=vmin, vmax=vmax, aspect="auto")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        rows, cols = data.shape
        ax.set_xticks(np.arange(cols))
        ax.set_yticks(np.arange(rows))
        ax.set_xticklabels(matrix_df.columns.tolist(), rotation=20, ha="right")
        ax.set_yticklabels(matrix_df.index.tolist())

        for i in range(rows):
            for j in range(cols):
                val = data[i, j]
                txt = "-" if np.isnan(val) else format(val, fmt)
                color = "white" if (not np.isnan(val) and val > (vmin + vmax) * 0.55) else "#111827"
                ax.text(j, i, txt, ha="center", va="center", color=color, fontsize=9)

    ax.set_title(title)
    ax.set_xlabel("Đối thủ (Cột)")
    ax.set_ylabel("Tác tử (Hàng)")
    fig.tight_layout()
    _save_if_requested(fig, save_path)
    return fig, ax


def plot_decision_time_comparison(
    summary_df: pd.DataFrame,
    *,
    label_col: str = "agent",
    mean_col: str = "avg_decision_time_ms",
    p95_col: str = "p95_decision_time_ms",
    title: str = "Thời gian quyết định trung bình và p95 (ms)",
    save_path: Path | str | None = None,
    figsize: tuple[float, float] = (9.5, 5.0),
) -> tuple[Any, Any]:
    """Vẽ biểu đồ nhóm so sánh độ trễ trung bình và phân vị p95 theo từng Agent."""
    fig, ax = plt.subplots(figsize=figsize)
    labels = summary_df[label_col].astype(str).tolist()
    means = summary_df[mean_col].astype(float).to_numpy()
    p95s = summary_df[p95_col].astype(float).to_numpy()

    x = np.arange(len(labels))
    width = 0.36
    ax.bar(x - width / 2, means, width, label="Trung bình (ms)", color="#0ea5e9")
    ax.bar(x + width / 2, p95s, width, label="p95 (ms)", color="#f97316")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_title(title)
    ax.set_xlabel("Agent")
    ax.set_ylabel("Thời gian (ms)")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    _save_if_requested(fig, save_path)
    return fig, ax


def plot_sensitivity_curve(
    df: pd.DataFrame,
    *,
    param_col: str,
    metric_col: str = "score_ratio",
    ci_low_col: str | None = None,
    ci_high_col: str | None = None,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    save_path: Path | str | None = None,
    figsize: tuple[float, float] = (8.5, 4.8),
) -> tuple[Any, Any]:
    """Vẽ đường xu hướng phân tích độ nhạy theo tham số."""
    ordered = df.sort_values(by=param_col)
    x_vals = ordered[param_col].tolist()
    y_vals = ordered[metric_col].astype(float).to_numpy()

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(x_vals, y_vals, marker="o", linewidth=2, color="#16a34a", label=metric_col)
    if ci_low_col and ci_high_col and ci_low_col in ordered.columns and ci_high_col in ordered.columns:
        low = ordered[ci_low_col].astype(float).to_numpy()
        high = ordered[ci_high_col].astype(float).to_numpy()
        ax.fill_between(x_vals, low, high, alpha=0.2, color="#16a34a", label="Khoảng tin cậy")

    ax.set_title(title or f"Độ nhạy của `{metric_col}` theo `{param_col}`")
    ax.set_xlabel(xlabel or param_col)
    ax.set_ylabel(ylabel or metric_col)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    fig.tight_layout()
    _save_if_requested(fig, save_path)
    return fig, ax


__all__ = [
    "plot_decision_time_comparison",
    "plot_matchup_heatmap",
    "plot_metric_bar",
    "plot_sensitivity_curve",
    "plot_turn_length_distribution",
    "plot_wdl_stacked_bar",
]
