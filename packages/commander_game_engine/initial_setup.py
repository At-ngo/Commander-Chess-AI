# packages/commander_game_engine/initial_setup.py
"""Tạo đội hình xuất phát Cờ Tư Lệnh gồm 38 quân (19 quân mỗi phe).

Nguồn tọa độ: GAME_RULES_PHAN_1_TOA_DO.md, mục 1.3.
Quy ước vị trí: (y, x), y từ 0 đến 11 và x từ 0 đến 10.

Module này chỉ khởi tạo dữ liệu bàn cờ, KHÔNG kiểm tra nước đi hoặc
thực thi hành động. Không tự suy diễn cách xếp quân từ tính đối xứng.
"""

from __future__ import annotations

from collections import Counter

from .board import Board, Position
from .game_state import GameState, Piece, PieceType, Player


# Tọa độ được chép nguyên theo bảng bố trí ban đầu trong tài liệu.
# Thứ tự từng tuple giữ ổn định để sinh ID quân nhất quán.
INITIAL_POSITIONS: dict[Player, dict[PieceType, tuple[Position, ...]]] = {
    Player.RED: {
        PieceType.COMMANDER: ((0, 6),),
        PieceType.AIRCRAFT: ((1, 4), (1, 8)),
        PieceType.HEADQUARTERS: ((1, 5), (1, 7)),
        PieceType.MISSILE: ((2, 6),),
        PieceType.ARTILLERY: ((2, 3), (2, 9)),
        PieceType.ANTI_AIRCRAFT: ((3, 4), (3, 8)),
        PieceType.TANK: ((3, 5), (3, 7)),
        PieceType.INFANTRY: ((4, 2), (4, 10)),
        PieceType.ENGINEER: ((4, 3), (4, 9)),
        PieceType.MILITIA: ((4, 6),),
        PieceType.NAVY: ((1, 1), (3, 2)),
    },
    Player.BLUE: {
        PieceType.COMMANDER: ((11, 6),),
        PieceType.AIRCRAFT: ((10, 4), (10, 8)),
        PieceType.HEADQUARTERS: ((10, 5), (10, 7)),
        PieceType.MISSILE: ((9, 6),),
        PieceType.ARTILLERY: ((9, 3), (9, 9)),
        PieceType.ANTI_AIRCRAFT: ((8, 4), (8, 8)),
        PieceType.TANK: ((8, 5), (8, 7)),
        PieceType.INFANTRY: ((7, 2), (7, 10)),
        PieceType.ENGINEER: ((7, 3), (7, 9)),
        PieceType.MILITIA: ((7, 6),),
        PieceType.NAVY: ((10, 1), (8, 2)),
    },
}

# Số lượng chính thức từng loại quân cho mỗi phe.
EXPECTED_COUNTS: dict[PieceType, int] = {
    PieceType.COMMANDER: 1,
    PieceType.INFANTRY: 2,
    PieceType.TANK: 2,
    PieceType.MILITIA: 1,
    PieceType.ENGINEER: 2,
    PieceType.ARTILLERY: 2,
    PieceType.ANTI_AIRCRAFT: 2,
    PieceType.MISSILE: 1,
    PieceType.AIRCRAFT: 2,
    PieceType.NAVY: 2,
    PieceType.HEADQUARTERS: 2,
}


def validate_initial_positions(board: Board | None = None) -> None:
    """Kiểm tra đủ 38 quân, đúng số lượng, đúng tọa độ và không trùng vị trí.

    Raise:
        ValueError: Khi bảng bố trí ban đầu có dữ liệu không hợp lệ.
    """
    board = board if board is not None else Board()
    if set(INITIAL_POSITIONS) != {Player.RED, Player.BLUE}:
        raise ValueError("Bảng bố trí phải có đúng hai phe Đỏ và Xanh.")

    occupied: dict[Position, str] = {}
    for player in (Player.RED, Player.BLUE):
        formation = INITIAL_POSITIONS[player]
        if set(formation) != set(EXPECTED_COUNTS):
            raise ValueError(f"Thiếu hoặc thừa loại quân của phe {player.value}.")

        count = 0
        for piece_type, expected in EXPECTED_COUNTS.items():
            positions = formation[piece_type]
            if len(positions) != expected:
                raise ValueError(
                    f"Phe {player.value}, quân {piece_type.value}: "
                    f"cần {expected} quân, hiện có {len(positions)}."
                )
            for pos in positions:
                if not board.is_valid_position(pos):
                    raise ValueError(f"Tọa độ ngoài bàn cờ: {pos}.")
                if pos in occupied:
                    raise ValueError(
                        f"Tọa độ {pos} bị trùng: {occupied[pos]} "
                        f"và {player.value}/{piece_type.value}."
                    )
                occupied[pos] = f"{player.value}/{piece_type.value}"
                count += 1

        if count != 19:
            raise ValueError(f"Phe {player.value} phải có 19 quân, hiện có {count}.")

    if len(occupied) != 38:
        raise ValueError("Đội hình khởi đầu phải có đúng 38 giao điểm đặt quân.")


def create_initial_pieces(board: Board | None = None) -> dict[str, Piece]:
    """Tạo 38 đối tượng Piece với ID duy nhất và tọa độ xuất phát.

    ID có dạng red_infantry_1, blue_navy_2, ...
    Tại thời điểm bắt đầu: không quân nào được chở, không quân Anh hùng.
    """
    board = board if board is not None else Board()
    validate_initial_positions(board)

    pieces: dict[str, Piece] = {}
    for player in (Player.RED, Player.BLUE):
        for piece_type, positions in INITIAL_POSITIONS[player].items():
            for index, position in enumerate(positions, start=1):
                piece_id = f"{player.value}_{piece_type.value}_{index}"
                pieces[piece_id] = Piece(
                    id=piece_id,
                    piece_type=piece_type,
                    owner=player,
                    position=position,
                )
    return pieces


def create_initial_state() -> GameState:
    """Khởi tạo ván mới với bàn cờ mặc định và Đỏ đi trước.

    GameState cung cấp các giá trị mặc định khác như điểm/lượt/trạng thái ván
    theo định nghĩa hiện có; không tự thêm trường lạ vào model.
    """
    board = Board()
    pieces = create_initial_pieces(board)
    state = GameState(
        board=board,
        pieces=pieces,
        current_player=Player.RED,
    )
    # Nếu GameState có hàm kiểm tra cấu trúc, tận dụng để soát dữ liệu.
    validate = getattr(state, "validate_structure", None)
    if callable(validate):
        validate()
    return state


def get_initial_position(player: Player, piece_type: PieceType, index: int = 1) -> Position:
    """Lấy tọa độ của quân thứ index (đánh số từ 1) thuộc một loại và một phe."""
    positions = INITIAL_POSITIONS[player][piece_type]
    if not 1 <= index <= len(positions):
        raise IndexError(
            f"{player.value}/{piece_type.value} không có quân thứ {index}."
        )
    return positions[index - 1]


__all__ = [
    "INITIAL_POSITIONS",
    "EXPECTED_COUNTS",
    "validate_initial_positions",
    "create_initial_pieces",
    "create_initial_state",
    "get_initial_position",
]
