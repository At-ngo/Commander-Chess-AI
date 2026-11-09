/**
 * Commander Chess AI — REST API Client
 * Aligned with docs/API_CONTRACT.md
 */

import {
  GameStateDTO,
  ActionResponseDTO,
  AgentDTO,
  Side,
  GameMode,
  ActionType,
  Position,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  code: string;
  details?: any;

  constructor(code: string, message: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorInfo = data?.error || {
      code: `HTTP_${response.status}`,
      message: response.statusText || 'Unknown API Error',
    };
    throw new ApiError(errorInfo.code, errorInfo.message, errorInfo.details);
  }

  return data as T;
}

export const apiClient = {
  /**
   * Kiểm tra tình trạng hoạt động của API Backend
   */
  async checkHealth(): Promise<{ status: string; timestamp: string; uptime_seconds: number }> {
    return request('/health');
  },

  /**
   * Lấy thông tin phiên bản và chế độ hoạt động
   */
  async getVersion(): Promise<{ name: string; version: string; contract_version: string; mode: string }> {
    return request('/version');
  },

  /**
   * Lấy danh mục tác tử AI
   */
  async getAgents(): Promise<{ agents: AgentDTO[] }> {
    return request('/agents');
  },

  /**
   * Khởi tạo một phiên chơi mới
   */
  async createGame(params?: {
    mode?: GameMode;
    player_side?: Side;
    red_agent_id?: string | null;
    blue_agent_id?: string | null;
    time_limit_seconds?: number;
  }): Promise<GameStateDTO> {
    return request('/games', {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  },

  /**
   * Lấy trạng thái hiện tại của phiên chơi
   */
  async getGame(gameId: string): Promise<GameStateDTO> {
    return request(`/games/${gameId}`);
  },

  /**
   * Thực thi một hành động chiến thuật
   */
  async executeAction(
    gameId: string,
    action: {
      action_type: ActionType;
      piece_id: string;
      to_pos: Position;
      target_piece_id?: string | null;
      state_version: number;
      is_compound_action?: boolean;
    }
  ): Promise<ActionResponseDTO> {
    return request(`/games/${gameId}/actions`, {
      method: 'POST',
      body: JSON.stringify(action),
    });
  },

  /**
   * Chủ động kết thúc sớm lượt tổ hợp
   */
  async endTurn(gameId: string, stateVersion: number): Promise<GameStateDTO> {
    return request(`/games/${gameId}/end-turn`, {
      method: 'POST',
      body: JSON.stringify({ state_version: stateVersion }),
    });
  },

  /**
   * Kích hoạt nước đi của tác tử AI
   */
  async aiStep(gameId: string, timeBudgetMs = 1000): Promise<ActionResponseDTO> {
    return request(`/games/${gameId}/ai-step`, {
      method: 'POST',
      body: JSON.stringify({ time_budget_ms: timeBudgetMs }),
    });
  },

  /**
   * Đầu hàng ván đấu
   */
  async resignGame(gameId: string, side: Side): Promise<GameStateDTO> {
    return request(`/games/${gameId}/resign`, {
      method: 'POST',
      body: JSON.stringify({ side }),
    });
  },

  /**
   * Cầu hòa ván đấu
   */
  async drawGame(gameId: string, side: Side, action = 'OFFER'): Promise<GameStateDTO> {
    return request(`/games/${gameId}/draw`, {
      method: 'POST',
      body: JSON.stringify({ side, action }),
    });
  },
};
