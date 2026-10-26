"""
Commander Chess AI — Agent Catalog Routes
Aligned with docs/API_CONTRACT.md Section 3.2
"""

from typing import Dict
from fastapi import APIRouter, HTTPException

from ..models.agent import AgentDTO, AgentListResponse, AgentDetailResponse
from ..models.enums import Side

router = APIRouter(prefix="/agents", tags=["Agents"])

# Initial agent registry
# Note: per AGENTS.md, agents are implemented by the Student in packages/agents.
# We expose registered descriptors clearly labeling their status.
REGISTERED_AGENTS: Dict[str, AgentDTO] = {
    "random_agent": AgentDTO(
        agent_id="random_agent",
        name="Random Tactical Agent",
        algorithm="RANDOM",
        version="0.1.0",
        description="Lựa chọn ngẫu nhiên đồng đều trong tập hợp các nước đi hợp lệ.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"seed": {"type": "integer", "default": 42}},
    ),
    "heuristic_agent": AgentDTO(
        agent_id="heuristic_agent",
        name="Rule-based Tactical Agent",
        algorithm="RULE_BASED",
        version="0.1.0",
        description="Ưu tiên tấn công mục tiêu giá trị cao và bảo vệ Tư lệnh.",
        status="IN_DEVELOPMENT",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"aggression": {"type": "number", "default": 1.0}},
    ),
    "minimax_agent": AgentDTO(
        agent_id="minimax_agent",
        name="Minimax Alpha-Beta Agent",
        algorithm="ALPHA_BETA",
        version="0.1.0",
        description="Duyệt cây trò chơi với tỉa cành Alpha-Beta và hàm đánh giá thế trận.",
        status="IN_DEVELOPMENT",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"max_depth": {"type": "integer", "default": 3}},
    ),
}


@router.get("", response_model=AgentListResponse)
def list_agents() -> AgentListResponse:
    """Liệt kê danh sách tất cả các tác tử AI được đăng ký trong hệ thống"""
    return AgentListResponse(agents=list(REGISTERED_AGENTS.values()))


@router.get("/{agent_id}", response_model=AgentDetailResponse)
def get_agent(agent_id: str) -> AgentDetailResponse:
    """Truy vấn thông tin chi tiết của một tác tử AI cụ thể"""
    agent = REGISTERED_AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Không tìm thấy tác tử với mã '{agent_id}'"},
        )
    return AgentDetailResponse(agent=agent)
