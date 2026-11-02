
# packages/commander_game_engine/game_state.py

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

from .board import Board, Position


class Player(Enum):
    """Hai phe tham gia trò chơi."""
    RED = "red"
    BLUE = "blue"


class PieceType(Enum):
    """11 loại quân Cờ Tư Lệnh."""
    COMMANDER = "commander"          # Tư lệnh
    INFANTRY = "infantry"            # Bộ binh
    MILITIA = "militia"              # Dân quân
    TANK = "tank"                    # Xe tăng
    ARTILLERY = "artillery"          # Pháo binh
    ANTI_AIRCRAFT = "anti_aircraft"  # Cao xạ
    MISSILE = "missile"              # Tên lửa
    AIRCRAFT = "aircraft"            # Máy bay
    NAVY = "navy"                    # Hải quân
    ENGINEER = "engineer"            # Công binh
    HEADQUARTERS = "headquarters"    # Sở chỉ huy


class GameStatus(Enum):
    """Trạng thái kết quả của ván đấu."""
    ONGOING = "ongoing"
    RED_WIN = "red_win"
    BLUE_WIN = "blue_win"
    DRAW = "draw"


@dataclass
class Piece:
    """Dữ liệu trạng thái của một quân cờ."""

    id: str                         # ID duy nhất
    piece_type: PieceType           # Loại quân
    owner: Player                   # Phe sở hữu
    position: Position | None       # Vị trí nếu đứng trên bàn cờ

    # Trạng thái vận chuyển
    carried_by: str | None = None   # ID phương tiện đang chở
    cargo: list[str] = field(default_factory=list)

    # Trạng thái quân anh hùng
    is_heroic: bool = False


@dataclass
class CompoundTurnState:
    """
    Dữ liệu của một lượt ghép đang thực hiện.

    Không kiểm tra tính hợp lệ của hành động.
    Không tự động chuyển lượt.
    """

    # ID phương tiện gốc của tổ hợp
    root_transport_id: str

    # Vị trí xuất phát ban đầu
    origin: Position

    # Số hành động đã thực hiện trong lượt ghép
    actions_used: int = 0

    # ID các quân đã thực hiện hành động
    acted_piece_ids: set[str] = field(default_factory=set)


@dataclass
class GameState:
    """Lưu trữ trạng thái của một ván Cờ Tư Lệnh."""

    # 1. Bàn cờ
    board: Board = field(default_factory=Board)

    # 2. Các quân cờ hiện còn trong ván
    pieces: dict[str, Piece] = field(default_factory=dict)

    # 3. Thông tin lượt chơi
    current_player: Player = Player.RED
    turn_number: int = 1

    # Tổng số hành động đã thực hiện
    action_count: int = 0

    # 4. Trạng thái lượt ghép
    compound_turn: CompoundTurnState | None = None

    # 5. Điểm số
    scores: dict[Player, int] = field(
        default_factory=lambda: {
            Player.RED: 0,
            Player.BLUE: 0,
        }
    )

    # 6. Thời gian đã sử dụng (giây)
    elapsed_time: dict[Player, float] = field(
        default_factory=lambda: {
            Player.RED: 0.0,
            Player.BLUE: 0.0,
        }
    )

    # 7. Trạng thái kết quả ván đấu
    game_status: GameStatus = GameStatus.ONGOING

    # ==================================================
    # TRUY XUẤT DỮ LIỆU
    # ==================================================

    def get_piece(self, piece_id: str) -> Piece | None:
        """Tìm quân cờ theo ID."""
        return self.pieces.get(piece_id)

    def get_piece_at(self, pos: Position) -> Piece | None:
        """Tìm quân đứng trực tiếp tại một giao điểm."""

        if not self.board.is_valid_position(pos):
            raise ValueError("Invalid position")

        for piece in self.pieces.values():
            if (
                piece.position == pos
                and piece.carried_by is None
            ):
                return piece

        return None

    def get_pieces_by_player(self, player: Player) -> list[Piece]:
        """Lấy danh sách quân hiện còn của một phe."""

        return [
            piece
            for piece in self.pieces.values()
            if piece.owner == player
        ]

    # ==================================================
    # THÊM DỮ LIỆU QUÂN CỜ
    # ==================================================

    def add_piece(self, piece: Piece) -> None:
        """Thêm một quân độc lập lên bàn cờ."""

        if piece.id in self.pieces:
            raise ValueError("Duplicate piece ID")

        if piece.position is None:
            raise ValueError("Piece must have a position")

        if piece.carried_by is not None:
            raise ValueError("Cannot directly place carried piece")

        if piece.cargo:
            raise ValueError(
                "Cannot directly add a piece with unresolved cargo"
            )

        if not self.board.is_valid_position(piece.position):
            raise ValueError("Invalid position")

        if self.get_piece_at(piece.position) is not None:
            raise ValueError("Position occupied")

        self.pieces[piece.id] = piece

    # ==================================================
    # SAO CHÉP TRẠNG THÁI
    # ==================================================

    def copy(self) -> "GameState":
        """
        Tạo bản sao độc lập của toàn bộ GameState.

        Phục vụ mô phỏng trạng thái trong Minimax, MCTS,
        Reinforcement Learning và các thuật toán khác.
        """
        return deepcopy(self)

    # ==================================================
    # KIỂM TRA TÍNH NHẤT QUÁN CỦA DỮ LIỆU
    # ==================================================

    def validate_structure(self) -> None:
        """
        Kiểm tra các bất biến cấu trúc dữ liệu.

        Không kiểm tra luật di chuyển, sức chứa phương tiện,
        khả năng tấn công hoặc điều kiện thắng thua.
        """

        occupied: set[Position] = set()

        # 1. Kiểm tra ID, vị trí và quan hệ vận chuyển
        for piece_id, piece in self.pieces.items():

            if piece_id != piece.id:
                raise ValueError("Piece dictionary key mismatch")

            if piece.carried_by is None:
                # Quân đứng trực tiếp trên bàn
                if piece.position is None:
                    raise ValueError(
                        f"Piece {piece_id} has no position"
                    )

                if not self.board.is_valid_position(piece.position):
                    raise ValueError(
                        f"Invalid position for {piece_id}"
                    )

                if piece.position in occupied:
                    raise ValueError(
                        f"Duplicate occupied position: {piece.position}"
                    )

                occupied.add(piece.position)

            else:
                # Quân được chở không chiếm giao điểm riêng
                if piece.position is not None:
                    raise ValueError(
                        f"Carried piece {piece_id} must have no position"
                    )

                carrier = self.pieces.get(piece.carried_by)

                if carrier is None:
                    raise ValueError(
                        f"Carrier not found for {piece_id}"
                    )

                if carrier.owner != piece.owner:
                    raise ValueError(
                        f"Carrier owner mismatch for {piece_id}"
                    )

                if piece_id not in carrier.cargo:
                    raise ValueError(
                        f"Transport relationship mismatch: {piece_id}"
                    )

            # Kiểm tra danh sách quân được chở
            if len(piece.cargo) != len(set(piece.cargo)):
                raise ValueError(
                    f"Duplicate cargo IDs in {piece_id}"
                )

            for cargo_id in piece.cargo:
                carried_piece = self.pieces.get(cargo_id)

                if carried_piece is None:
                    raise ValueError(
                        f"Cargo {cargo_id} not found"
                    )

                if carried_piece.carried_by != piece_id:
                    raise ValueError(
                        f"Invalid cargo relationship: {cargo_id}"
                    )

        # 2. Kiểm tra chu trình vận chuyển lồng nhau
        for piece_id in self.pieces:
            visited = set()
            current_id = piece_id

            while current_id is not None:
                if current_id in visited:
                    raise ValueError(
                        "Circular transport relationship"
                    )

                visited.add(current_id)

                current_piece = self.pieces[current_id]
                current_id = current_piece.carried_by

        # 3. Kiểm tra thông tin lượt
        if self.turn_number < 1:
            raise ValueError("Invalid turn number")

        if self.action_count < 0:
            raise ValueError("Invalid action count")

        # 4. Kiểm tra dữ liệu lượt ghép
        if self.compound_turn is not None:
            ct = self.compound_turn

            if ct.root_transport_id not in self.pieces:
                raise ValueError("Compound turn root not found")

            root = self.pieces[ct.root_transport_id]

            if root.owner != self.current_player:
                raise ValueError("Compound turn owner mismatch")

            if not self.board.is_valid_position(ct.origin):
                raise ValueError("Invalid compound turn origin")

            if ct.actions_used < 0 or ct.actions_used > 3:
                raise ValueError("Invalid compound action count")

            if len(ct.acted_piece_ids) > ct.actions_used:
                raise ValueError(
                    "Acted piece count exceeds action count"
                )

            for piece_id in ct.acted_piece_ids:
                if not isinstance(piece_id, str):
                    raise ValueError("Invalid acted piece ID")

        # 5. Kiểm tra điểm số và thời gian
        for player in Player:
            if player not in self.scores:
                raise ValueError("Missing player score")

            if player not in self.elapsed_time:
                raise ValueError("Missing player time")

            if self.elapsed_time[player] < 0:
                raise ValueError("Negative elapsed time")
