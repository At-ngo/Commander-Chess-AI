# packages/agents/evaluation/context.py
"""Bối cảnh lượng giá dùng chung `EvalContext` (bất biến, đối xứng hai phe, tối ưu tốc độ)."""

from __future__ import annotations

from dataclasses import dataclass, field

from commander_game_engine import rules
from commander_game_engine.board import Position
from commander_game_engine.game_state import GameState, Piece, PieceType, Player

from .material_table import piece_value

# Tầm tấn công tối đa theo từng (PieceType, is_heroic) để lọc hình học O(1)
# trước khi kiểm tra chính xác quan hệ uy hiếp.
MAX_THREAT_RANGE: dict[PieceType, tuple[int, int]] = {
    PieceType.COMMANDER: (1, 2),
    PieceType.INFANTRY: (1, 2),
    PieceType.ENGINEER: (1, 2),
    PieceType.ANTI_AIRCRAFT: (1, 2),
    PieceType.MILITIA: (1, 2),
    PieceType.TANK: (2, 3),
    PieceType.MISSILE: (2, 3),
    PieceType.ARTILLERY: (3, 4),
    PieceType.AIRCRAFT: (4, 5),
    PieceType.NAVY: (4, 5),
    PieceType.HEADQUARTERS: (0, 2),
}

_DEEP_CROSSERS = frozenset({
    PieceType.COMMANDER,
    PieceType.INFANTRY,
    PieceType.MILITIA,
    PieceType.TANK,
    PieceType.ENGINEER,
    PieceType.HEADQUARTERS,
})
_AA_UNIT_TYPES = frozenset({
    PieceType.ANTI_AIRCRAFT,
    PieceType.MISSILE,
    PieceType.NAVY,
})

# Tiền tính toàn bộ offset phòng không cho (PieceType, is_heroic) để tránh cấp phát lặp
_AA_OFFSETS_CACHE: dict[tuple[PieceType, bool], tuple[tuple[int, int], ...]] = {
    (pt, hero): tuple(rules.anti_air_offsets(pt, hero))
    for pt in PieceType
    for hero in (False, True)
}


def opponent_of(player: Player) -> Player:
    return Player.BLUE if player == Player.RED else Player.RED


def can_navy_occupy_xy(y: int, x: int) -> bool:
    """Hải quân chỉ đứng ở biển (x<=1), bờ biển (x=2) và dải sông (y=5,6 trừ ngầm đá x=5,7)."""
    if (y == 5 or y == 6) and (x == 5 or x == 7):
        return False
    return x <= 2 or y == 5 or y == 6


def is_navy_land_diagonal_xy(ay: int, ax: int, by: int, bx: int) -> bool:
    """Đường chéo cắt qua vùng đất liền giữa bờ biển và bờ sông (khớp `rules.is_navy_land_diagonal`)."""
    if ay == by or ax == bx:
        return False
    if (ax if ax < bx else bx) >= 2:
        if (ay >= 7 and by <= 6) or (by >= 7 and ay <= 6):
            return True
        if (ay <= 4 and by >= 5) or (by <= 4 and ay >= 5):
            return True
    return False


def grid_path_blocked(occ_grid: list[Piece | None], sy: int, sx: int, ty: int, tx: int) -> bool:
    """Kiểm tra có quân đứng giữa `(sy, sx)` và `(ty, tx)` không cấp phát tuple."""
    dy = ty - sy
    dx = tx - sx
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    cy = sy + step_y
    cx = sx + step_x
    while cy != ty or cx != tx:
        if occ_grid[cy * 11 + cx] is not None:
            return True
        cy += step_y
        cx += step_x
    return False


def grid_path_blocked_ignoring(
    occ_grid: list[Piece | None],
    sy: int,
    sx: int,
    ty: int,
    tx: int,
    ignore_y: int,
    ignore_x: int,
) -> bool:
    """Kiểm tra vật cản giữa `(sy, sx)` và `(ty, tx)` (bỏ qua tọa độ `ignore_y, ignore_x`)."""
    dy = ty - sy
    dx = tx - sx
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    cy = sy + step_y
    cx = sx + step_x
    while cy != ty or cx != tx:
        if (cy != ignore_y or cx != ignore_x) and occ_grid[cy * 11 + cx] is not None:
            return True
        cy += step_y
        cx += step_x
    return False


def navy_phase1_clear_grid(
    occ_grid: list[Piece | None],
    navy_owner: Player,
    sy: int,
    sx: int,
    ty: int,
    tx: int,
    *,
    allow_enemy_target_at_end: bool,
) -> bool:
    """Kiểm tra pha 1 Hải quân khớp 100% `rules._navy_phase1_clear` không cấp phát."""
    dy = ty - sy
    dx = tx - sx
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    ay, ax = sy, sx
    while True:
        by = ay + step_y
        bx = ax + step_x
        if is_navy_land_diagonal_xy(ay, ax, by, bx):
            return False
        if (by == 5 or by == 6) and (bx == 5 or bx == 7):
            return False
        if not (bx <= 2 or by == 5 or by == 6):
            return False
        if by == ty and bx == tx:
            break
        occ = occ_grid[by * 11 + bx]
        if occ is not None and (occ.piece_type == PieceType.NAVY or occ.owner != navy_owner):
            return False
        ay, ax = by, bx

    if not allow_enemy_target_at_end:
        occ_end = occ_grid[ty * 11 + tx]
        if occ_end is not None and occ_end.owner != navy_owner:
            return False
    return True


def movement_shape_ok(
    ptype: PieceType,
    hero: bool,
    sy: int,
    sx: int,
    ty: int,
    tx: int,
    capture: bool = False,
) -> bool:
    """Kiểm tra hướng/tầm khớp 100% `rules.movement_shape` không tạo `RuleResult`."""
    dy = ty - sy
    dx = tx - sx
    ady = -dy if dy < 0 else dy
    adx = -dx if dx < 0 else dx
    dist = ady if ady > adx else adx
    if dist == 0:
        return False
    is_orth = (ady == 0) or (adx == 0)
    if not (is_orth or ady == adx):
        return False

    if ptype == PieceType.COMMANDER:
        if hero:
            return dist <= 2
        if capture:
            return is_orth and dist <= 1
        return is_orth and dist <= 11
    if ptype in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIRCRAFT):
        if hero:
            return dist <= 2
        return is_orth and dist <= 1
    if ptype == PieceType.MILITIA:
        return dist <= (2 if hero else 1)
    if ptype == PieceType.TANK:
        if hero:
            return dist <= 3
        return is_orth and dist <= 2
    if ptype == PieceType.MISSILE:
        if hero:
            return dist <= (2 if not is_orth else 3)
        return dist <= (1 if not is_orth else 2)
    if ptype == PieceType.ARTILLERY:
        return dist <= (4 if hero else 3)
    if ptype == PieceType.AIRCRAFT:
        return dist <= (5 if hero else 4)
    if ptype == PieceType.NAVY:
        if hero:
            return dist <= 5
        return dist <= 4
    if ptype == PieceType.HEADQUARTERS:
        return hero and dist <= 2
    return False


def terrain_ok_grid(
    occ_grid: list[Piece | None],
    piece: Piece,
    sy: int,
    sx: int,
    ty: int,
    tx: int,
    capture: bool,
) -> bool:
    """Kiểm tra địa hình vượt sông & biển khớp 100% `rules._terrain_ok` (allow_sea_boarding=False)."""
    ptype = piece.piece_type
    if ptype == PieceType.NAVY:
        return navy_phase1_clear_grid(
            occ_grid, piece.owner, sy, sx, ty, tx, allow_enemy_target_at_end=capture
        )
    if tx < 2:
        return False
    if ptype == PieceType.AIRCRAFT:
        return True
    if ptype in _DEEP_CROSSERS or capture:
        return True

    # Với quân nặng đi (không ăn): không vượt sông sâu {5, 6} (trừ thẳng trên cầu ngầm x in {5, 7})
    dy = ty - sy
    dx = tx - sx
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    ay, ax = sy, sx
    while ay != ty or ax != tx:
        by = ay + step_y
        bx = ax + step_x
        if ((ay == 5 and by == 6) or (ay == 6 and by == 5)) and (ax if ax < bx else bx) >= 2:
            if ax != bx or (ax != 5 and ax != 7):
                return False
        ay, ax = by, bx
    return True


def _piece_threatens_fast(
    occ_grid: list[Piece | None],
    att: Piece,
    sy: int,
    sx: int,
    ty: int,
    tx: int,
    target_occ: Piece | None,
    is_sea_target: bool,
) -> bool:
    """Kiểm tra trực tiếp `att` tại `(sy, sx)` có uy hiếp `(ty, tx)` khớp `rules._piece_threatens_square`."""
    if att.carried_by is not None and is_sea_target and att.piece_type != PieceType.NAVY:
        return False

    dy = ty - sy
    dx = tx - sx
    ady = -dy if dy < 0 else dy
    adx = -dx if dx < 0 else dx
    is_orth = ady == 0 or adx == 0
    dist = ady if ady > adx else adx
    ptype = att.piece_type
    hero = att.is_heroic

    if ptype == PieceType.COMMANDER:
        if hero:
            return dist <= 2 and not grid_path_blocked(occ_grid, sy, sx, ty, tx)
        return is_orth and dist == 1

    if ptype in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIRCRAFT):
        if not hero:
            return is_orth and dist == 1
        return dist <= 2 and not grid_path_blocked(occ_grid, sy, sx, ty, tx)

    if ptype == PieceType.MILITIA:
        if not hero:
            return dist == 1
        return dist <= 2 and not grid_path_blocked(occ_grid, sy, sx, ty, tx)

    if ptype == PieceType.TANK:
        if not hero:
            if not is_orth or dist > 2:
                return False
        return not grid_path_blocked(occ_grid, sy, sx, ty, tx)

    if ptype == PieceType.MISSILE:
        max_r = (3 if hero else 2) if is_orth else (2 if hero else 1)
        return dist <= max_r

    if ptype == PieceType.ARTILLERY:
        return dist <= (4 if hero else 3)

    if ptype == PieceType.AIRCRAFT:
        return dist <= (5 if hero else 4)

    if ptype == PieceType.NAVY:
        if not can_navy_occupy_xy(sy, sx):
            return False
        if target_occ is not None and target_occ.piece_type == PieceType.NAVY:
            if dist > (5 if hero else 4):
                return False
            return navy_phase1_clear_grid(
                occ_grid, att.owner, sy, sx, ty, tx, allow_enemy_target_at_end=True
            )
        return dist <= (4 if hero else 3)

    if ptype == PieceType.HEADQUARTERS:
        return hero and dist <= 2 and not grid_path_blocked(occ_grid, sy, sx, ty, tx)

    return False


@dataclass
class EvalContext:
    """Tiền tính toán bản đồ bàn cờ, tọa độ gốc, vùng phòng không và quan hệ uy hiếp."""

    state: GameState
    pieces_by_player: dict[Player, list[Piece]]
    occ_map: dict[Position, Piece]
    occ_grid: list[Piece | None]
    origins: dict[str, Position]
    defended_by: dict[Player, frozenset[Position]]
    aa_danger_by: dict[Player, frozenset[Position]]
    aa_danger_grid: dict[Player, list[bool]]
    attackers_with_range: dict[Player, list[tuple[Piece, Position, int]]]
    cmd_piece: dict[Player, Piece | None]
    cmd_alive: dict[Player, bool]
    cmd_origin: dict[Player, Position | None]
    cmd_sheltered_hq: dict[Player, Piece | None]
    cmd_in_check: dict[Player, bool]
    root_threats: dict[str, list[Piece]] = field(default_factory=dict)
    root_defenders: dict[str, list[Piece]] = field(default_factory=dict)
    _attackers_cache: dict[tuple[Player, Position], list[Piece]] = field(default_factory=dict)
    _stack_value_cache: dict[str, float] = field(default_factory=dict)
    _desc_cache: dict[str, list[str]] = field(default_factory=dict)
    _defender_has_legal: dict[Player, bool] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: GameState, *, compute_aa: bool = True) -> "EvalContext":
        pieces_by_player: dict[Player, list[Piece]] = {Player.RED: [], Player.BLUE: []}
        occ_map: dict[Position, Piece] = {}
        occ_grid: list[Piece | None] = [None] * 132
        origins: dict[str, Position] = {}

        for p in state.pieces.values():
            pieces_by_player[p.owner].append(p)
            if p.carried_by is None and p.position is not None:
                pos = p.position
                occ_map[pos] = p
                occ_grid[pos[0] * 11 + pos[1]] = p
                origins[p.id] = pos

        for p in state.pieces.values():
            if p.id not in origins:
                ori = rules._origin(state, p)
                if ori is not None:
                    origins[p.id] = ori

        attackers_with_range: dict[Player, list[tuple[Piece, Position, int]]] = {
            Player.RED: [],
            Player.BLUE: [],
        }
        for side in (Player.RED, Player.BLUE):
            lst = attackers_with_range[side]
            for att in pieces_by_player[side]:
                max_r = MAX_THREAT_RANGE[att.piece_type][1 if att.is_heroic else 0]
                if max_r <= 0:
                    continue
                pos = origins.get(att.id)
                if pos is not None:
                    lst.append((att, pos, max_r))

        if compute_aa:
            defended_by: dict[Player, frozenset[Position]] = {}
            aa_danger_by: dict[Player, frozenset[Position]] = {}
            aa_danger_grid: dict[Player, list[bool]] = {}
            for side in (Player.RED, Player.BLUE):
                def_set: set[Position] = set()
                dng_grid = [False] * 132
                own_aa_self: list[Position] = []
                for p in pieces_by_player[side]:
                    if p.carried_by is not None or p.position is None:
                        continue
                    offs = _AA_OFFSETS_CACHE[(p.piece_type, p.is_heroic)]
                    if offs:
                        py, px = p.position
                        for dy, dx in offs:
                            ny = py + dy
                            nx = px + dx
                            if 0 <= ny < 12 and 0 <= nx < 11:
                                npos = (ny, nx)
                                def_set.add(npos)
                                dng_grid[ny * 11 + nx] = True
                    if p.piece_type in _AA_UNIT_TYPES:
                        own_aa_self.append(p.position)
                        dng_grid[p.position[0] * 11 + p.position[1]] = True
                def_fs = frozenset(def_set)
                defended_by[side] = def_fs
                aa_danger_by[side] = def_fs | frozenset(own_aa_self) if own_aa_self else def_fs
                aa_danger_grid[side] = dng_grid
        else:
            empty_fs: frozenset[Position] = frozenset()
            empty_grid = [False] * 132
            defended_by = {Player.RED: empty_fs, Player.BLUE: empty_fs}
            aa_danger_by = {Player.RED: empty_fs, Player.BLUE: empty_fs}
            aa_danger_grid = {Player.RED: empty_grid, Player.BLUE: empty_grid}

        cmd_piece: dict[Player, Piece | None] = {}
        cmd_alive: dict[Player, bool] = {}
        cmd_origin: dict[Player, Position | None] = {}
        cmd_sheltered_hq: dict[Player, Piece | None] = {}
        cmd_in_check: dict[Player, bool] = {}

        ctx = cls(
            state=state,
            pieces_by_player=pieces_by_player,
            occ_map=occ_map,
            occ_grid=occ_grid,
            origins=origins,
            defended_by=defended_by,
            aa_danger_by=aa_danger_by,
            aa_danger_grid=aa_danger_grid,
            attackers_with_range=attackers_with_range,
            cmd_piece=cmd_piece,
            cmd_alive=cmd_alive,
            cmd_origin=cmd_origin,
            cmd_sheltered_hq=cmd_sheltered_hq,
            cmd_in_check=cmd_in_check,
        )

        for side in (Player.RED, Player.BLUE):
            cmd = next(
                (p for p in pieces_by_player[side] if p.piece_type == PieceType.COMMANDER),
                None,
            )
            cmd_piece[side] = cmd
            cmd_alive[side] = cmd is not None
            if cmd is None:
                cmd_origin[side] = None
                cmd_sheltered_hq[side] = None
                cmd_in_check[side] = False
                continue

            cori = origins.get(cmd.id)
            cmd_origin[side] = cori
            sheltered_hq: Piece | None = None
            if cmd.carried_by is not None:
                carrier = state.pieces.get(cmd.carried_by)
                if carrier is not None and carrier.piece_type == PieceType.HEADQUARTERS and not carrier.is_heroic:
                    sheltered_hq = carrier
            cmd_sheltered_hq[side] = sheltered_hq

            if sheltered_hq is not None or cori is None:
                cmd_in_check[side] = False
            else:
                cmd_in_check[side] = bool(ctx.attackers_to_square(opponent_of(side), cori))

        return ctx

    def attackers_to_square(self, attacker_side: Player, target_pos: Position) -> list[Piece]:
        """Liệt kê mọi quân phe `attacker_side` có thể tấn công trực tiếp vào `target_pos` (có cache)."""
        key = (attacker_side, target_pos)
        cached = self._attackers_cache.get(key)
        if cached is not None:
            return cached

        ty, tx = target_pos
        is_sea_target = tx < 2
        target_occ = self.occ_grid[ty * 11 + tx]
        occ_grid = self.occ_grid
        hits: list[Piece] = []

        for att, (sy, sx), max_r in self.attackers_with_range[attacker_side]:
            if sy == ty and sx == tx:
                continue
            dy = ty - sy
            dx = tx - sx
            ady = -dy if dy < 0 else dy
            adx = -dx if dx < 0 else dx
            if ady > max_r or adx > max_r:
                continue
            if not (ady == 0 or adx == 0 or ady == adx):
                continue
            if _piece_threatens_fast(occ_grid, att, sy, sx, ty, tx, target_occ, is_sea_target):
                hits.append(att)

        self._attackers_cache[key] = hits
        return hits

    def ensure_root_threat_map(self) -> None:
        """Tính lười (lazy) bản đồ quân đứng trực tiếp trên bàn bị tấn công bởi địch & được bảo vệ bởi ta."""
        if self.root_threats:
            return
        occ_grid = self.occ_grid
        for pos, piece in self.occ_map.items():
            opp = opponent_of(piece.owner)
            self.root_threats[piece.id] = self.attackers_to_square(opp, pos)
            ty, tx = pos
            is_sea_target = tx < 2
            target_occ = occ_grid[ty * 11 + tx]
            defs: list[Piece] = []
            for ally, (sy, sx), max_r in self.attackers_with_range[piece.owner]:
                if ally.id == piece.id or (sy == ty and sx == tx):
                    continue
                dy = ty - sy
                dx = tx - sx
                ady = -dy if dy < 0 else dy
                adx = -dx if dx < 0 else dx
                if ady > max_r or adx > max_r or not (ady == 0 or adx == 0 or ady == adx):
                    continue
                if self._ally_guards_square_fast(ally, sy, sx, ty, tx, target_occ, is_sea_target):
                    defs.append(ally)
            self.root_defenders[piece.id] = defs

    def _ally_guards_square_fast(
        self,
        ally: Piece,
        sy: int,
        sx: int,
        ty: int,
        tx: int,
        target_occ: Piece | None,
        is_sea_target: bool,
    ) -> bool:
        """Kiểm tra nhanh đồng minh `ally` tại `(sy, sx)` có thể đánh trả vào `(ty, tx)` sau trao đổi."""
        ptype = ally.piece_type
        hero = ally.is_heroic
        if ptype == PieceType.HEADQUARTERS and not hero:
            return False
        if ally.carried_by is not None and is_sea_target and ptype != PieceType.NAVY:
            return False

        dy = ty - sy
        dx = tx - sx
        ady = -dy if dy < 0 else dy
        adx = -dx if dx < 0 else dx
        if (ady == 0 and adx == 0) or not (ady == 0 or adx == 0 or ady == adx):
            return False
        is_orth = ady == 0 or adx == 0
        dist = ady if ady > adx else adx

        if ptype == PieceType.MISSILE:
            max_r = (3 if hero else 2) if is_orth else (2 if hero else 1)
            return dist <= max_r
        if ptype == PieceType.ARTILLERY:
            return dist <= (4 if hero else 3)
        if ptype == PieceType.AIRCRAFT:
            return dist <= (5 if hero else 4)
        if ptype == PieceType.NAVY:
            if not can_navy_occupy_xy(sy, sx):
                return False
            if is_sea_target or (target_occ is not None and target_occ.piece_type == PieceType.NAVY):
                if dist > (5 if hero else 4):
                    return False
                return navy_phase1_clear_grid(
                    self.occ_grid, ally.owner, sy, sx, ty, tx, allow_enemy_target_at_end=True
                )
            return dist <= (4 if hero else 3)

        if ptype == PieceType.COMMANDER and not hero:
            return is_orth and dist == 1
        if ptype in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIRCRAFT):
            if (not hero and not is_orth) or dist > (2 if hero else 1):
                return False
        elif ptype == PieceType.MILITIA:
            if dist > (2 if hero else 1):
                return False
        elif ptype == PieceType.TANK:
            if (not hero and not is_orth) or dist > (3 if hero else 2):
                return False
        elif ptype in (PieceType.COMMANDER, PieceType.HEADQUARTERS):
            if not hero or dist > 2:
                return False

        return not grid_path_blocked(self.occ_grid, sy, sx, ty, tx)

    def _ally_guards_square(
        self,
        ally: Piece,
        start: Position,
        target_pos: Position,
        defender_owner: Player,
    ) -> bool:
        """Wrapper tương thích cho phép kiểm tra đồng minh giữ ô `target_pos`."""
        ty, tx = target_pos
        return self._ally_guards_square_fast(
            ally,
            start[0],
            start[1],
            ty,
            tx,
            self.occ_grid[ty * 11 + tx],
            tx < 2,
        )

    def descendants(self, piece_id: str) -> list[str]:
        """Lấy toàn bộ ID quân con/cháu bên trong `piece_id` (khử trùng lắp & phòng vòng lặp)."""
        cached = self._desc_cache.get(piece_id)
        if cached is not None:
            return cached
        res = rules.all_carried_ids(self.state, piece_id)
        self._desc_cache[piece_id] = res
        return res

    def stack_value(self, piece_id: str, *, include_hq_sheltered: bool = False) -> float:
        """Tính V_stack(u, s) = Σ V(v, s) cho {u} ∪ Desc(u, s)."""
        if not include_hq_sheltered and piece_id in self._stack_value_cache:
            return self._stack_value_cache[piece_id]
        root = self.state.pieces.get(piece_id)
        if root is None:
            return 0.0
        seen: set[str] = {piece_id}
        total = piece_value(root)
        for cid in self.descendants(piece_id):
            if cid in seen:
                continue
            seen.add(cid)
            child = self.state.pieces.get(cid)
            if child is None:
                continue
            if not include_hq_sheltered and root.piece_type == PieceType.HEADQUARTERS and not root.is_heroic and child.piece_type == PieceType.COMMANDER:
                continue
            total += piece_value(child)
        if not include_hq_sheltered:
            self._stack_value_cache[piece_id] = total
        return total


__all__ = [
    "EvalContext",
    "MAX_THREAT_RANGE",
    "can_navy_occupy_xy",
    "grid_path_blocked",
    "grid_path_blocked_ignoring",
    "is_navy_land_diagonal_xy",
    "movement_shape_ok",
    "navy_phase1_clear_grid",
    "opponent_of",
    "terrain_ok_grid",
]
