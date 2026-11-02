
# packages/commander_game_engine/actions.py

from dataclasses import dataclass, field
from enum import Enum

from .board import Position


class ActionType(Enum):
    """Các loại hành động đơn mà một quân cờ có thể thực hiện."""

    MOVE = "move"          # Di chuyển đến vị trí mới
    CAPTURE = "capture"    # Ăn quân địch và chiếm vị trí
    BOMB = "bomb"          # Thả bom không chiếm vị trí
    BOMBARD = "bombard"    # Pháo kích không chiếm vị trí
    BOARD = "board"        # Đưa quân lên phương tiện vận chuyển
    PICKUP = "pickup"      # Phương tiện chủ động đến đón quân


class TurnCommandType(Enum):
    """Các lệnh điều khiển lượt chơi, không phải nước đi của quân."""

    CONFIRM_DEPLOYMENT = "confirm_deployment"  # Xác nhận triển khai tổ hợp
    END_TURN = "end_turn"                      # Yêu cầu kết thúc lượt


@dataclass(frozen=True)
class AtomicAction:
    """
    Biểu diễn một hành động đơn của một quân cờ.

    Chỉ lưu thông tin hành động được yêu cầu.
    Không kiểm tra luật hoặc thay đổi GameState.
    """

    action_type: ActionType             # Loại hành động
    piece_id: str                       # ID quân thực hiện hành động

    start: Position | None = None       # Vị trí xuất phát
    end: Position | None = None         # Vị trí đích hoặc vị trí mục tiêu

    target_piece_id: str | None = None  # ID quân bị tấn công
    carrier_id: str | None = None       # ID phương tiện được chọn để lên
    passenger_id: str | None = None     # ID quân được đón


@dataclass
class CompoundAction:
    """
    Biểu diễn một chuỗi hành động trong lượt tổ hợp.

    Các hành động được lưu theo thứ tự thực hiện.
    Không tự kiểm tra giới hạn hành động hay luật vận chuyển.
    """

    root_transport_id: str              # ID phương tiện gốc của tổ hợp

    actions: list[AtomicAction] = field(
        default_factory=list
    )                                    # Danh sách hành động theo thứ tự

    remaining_transport: dict[str, list[str]] = field(
        default_factory=dict
    )
    # Cấu hình vận chuyển dự kiến sau khi triển khai
    # Key: ID phương tiện
    # Value: Danh sách ID quân tiếp tục được phương tiện đó chở


@dataclass(frozen=True)
class TurnCommand:
    """
    Biểu diễn yêu cầu điều khiển lượt chơi.

    Không trực tiếp di chuyển quân hoặc cập nhật GameState.
    """

    command_type: TurnCommandType       # Loại lệnh điều khiển lượt
