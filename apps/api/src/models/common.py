"""
Commander Chess AI — Common Data Models
Aligned with docs/API_CONTRACT.md Section 2.2
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Position(BaseModel):
    """
    Tọa độ giao điểm trên bàn cờ Cờ Tư Lệnh (11 cột x 12 dòng).
    x: 0..10 (hoành độ)
    y: 0..11 (tung độ)
    """
    x: int = Field(..., ge=0, le=10, description="Hoành độ x (0..10)")
    y: int = Field(..., ge=0, le=11, description="Tung độ y (0..11)")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Mã lỗi chuẩn (e.g. GAME_NOT_FOUND, ILLEGAL_ACTION)")
    message: str = Field(..., description="Mô tả lỗi dễ hiểu cho người dùng")
    details: Optional[Dict[str, Any]] = Field(None, description="Chi tiết gỡ lỗi bổ sung")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Trạng thái dịch vụ")
    timestamp: str = Field(..., description="Thời điểm kiểm tra (ISO 8601)")
    uptime_seconds: float = Field(..., description="Thời gian hoạt động (giây)")


class VersionResponse(BaseModel):
    name: str = Field("commander-chess-api", description="Tên dịch vụ API")
    version: str = Field("1.0.0", description="Phiên bản phát hành")
    contract_version: str = Field("1.0", description="Phiên bản API Contract")
    rules_version: str = Field("1.0", description="Phiên bản luật chơi")
    mode: str = Field("TOTAL_FORCE", description="Chế độ chiến tranh tổng lực")
