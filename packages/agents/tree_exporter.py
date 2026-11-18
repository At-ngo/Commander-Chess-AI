# packages/agents/tree_exporter.py
"""Tiện ích xuất và trực quan hóa cây tìm kiếm Minimax dưới dạng JSON & đồ thị.

Cung cấp:
1. `export_minimax_tree_json`: Duyệt cây tìm kiếm phân cấp từ trạng thái cờ, tính điểm
   Heuristic H6 ở các nút lá, lan truyền ngược giá trị Min/Max, và xuất ra file JSON nhỏ gọn (~2-3 KB).
2. `plot_minimax_tree_from_json`: Đọc file JSON cây tìm kiếm và vẽ sơ đồ cây phân cấp
   chuẩn bài báo khoa học (300 DPI) bằng Matplotlib, làm nổi bật nhánh tối ưu (Principal Variation).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

from commander_game_engine.actions import ActionType, AtomicAction, TurnCommand
from commander_game_engine.engine import EngineResult, preview_action
from commander_game_engine.game_state import GameState, GameStatus, PieceType, Player
from commander_game_engine.move_generator import generate_legal_actions

from .base import AgentAction, format_action_str
from .evaluation import CCHEFEvaluator, opponent_of
from .minimax_agent import MinimaxAgent


def export_minimax_tree_to_dict(
    agent: MinimaxAgent,
    state: GameState,
    top_k_ply1: int = 3,
    top_k_ply2: int = 2,
) -> dict[str, Any]:
    """Trích xuất cây tìm kiếm Minimax (depth=2) thành cấu trúc dict JSON-serializable."""
    perspective = state.current_player
    opp = opponent_of(perspective)
    legal_actions = list(generate_legal_actions(state))

    if not legal_actions:
        return {
            "algorithm": agent.algorithm,
            "depth": agent.depth,
            "perspective": perspective.value,
            "best_action": None,
            "best_score": 0.0,
            "tree": {
                "id": "root",
                "type": "MAX",
                "player": perspective.value,
                "action": None,
                "score": 0.0,
                "is_best": True,
                "children": [],
            },
        }

    # Ply 1: Đánh giá nhanh các ứng viên phe ta (Maximizing)
    ply1_scored: list[tuple[float, Any, GameState, EngineResult]] = []
    for action in legal_actions:
        res = preview_action(state, action)
        next_s = res.state
        s, _, _ = agent.evaluator.evaluate_state(next_s, perspective)
        ply1_scored.append((float(s), action, next_s, res))

    ply1_scored.sort(key=lambda x: x[0], reverse=True)
    top_ply1 = ply1_scored[:top_k_ply1]

    root_node: dict[str, Any] = {
        "id": "root",
        "type": "MAX",
        "player": perspective.value,
        "action": None,
        "score": None,
        "is_best": True,
        "children": [],
    }

    best_root_val = -float("inf")
    best_child_idx = 0

    for idx, (s1, a1, next_s1, res1) in enumerate(top_ply1):
        act1_str = format_action_str(a1)
        p2_legal = list(generate_legal_actions(next_s1))

        # Ply 2: Đối phương chọn phản đòn làm điểm của ta nhỏ nhất (Minimizing)
        p2_scored: list[tuple[float, Any, GameState, dict[str, float]]] = []
        for a2 in p2_legal:
            res2 = preview_action(next_s1, a2)
            s2, comps, _ = agent.evaluator.evaluate_state(res2.state, perspective)
            p2_scored.append((float(s2), a2, res2.state, comps))

        p2_scored.sort(key=lambda x: x[0])  # Đối phương ép điểm ta xuống MIN
        top_p2 = p2_scored[:top_k_ply2]

        minimax_val = top_p2[0][0] if top_p2 else s1
        if minimax_val > best_root_val:
            best_root_val = minimax_val
            best_child_idx = idx

        child_node: dict[str, Any] = {
            "id": f"ply1_{idx}",
            "type": "MIN",
            "player": opp.value,
            "action": act1_str,
            "minimax_score": round(float(minimax_val), 4),
            "is_best": False,
            "children": [],
        }

        for jdx, (s2, a2, next_s2, comps) in enumerate(top_p2):
            leaf_node = {
                "id": f"ply2_{idx}_{jdx}",
                "type": "LEAF",
                "player": perspective.value,
                "action": format_action_str(a2),
                "score": round(float(s2), 4),
                "is_best": (jdx == 0),
                "heuristic_components": {
                    k: round(float(v), 4) for k, v in comps.items()
                },
            }
            child_node["children"].append(leaf_node)

        root_node["children"].append(child_node)

    root_node["score"] = round(float(best_root_val), 4)
    if root_node["children"]:
        root_node["children"][best_child_idx]["is_best"] = True

    return {
        "algorithm": "Minimax",
        "depth": 2,
        "perspective": perspective.value,
        "best_action": (
            root_node["children"][best_child_idx]["action"]
            if root_node["children"]
            else None
        ),
        "best_score": root_node["score"],
        "tree": root_node,
    }


def export_minimax_tree_json(
    agent: MinimaxAgent,
    state: GameState,
    filepath: Union[str, Path],
    top_k_ply1: int = 3,
    top_k_ply2: int = 2,
) -> Path:
    """Xuất cây tìm kiếm Minimax từ trạng thái cờ thành file JSON có cấu trúc."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    tree_data = export_minimax_tree_to_dict(
        agent=agent,
        state=state,
        top_k_ply1=top_k_ply1,
        top_k_ply2=top_k_ply2,
    )
    with open(p, "w", encoding="utf-8") as f:
        json.dump(tree_data, f, indent=2, ensure_ascii=False)
    return p


def plot_minimax_tree_from_json(
    json_path_or_dict: Union[str, Path, dict[str, Any]],
    output_png_path: Union[str, Path, None] = None,
    figsize: tuple[float, float] = (13, 7.5),
    dpi: int = 300,
) -> Any:
    """Vẽ cây tìm kiếm Minimax từ file JSON hoặc dictionary dữ liệu cây bằng Matplotlib."""
    import matplotlib.pyplot as plt

    if isinstance(json_path_or_dict, (str, Path)):
        with open(json_path_or_dict, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json_path_or_dict

    root = data["tree"]
    perspective = data.get("perspective", "red").upper()
    best_score = data.get("best_score", 0.0)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # 1. Vẽ Root (MAX)
    root_x, root_y = 50.0, 90.0
    ax.text(
        root_x,
        root_y,
        f"Gốc: MAX ({perspective})\nĐiểm chọn: {best_score:+.4f}",
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="square,pad=0.5",
            facecolor="#ffcccc" if perspective == "RED" else "#cce5ff",
            edgecolor="#cc0000" if perspective == "RED" else "#0066cc",
            lw=2.5,
        ),
        fontsize=10,
        fontweight="bold",
    )

    children_ply1 = root.get("children", [])
    num_p1 = len(children_ply1)
    if num_p1 == 0:
        if output_png_path:
            plt.savefig(output_png_path, bbox_inches="tight")
            plt.close(fig)
        return fig

    # Tọa độ X cho các nhánh Ply 1
    p1_spacing = 80.0 / max(num_p1, 1)
    p1_xs = [10.0 + (i + 0.5) * p1_spacing for i in range(num_p1)]
    p1_y = 55.0

    leaf_records: list[tuple[float, float, str, float, float, bool]] = []

    for i, child in enumerate(children_ply1):
        cx = p1_xs[i]
        is_best_p1 = child.get("is_best", False)
        act_str = child.get("action", "")
        if len(act_str) > 28:
            act_str = act_str[:25] + "..."
        score_val = child.get("minimax_score", 0.0)

        # Mũi tên từ Root -> Ply 1
        arrow_color = "#cc0000" if is_best_p1 else "#888888"
        arrow_lw = 2.5 if is_best_p1 else 1.0
        ax.annotate(
            "",
            xy=(cx, p1_y + 6.5),
            xytext=(root_x, root_y - 6.5),
            arrowprops=dict(
                arrowstyle="->",
                color=arrow_color,
                lw=arrow_lw + 0.8,
                mutation_scale=15,
            ),
        )

        label = f"{act_str}\n[MIN: {score_val:+.4f}]" + (" ★" if is_best_p1 else "")
        bg_col = "#ff9999" if is_best_p1 else "#f2f2f2"
        ax.text(
            cx,
            p1_y,
            label,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor=bg_col,
                edgecolor=arrow_color,
                lw=arrow_lw,
            ),
            fontsize=8.5,
            fontweight="bold" if is_best_p1 else "normal",
        )

        # Chuẩn bị tọa độ cho Ply 2 (Nút lá)
        leaves = child.get("children", [])
        num_leaves = len(leaves)
        if num_leaves > 0:
            leaf_span = p1_spacing * 0.85
            leaf_start = cx - leaf_span / 2.0
            leaf_sub_spacing = leaf_span / max(num_leaves, 1)
            for j, leaf in enumerate(leaves):
                lx = leaf_start + (j + 0.5) * leaf_sub_spacing
                ly = 15.0
                is_best_leaf = is_best_p1 and leaf.get("is_best", False)
                leaf_records.append((lx, ly, leaf.get("action", ""), leaf.get("score", 0.0), cx, is_best_leaf))

    # 2. Vẽ Ply 2 (Nút lá)
    for lx, ly, act_leaf, leaf_score, parent_x, is_best_leaf in leaf_records:
        arrow_col = "#cc0000" if is_best_leaf else "#aaaaaa"
        arrow_lw = 2.2 if is_best_leaf else 0.8
        arrow_style = "solid" if is_best_leaf else "dashed"

        ax.annotate(
            "",
            xy=(lx, ly + 6.0),
            xytext=(parent_x, p1_y - 6.5),
            arrowprops=dict(
                arrowstyle="->",
                color=arrow_col,
                lw=arrow_lw + 0.5,
                linestyle=arrow_style,
                mutation_scale=12,
            ),
        )

        short_act = act_leaf if len(act_leaf) <= 26 else act_leaf[:23] + "..."
        leaf_text = f"{short_act}\nH6: {leaf_score:+.4f}" + (" ★" if is_best_leaf else "")
        leaf_bg = "#ffd6cc" if is_best_leaf else "#e6f2ff"
        ax.text(
            lx,
            ly,
            leaf_text,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor=leaf_bg,
                edgecolor=arrow_col,
                lw=arrow_lw,
            ),
            fontsize=7.5,
            fontweight="bold" if is_best_leaf else "normal",
        )

    plt.title(
        f"Trực quan hóa Cây tìm kiếm Minimax (Depth = 2, Top-{num_p1} Nhánh ứng viên)\n"
        f"Đường đỏ đậm (★): Nhánh tối ưu (Principal Variation) — Nước đi: {data.get('best_action')}",
        fontsize=11.5,
        fontweight="bold",
        pad=16,
    )

    if output_png_path:
        p_out = Path(output_png_path)
        p_out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(p_out, bbox_inches="tight")
        plt.close(fig)

    return fig




# ===========================================================================
# TIỆN ÍCH XUẤT VÀ VẼ CÂY TÌM KIẾM ALPHA-BETA (CÓ ĐÁNH DẤU CẮT TỈA)
# ===========================================================================

def export_alphabeta_tree_to_dict(
    agent: Any,
    state: GameState,
    top_k_ply1: int = 3,
    top_k_ply2: int = 3,
) -> dict[str, Any]:
    """Trích xuất cây tìm kiếm Alpha-Beta có đánh dấu các nhánh bị cắt tỉa (Cutoff)."""
    perspective = state.current_player
    opp = opponent_of(perspective)
    legal_actions = list(generate_legal_actions(state))

    if not legal_actions:
        return {
            "algorithm": "AlphaBeta",
            "depth": getattr(agent, "depth", 2),
            "perspective": perspective.value,
            "best_action": None,
            "best_score": 0.0,
            "tree": {
                "id": "root",
                "type": "MAX",
                "player": perspective.value,
                "action": None,
                "score": 0.0,
                "is_best": True,
                "children": [],
            },
        }

    # Ply 1: Sắp xếp nước đi (Move Ordering) và đánh giá ứng viên
    ply1_scored: list[tuple[float, Any, GameState, EngineResult]] = []
    for action in legal_actions:
        res = preview_action(state, action)
        next_s = res.state
        s, _, _ = agent.evaluator.evaluate_state(next_s, perspective)
        ply1_scored.append((float(s), action, next_s, res))

    ply1_scored.sort(key=lambda x: x[0], reverse=True)
    top_ply1 = ply1_scored[:top_k_ply1]

    root_node: dict[str, Any] = {
        "id": "root",
        "type": "MAX",
        "player": perspective.value,
        "action": None,
        "score": None,
        "alpha": -float("inf"),
        "beta": float("inf"),
        "is_best": True,
        "children": [],
    }

    alpha = -float("inf")
    beta = float("inf")
    best_root_val = -float("inf")
    best_child_idx = 0
    total_cutoffs = 0

    for idx, (s1, a1, next_s1, res1) in enumerate(top_ply1):
        act1_str = format_action_str(a1)
        p2_legal = list(generate_legal_actions(next_s1))

        # Ply 2: MIN node
        p2_scored: list[tuple[float, Any, GameState, dict[str, float]]] = []
        for a2 in p2_legal:
            res2 = preview_action(next_s1, a2)
            s2, comps, _ = agent.evaluator.evaluate_state(res2.state, perspective)
            p2_scored.append((float(s2), a2, res2.state, comps))

        p2_scored.sort(key=lambda x: x[0])  # Đối phương ép điểm MIN
        candidate_p2 = p2_scored[:top_k_ply2]

        child_node: dict[str, Any] = {
            "id": f"ply1_{idx}",
            "type": "MIN",
            "player": opp.value,
            "action": act1_str,
            "score": None,
            "alpha": alpha,
            "beta": beta,
            "is_best": False,
            "pruned": False,
            "children": [],
        }

        min_val = float("inf")
        local_beta = beta
        branch_pruned = False

        for jdx, (s2, a2, next_s2, comps) in enumerate(candidate_p2):
            leaf_node = {
                "id": f"ply2_{idx}_{jdx}",
                "type": "LEAF",
                "player": perspective.value,
                "action": format_action_str(a2),
                "score": round(float(s2), 4),
                "is_best": False,
                "pruned": branch_pruned,
                "heuristic_components": {
                    k: round(float(v), 4) for k, v in comps.items()
                },
            }

            if not branch_pruned:
                if s2 < min_val:
                    min_val = s2
                local_beta = min(local_beta, min_val)
                # Kiểm tra cắt tỉa beta <= alpha
                if local_beta <= alpha:
                    branch_pruned = True
                    total_cutoffs += 1
                    leaf_node["pruning_trigger"] = True

            child_node["children"].append(leaf_node)

        final_child_val = min_val if min_val != float("inf") else s1
        child_node["score"] = round(float(final_child_val), 4)

        if final_child_val > best_root_val:
            best_root_val = final_child_val
            best_child_idx = idx

        alpha = max(alpha, best_root_val)
        root_node["alpha"] = round(float(alpha), 4)
        root_node["children"].append(child_node)

    root_node["score"] = round(float(best_root_val), 4)
    if root_node["children"]:
        root_node["children"][best_child_idx]["is_best"] = True

    return {
        "algorithm": "AlphaBeta",
        "depth": 2,
        "perspective": perspective.value,
        "best_action": (
            root_node["children"][best_child_idx]["action"]
            if root_node["children"]
            else None
        ),
        "best_score": root_node["score"],
        "total_cutoffs_in_tree": total_cutoffs,
        "tree": root_node,
    }


def export_alphabeta_tree_json(
    agent: Any,
    state: GameState,
    filepath: Union[str, Path],
    top_k_ply1: int = 3,
    top_k_ply2: int = 3,
) -> Path:
    """Xuất cây tìm kiếm Alpha-Beta từ trạng thái cờ thành file JSON có cấu trúc."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    tree_data = export_alphabeta_tree_to_dict(
        agent=agent,
        state=state,
        top_k_ply1=top_k_ply1,
        top_k_ply2=top_k_ply2,
    )
    with open(p, "w", encoding="utf-8") as f:
        json.dump(tree_data, f, indent=2, ensure_ascii=False)
    return p


def plot_alphabeta_tree_from_json(
    json_path_or_dict: Union[str, Path, dict[str, Any]],
    output_png_path: Union[str, Path, None] = None,
    figsize: tuple[float, float] = (14, 8.0),
    dpi: int = 300,
) -> Any:
    """Vẽ cây tìm kiếm Alpha-Beta, làm nổi bật nhánh cắt tỉa bằng nét đứt đỏ và nhãn [BỊ CẮT TỈA]."""
    import matplotlib.pyplot as plt

    if isinstance(json_path_or_dict, (str, Path)):
        with open(json_path_or_dict, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json_path_or_dict

    root = data["tree"]
    perspective = data.get("perspective", "red").upper()
    best_score = data.get("best_score", 0.0)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # 1. Root (MAX)
    root_x, root_y = 50.0, 90.0
    ax.text(
        root_x,
        root_y,
        f"Gốc: MAX ({perspective})\nĐiểm chọn: {best_score:+.4f}\nα = {root.get('alpha', -1):+.4f}",
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="square,pad=0.5",
            facecolor="#ffcccc" if perspective == "RED" else "#cce5ff",
            edgecolor="#cc0000" if perspective == "RED" else "#0066cc",
            lw=2.5,
        ),
        fontsize=9.5,
        fontweight="bold",
    )

    children_p1 = root.get("children", [])
    num_p1 = len(children_p1)
    if num_p1 == 0:
        return fig

    p1_spacing = 90.0 / max(num_p1, 1)
    p1_start_x = 5.0 + p1_spacing / 2.0
    p1_y = 55.0

    leaf_records = []

    for idx, child in enumerate(children_p1):
        cx = p1_start_x + idx * p1_spacing
        is_best_p1 = child.get("is_best", False)

        arrow_color = "#cc0000" if is_best_p1 else "#555555"
        arrow_lw = 2.4 if is_best_p1 else 1.2
        arrow_style = "solid" if is_best_p1 else "dashed"

        ax.annotate(
            "",
            xy=(cx, p1_y + 6.5),
            xytext=(root_x, root_y - 6.5),
            arrowprops=dict(
                arrowstyle="->",
                color=arrow_color,
                lw=arrow_lw,
                linestyle=arrow_style,
                mutation_scale=14,
            ),
        )

        p1_act = child.get("action", "")
        p1_score = child.get("score", 0.0)
        p1_text = f"Ply 1 [MIN]\n{p1_act[:25]}\nScore: {p1_score:+.4f}" + (" ★" if is_best_p1 else "")

        bg_col = "#ffe6e6" if is_best_p1 else "#f0f0f0"
        ax.text(
            cx,
            p1_y,
            p1_text,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor=bg_col,
                edgecolor=arrow_color,
                lw=arrow_lw,
            ),
            fontsize=8.5,
            fontweight="bold" if is_best_p1 else "normal",
        )

        # Chuẩn bị tọa độ Ply 2
        leaves = child.get("children", [])
        num_leaves = len(leaves)
        if num_leaves > 0:
            leaf_span = p1_spacing * 0.88
            leaf_start = cx - leaf_span / 2.0
            leaf_sub_spacing = leaf_span / max(num_leaves, 1)
            for j, leaf in enumerate(leaves):
                lx = leaf_start + (j + 0.5) * leaf_sub_spacing
                ly = 15.0
                is_pruned = leaf.get("pruned", False)
                is_best_leaf = is_best_p1 and leaf.get("is_best", False)
                leaf_records.append((lx, ly, leaf.get("action", ""), leaf.get("score", 0.0), cx, is_best_leaf, is_pruned))

    # 2. Ply 2 (Nút lá hoặc Bị cắt tỉa)
    for lx, ly, act_leaf, leaf_score, parent_x, is_best_leaf, is_pruned in leaf_records:
        if is_pruned:
            arrow_col = "#e11d48"
            arrow_lw = 1.0
            arrow_style = "dotted"
            leaf_bg = "#fee2e2"
            leaf_text = f"[BỊ CẮT TỈA]\nβ ≤ α (Cutoff)\n(Tiết kiệm nút)"
        else:
            arrow_col = "#cc0000" if is_best_leaf else "#888888"
            arrow_lw = 2.2 if is_best_leaf else 0.8
            arrow_style = "solid" if is_best_leaf else "dashed"
            leaf_bg = "#ffd6cc" if is_best_leaf else "#e6f2ff"
            short_act = act_leaf if len(act_leaf) <= 24 else act_leaf[:21] + "..."
            leaf_text = f"{short_act}\nH6: {leaf_score:+.4f}" + (" ★" if is_best_leaf else "")

        ax.annotate(
            "",
            xy=(lx, ly + 6.0),
            xytext=(parent_x, p1_y - 6.5),
            arrowprops=dict(
                arrowstyle="->",
                color=arrow_col,
                lw=arrow_lw + 0.5,
                linestyle=arrow_style,
                mutation_scale=11,
            ),
        )

        ax.text(
            lx,
            ly,
            leaf_text,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor=leaf_bg,
                edgecolor=arrow_col,
                lw=arrow_lw,
            ),
            fontsize=7.2,
            fontweight="bold" if is_best_leaf or is_pruned else "normal",
        )

    plt.title(
        f"Trực quan hóa Cây tìm kiếm Alpha-Beta (Depth = 2, Cắt tỉa nhánh β ≤ α)\n"
        f"Đỏ đậm (★): Nhánh tối ưu PV | Đỏ chấm [BỊ CẮT TỈA]: Nhánh bị triệt tiêu không cần duyệt",
        fontsize=11.5,
        fontweight="bold",
        pad=16,
    )

    if output_png_path:
        p_out = Path(output_png_path)
        p_out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(p_out, bbox_inches="tight")
        plt.close(fig)

    return fig
