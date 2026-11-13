# packages/agents/evaluation/weights.py
"""Cấu hình phiên bản H1-H7, hệ số chuẩn hóa `scale_X`, trọng số CCHEF và pha ván đấu (H7)."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping, Sequence

from commander_game_engine.game_state import GameState, PieceType, Player

from .material_table import CCHEF_BASE_POINTS, HERO_BONUS


FEATURE_NAMES: tuple[str, ...] = ("M", "K", "Q", "P", "C", "D", "T")
VARIANT_NAMES: tuple[str, ...] = ("H1", "H2", "H3", "H4", "H5", "H6", "H7")

VARIANT_ENABLED_FEATURES: dict[str, tuple[str, ...]] = {
    "H1": ("M",),
    "H2": ("M", "P", "C"),
    "H3": ("M", "P", "C", "K"),
    "H4": ("M", "P", "C", "K", "Q"),
    "H5": ("M", "P", "C", "K", "Q", "D"),
    "H6": ("M", "K", "Q", "P", "C", "D", "T"),
    "H7": ("M", "K", "Q", "P", "C", "D", "T"),
}

# Trọng số khởi tạo đề xuất theo CCHEF §11 (tổng = 1.0)
DEFAULT_CCHEF_WEIGHTS: dict[str, float] = {
    "M": 0.25,
    "K": 0.25,
    "Q": 0.15,
    "P": 0.10,
    "C": 0.05,
    "D": 0.05,
    "T": 0.15,
}

# Scale chuẩn hóa cố định trước khi đánh giá test (CCHEF §11: clip(X / scale_X, -1, 1))
# Tổng V_base khởi đầu mỗi phe (với HQ=10, Tư lệnh=0) = 450đ.
DEFAULT_FEATURE_SCALES: dict[str, float] = {
    "M": 180.0,
    "K": 80.0,
    "Q": 60.0,
    "P": 80.0,
    "C": 60.0,
    "D": 50.0,
    "T": 80.0,
}

# Hệ số điều chỉnh nhóm trọng số theo pha (giai đoạn) ván đấu cho H7 (CCHEF §13.6)
DEFAULT_PHASE_MODIFIERS: dict[str, dict[str, float]] = {
    "opening": {"M": 0.85, "K": 0.90, "Q": 0.90, "P": 1.35, "C": 1.25, "D": 1.65, "T": 0.95},
    "middlegame": {"M": 1.00, "K": 1.00, "Q": 1.00, "P": 1.00, "C": 1.00, "D": 1.00, "T": 1.00},
    "endgame": {"M": 1.25, "K": 1.40, "Q": 1.45, "P": 0.80, "C": 0.95, "D": 0.40, "T": 1.15},
}

LEGACY_FEATURE_ALIASES: dict[str, str] = {
    "material": "M",
    "safety": "K",
    "king_safety": "K",
    "attack": "Q",
    "safe_check": "Q",
    "spc": "Q",
    "position": "P",
    "mobility": "C",
    "deployment": "D",
    "tactical": "T",
}

_INITIAL_TOTAL_NON_CMD_POINTS: float = 900.0  # 450 mỗi phe với HQ=10, Tư lệnh=0


def normalize_feature_key(key: str) -> str:
    k = str(key).strip()
    if k in FEATURE_NAMES:
        return k
    upper = k.upper()
    if upper in FEATURE_NAMES:
        return upper
    lower = k.lower()
    if lower in LEGACY_FEATURE_ALIASES:
        return LEGACY_FEATURE_ALIASES[lower]
    raise KeyError(f"Đặc trưng CCHEF không hợp lệ: '{key}'. Hỗ trợ: {FEATURE_NAMES}.")


def normalize_weights(
    raw_weights: Mapping[str, float],
    enabled_features: Sequence[str] | None = None,
    *,
    normalization: str = "sum_to_one",
) -> dict[str, float]:
    """Chuẩn hóa trọng số không âm (CCHEF §11 & §13.5)."""
    active = set(enabled_features) if enabled_features is not None else set(FEATURE_NAMES)
    out: dict[str, float] = {k: 0.0 for k in FEATURE_NAMES}

    for k, val in raw_weights.items():
        canon = normalize_feature_key(k)
        fval = float(val)
        if not math.isfinite(fval) or fval < 0.0:
            raise ValueError(f"Trọng số '{canon}' phải hữu hạn và không âm, nhận được {val}.")
        if canon in active:
            out[canon] = fval

    if normalization == "none":
        return out
    if normalization not in ("sum_to_one", "weight_l1"):
        raise ValueError(
            f"weight_normalization không hợp lệ '{normalization}'. Hỗ trợ: 'sum_to_one', 'weight_l1', 'none'."
        )

    total = sum(out[k] for k in FEATURE_NAMES if k in active)
    if total <= 0.0:
        raise ValueError(f"Tổng trọng số của các đặc trưng bật {sorted(active)} phải > 0.")
    return {k: (out[k] / total if k in active else 0.0) for k in FEATURE_NAMES}


def resolve_scales(raw_scales: Mapping[str, float] | None = None) -> dict[str, float]:
    scales = dict(DEFAULT_FEATURE_SCALES)
    if raw_scales:
        for k, v in raw_scales.items():
            canon = normalize_feature_key(k)
            fv = float(v)
            if not math.isfinite(fv) or fv <= 0.0:
                raise ValueError(f"scale_{canon} phải dương và hữu hạn, nhận được {v}.")
            scales[canon] = fv
    return scales


def compute_observable_phase(
    state: GameState,
    *,
    opening_material_threshold: float = 0.82,
    endgame_material_threshold: float = 0.45,
) -> dict[str, Any]:
    """Tính tỷ trọng pha (opening/middlegame/endgame) chỉ từ đặc trưng quan sát được và đối xứng 2 phe.

    Bảo đảm tính bất biến khi đảo góc nhìn Đỏ <-> Xanh (`HE-12`).
    """
    total_mat = 0.0
    mobile_count = 0
    advanced_count = 0
    red_combat_pieces = 0
    blue_combat_pieces = 0
    rows = state.board.ROWS

    for p in state.pieces.values():
        if p.piece_type == PieceType.COMMANDER:
            continue
        total_mat += CCHEF_BASE_POINTS[p.piece_type] + (HERO_BONUS if p.is_heroic else 0.0)
        if p.piece_type != PieceType.HEADQUARTERS:
            if p.owner == Player.RED:
                red_combat_pieces += 1
            else:
                blue_combat_pieces += 1

        if p.piece_type in (
            PieceType.INFANTRY,
            PieceType.MILITIA,
            PieceType.ENGINEER,
            PieceType.TANK,
            PieceType.ARTILLERY,
            PieceType.ANTI_AIRCRAFT,
            PieceType.MISSILE,
            PieceType.AIRCRAFT,
            PieceType.NAVY,
        ):
            mobile_count += 1
            if p.carried_by is not None:
                advanced_count += 1
            elif p.position is not None:
                adv_y = p.position[0] if p.owner == Player.RED else (rows - 1 - p.position[0])
                if adv_y >= 4:
                    advanced_count += 1

    mat_ratio = min(1.0, total_mat / _INITIAL_TOTAL_NON_CMD_POINTS)
    deploy_ratio = (advanced_count / mobile_count) if mobile_count > 0 else 1.0

    # Endgame weight tăng dần khi tổng vật chất giảm hoặc một phe còn ít quân tác chiến
    min_combat = min(red_combat_pieces, blue_combat_pieces)
    if mat_ratio <= endgame_material_threshold or min_combat <= 5:
        w_end = min(1.0, max(0.65, (endgame_material_threshold + 0.15 - mat_ratio) / 0.25))
    elif mat_ratio < opening_material_threshold:
        w_end = max(0.0, (opening_material_threshold - mat_ratio) / max(1e-6, opening_material_threshold - endgame_material_threshold)) * 0.45
    else:
        w_end = 0.0

    # Opening weight cao khi vật chất gần đầy đủ và chưa triển khai quá nhiều
    if mat_ratio >= opening_material_threshold and deploy_ratio < 0.55:
        w_open = min(1.0, (0.55 - deploy_ratio) / 0.38) * min(1.0, (mat_ratio - 0.72) / 0.20)
    else:
        w_open = 0.0

    raw_sum = w_open + w_end
    if raw_sum > 1.0:
        w_open /= raw_sum
        w_end /= raw_sum
        w_mid = 0.0
    else:
        w_mid = max(0.0, 1.0 - raw_sum)

    if w_end >= max(w_open, w_mid):
        label = "endgame"
    elif w_open >= max(w_mid, w_end):
        label = "opening"
    else:
        label = "middlegame"

    return {
        "phase_label": label,
        "opening": float(w_open),
        "middlegame": float(w_mid),
        "endgame": float(w_end),
        "material_ratio": float(mat_ratio),
        "deployment_ratio": float(deploy_ratio),
    }


def resolve_cchef_config(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Chuẩn hóa toàn bộ cấu hình biến thể H1..H7, trọng số, scales và cờ CO."""
    cfg = deepcopy(dict(config)) if config else {}
    variant = str(cfg.get("variant", "H6")).strip().upper()
    if variant not in VARIANT_NAMES:
        raise ValueError(f"Biến thể CCHEF không hợp lệ '{variant}'. Hỗ trợ: {VARIANT_NAMES}.")

    default_feats = list(VARIANT_ENABLED_FEATURES[variant])
    raw_enabled = cfg.get("enabled_features", cfg.get("enabled_components"))
    if raw_enabled is None:
        enabled = tuple(default_feats)
    else:
        enabled = tuple(dict.fromkeys(normalize_feature_key(x) for x in raw_enabled))
        if not enabled:
            raise ValueError("`enabled_features` không được rỗng.")

    raw_w = cfg.get("weights")
    weights_input: dict[str, float] = dict(DEFAULT_CCHEF_WEIGHTS)
    if isinstance(raw_w, Mapping):
        # Cho phép cấu hình chỉ truyền subset (VD H2: {"M": 0.6, "P": 0.2, "C": 0.2})
        if any(k in raw_w for k in enabled) or any(
            k in LEGACY_FEATURE_ALIASES and LEGACY_FEATURE_ALIASES[k] in enabled for k in raw_w
        ):
            weights_input = {k: 0.0 for k in FEATURE_NAMES}
            for k, v in raw_w.items():
                canon = normalize_feature_key(k)
                weights_input[canon] = float(v)
        else:
            for k, v in raw_w.items():
                weights_input[normalize_feature_key(k)] = float(v)

    w_norm_mode = str(
        cfg.get("weight_normalization", cfg.get("normalization", "sum_to_one"))
    ).strip().lower()
    if w_norm_mode == "weight_l1":
        w_norm_mode = "sum_to_one"

    effective_weights = normalize_weights(weights_input, enabled, normalization=w_norm_mode)
    scales = resolve_scales(cfg.get("scales"))

    phase_mods = deepcopy(DEFAULT_PHASE_MODIFIERS)
    if isinstance(cfg.get("phase_modifiers"), Mapping):
        for p_name, p_dict in cfg["phase_modifiers"].items():
            if p_name in phase_mods and isinstance(p_dict, Mapping):
                for k, v in p_dict.items():
                    phase_mods[p_name][normalize_feature_key(k)] = float(v)

    is_h6_plus = variant in ("H6", "H7") or ("T" in enabled)
    raw_co_lookahead = cfg.get("enable_compound_lookahead")
    raw_co_synergy = cfg.get("enable_co_synergy")
    enable_compound_lookahead = is_h6_plus if raw_co_lookahead is None else bool(raw_co_lookahead)
    enable_co_synergy = is_h6_plus if raw_co_synergy is None else bool(raw_co_synergy)

    return {
        "variant": variant,
        "enabled_features": enabled,
        "raw_weights": {k: float(weights_input.get(k, 0.0)) for k in FEATURE_NAMES},
        "effective_weights": effective_weights,
        "weight_normalization": w_norm_mode,
        "scales": scales,
        "phase_modifiers": phase_mods,
        "opening_material_threshold": float(cfg.get("opening_material_threshold", 0.82)),
        "endgame_material_threshold": float(cfg.get("endgame_material_threshold", 0.45)),
        "enable_compound_lookahead": enable_compound_lookahead,
        "enable_co_synergy": enable_co_synergy,
        "co_weight": float(cfg.get("co_weight", 0.08)),
    }


__all__ = [
    "DEFAULT_CCHEF_WEIGHTS",
    "DEFAULT_FEATURE_SCALES",
    "DEFAULT_PHASE_MODIFIERS",
    "FEATURE_NAMES",
    "VARIANT_ENABLED_FEATURES",
    "VARIANT_NAMES",
    "compute_observable_phase",
    "normalize_feature_key",
    "normalize_weights",
    "resolve_cchef_config",
    "resolve_scales",
]

