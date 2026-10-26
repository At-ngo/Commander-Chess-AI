"""
Commander Chess AI — Agent Models
Aligned with docs/API_CONTRACT.md Section 3.2
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import Side


class AgentDTO(BaseModel):
    agent_id: str = Field(..., description="Mã định danh tác tử (e.g. random_agent, heuristic_agent)")
    name: str = Field(..., description="Tên hiển thị của tác tử")
    algorithm: str = Field(..., description="Thuật toán (RANDOM, RULE_BASED, MINIMAX, ALPHA_BETA, MCTS)")
    version: str = Field(..., description="Phiên bản tác tử")
    description: str = Field(..., description="Mô tả chiến lược tác chiến")
    status: str = Field("READY", description="'READY', 'EXPERIMENTAL', hoặc 'IN_DEVELOPMENT'")
    supported_sides: List[Side] = Field(default_factory=lambda: [Side.RED, Side.BLUE])
    config_schema: Optional[Dict[str, Any]] = Field(None, description="Đặc tả cấu hình tham số có thể chỉnh")


class AgentListResponse(BaseModel):
    agents: List[AgentDTO]


class AgentDetailResponse(BaseModel):
    agent: AgentDTO
