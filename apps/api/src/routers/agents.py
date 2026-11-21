"""
Commander Chess AI — Agent Catalog Routes
Aligned with docs/API_CONTRACT.md Section 3.2
"""

from typing import Dict
from fastapi import APIRouter, HTTPException

from ..models.agent import AgentDTO, AgentListResponse, AgentDetailResponse
from ..models.enums import Side

router = APIRouter(prefix="/agents", tags=["Agents"])

# Authoritative agent registry
# Integrates student implementations in packages/agents:
# - RULE_BASED_AGENT: Ruleset_A (Check safety priority & high-value captures)
# - HEURISTIC_AGENT: CCHEF H6 best tuned variant (7 tactical features + CO lookahead)
# - RANDOM_AGENT: Uniform random baseline
# - MINIMAX_AGENT: Minimax depth 2 with candidate pruning k=20
REGISTERED_AGENTS: Dict[str, AgentDTO] = {
    "RULE_BASED_AGENT": AgentDTO(
        agent_id="RULE_BASED_AGENT",
        name="RULE-BASE AGENT",
        algorithm="RULE_BASED",
        version="1.0.0",
        description="Hệ luật chuyên gia Ruleset A: Ưu tiên bắt Tư lệnh, giải chiếu, ăn quân giá trị cao có lợi và bảo toàn lực lượng.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"ruleset": {"type": "string", "default": "Ruleset_A"}},
    ),
    "HEURISTIC_AGENT": AgentDTO(
        agent_id="HEURISTIC_AGENT",
        name="HEURISTIC_AGENT",
        algorithm="HEURISTIC_CCHEF",
        version="1.0.0",
        description="Hàm lượng giá CCHEF H6 tối ưu 7 đặc trưng chiến thuật quân sự và chuỗi hành động cõng quân phối hợp (CO).",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"variant": {"type": "string", "default": "H6"}},
    ),
    "RANDOM_AGENT": AgentDTO(
        agent_id="RANDOM_AGENT",
        name="RANDOM AGENT",
        algorithm="RANDOM",
        version="1.0.0",
        description="Lựa chọn ngẫu nhiên đồng đều trong tập hợp các nước đi hợp lệ.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"seed": {"type": "integer", "default": 2026}},
    ),
    "MINIMAX_AGENT": AgentDTO(
        agent_id="MINIMAX_AGENT",
        name="MINIMAX AGENT",
        algorithm="MINIMAX",
        version="1.0.0",
        description="Tìm kiếm đối kháng Minimax (depth=2, candidate pruning k=20) kết hợp hàm đánh giá H6.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"depth": {"type": "integer", "default": 2}},
    ),
    "ALPHA_BETA_AGENT": AgentDTO(
        agent_id="ALPHA_BETA_AGENT",
        name="ALPHA-BETA AGENT",
        algorithm="ALPHA_BETA",
        version="1.0.0",
        description="Tìm kiếm đối kháng Alpha-Beta Pruning (depth=2, move ordering) kết hợp hàm đánh giá H6 tối ưu.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"depth": {"type": "integer", "default": 2}, "move_ordering": {"type": "boolean", "default": True}},
    ),
    # Backwards-compatible aliases for legacy API clients and existing unit tests
    "random_agent": AgentDTO(
        agent_id="random_agent",
        name="Random Tactical Agent",
        algorithm="RANDOM",
        version="1.0.0",
        description="Lựa chọn ngẫu nhiên đồng đều trong tập hợp các nước đi hợp lệ.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"seed": {"type": "integer", "default": 42}},
    ),
    "heuristic_agent": AgentDTO(
        agent_id="heuristic_agent",
        name="HEURISTIC_AGENT",
        algorithm="HEURISTIC_CCHEF",
        version="1.0.0",
        description="Hàm lượng giá CCHEF H6 tối ưu 7 đặc trưng chiến thuật quân sự và chuỗi hành động cõng quân phối hợp (CO).",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"variant": {"type": "string", "default": "H6"}},
    ),
    "minimax_agent": AgentDTO(
        agent_id="minimax_agent",
        name="Minimax Alpha-Beta Agent",
        algorithm="ALPHA_BETA",
        version="1.0.0",
        description="Duyệt cây trò chơi với tỉa cành Alpha-Beta và hàm đánh giá thế trận.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"max_depth": {"type": "integer", "default": 2}},
    ),
    "alphabeta_agent": AgentDTO(
        agent_id="alphabeta_agent",
        name="Alpha-Beta Pruning Agent",
        algorithm="ALPHA_BETA",
        version="1.0.0",
        description="Tìm kiếm đối kháng Alpha-Beta Pruning (depth=2, move ordering) kết hợp hàm đánh giá H6 tối ưu.",
        status="READY",
        supported_sides=[Side.RED, Side.BLUE],
        config_schema={"depth": {"type": "integer", "default": 2}},
    ),
}


@router.get("", response_model=AgentListResponse)
def list_agents() -> AgentListResponse:
    """Liệt kê danh sách tất cả các tác tử AI được đăng ký trong hệ thống"""
    # Return unique agents preferring canonical uppercase IDs
    canonical_keys = ["RULE_BASED_AGENT", "HEURISTIC_AGENT", "RANDOM_AGENT", "MINIMAX_AGENT", "ALPHA_BETA_AGENT", "random_agent"]
    seen = set()
    result = []
    for k in list(REGISTERED_AGENTS.keys()):
        dto = REGISTERED_AGENTS[k]
        if dto.agent_id not in seen:
            seen.add(dto.agent_id)
            result.append(dto)
    return AgentListResponse(agents=result)


@router.get("/{agent_id}", response_model=AgentDetailResponse)
def get_agent(agent_id: str) -> AgentDetailResponse:
    """Truy vấn thông tin chi tiết của một tác tử AI cụ thể"""
    agent = REGISTERED_AGENTS.get(agent_id)
    if not agent:
        # Case-insensitive lookup
        for k, v in REGISTERED_AGENTS.items():
            if k.lower() == agent_id.lower() or v.name.lower() == agent_id.lower():
                agent = v
                break
    if not agent:
        raise HTTPException(
            status_code=404,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Không tìm thấy tác tử với mã '{agent_id}'"},
        )
    return AgentDetailResponse(agent=agent)
