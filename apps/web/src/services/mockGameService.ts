/**
 * Commander Chess AI — Authoritative Mock Game Service
 * 
 * [MOCK ADAPTER - FOR FRONTEND UI PREVIEW ONLY]
 * -------------------------------------------------------------
 * NOTE: As mandated by AGENTS.md, the authoritative game rules,
 * state validation, and legal move generation belong SOLELY to
 * packages/game-engine (managed by the Project Owner).
 * 
 * This service implements the exact movement and attack rules
 * specified in docs/GAME_RULES.md and docs/BUG_REPORT.md:
 * - Sở chỉ huy: Vật cản đứng yên, không có nước đi.
 * - Dân quân: Đi và ăn 8 hướng (ngang/dọc/chéo) 1 đoạn.
 * - Bộ binh / Công binh / Cao xạ: Đi và ăn ngang/dọc 1 đoạn.
 * - Xe tăng: Đi và ăn ngang/dọc 1–2 đoạn (bị cản bởi quân ở giữa).
 * - Tên lửa: Đi và ăn ngang/dọc 1–2 đoạn, chéo 1 đoạn.
 * - Pháo binh: Đi thường 8 hướng 1–3 đoạn (bị cản); Bắn ăn quân 8 hướng
 *   1–3 đoạn XUYÊN QUA QUÂN CẢN.
 * - Máy bay: Đi và ăn 8 hướng 1–4 đoạn, BAY VÀ ĂN XUYÊN QUÂN.
 *   Ăn máy bay địch bắt buộc thế chỗ; ăn quân mặt đất/mặt nước được ném bom
 *   (không thế chỗ) hoặc oanh tạc (thế chỗ).
 * - Tư lệnh: Đi ngang/dọc không giới hạn đoạn; ăn ngang/dọc 1 đoạn.
 * - Hải quân: Đi và ăn trên biển/sông 8 hướng 1–4 đoạn.
 */

import { PieceState, LegalAction, ActionType, GameEvent } from '../types';
import { formatCoordinateNotation } from '../utils/coordinates';
import { PIECE_VIETNAMESE_NAMES, PIECE_NOTATION_SYMBOL } from '../utils/assets';

export const PIECE_SCORES: Record<string, number> = {
  COMMANDER: 50,
  HEADQUARTERS: 100,
  AIRCRAFT: 40,
  NAVY: 80,
  MISSILE: 20,
  TANK: 30,
  ARTILLERY: 30,
  ANTI_AIR: 10,
  ENGINEER: 10,
  INFANTRY: 10,
  MILITIA: 10,
};

const ORTHOGONAL: [number, number][] = [
  [0, 1],   // Bắc (lên)
  [0, -1],  // Nam (xuống)
  [-1, 0],  // Tây (trái)
  [1, 0],   // Đông (phải)
];

const DIAGONAL: [number, number][] = [
  [1, 1],
  [1, -1],
  [-1, 1],
  [-1, -1],
];

const ALL_8: [number, number][] = [...ORTHOGONAL, ...DIAGONAL];

function isInsideBoard(x: number, y: number): boolean {
  return x >= 0 && x <= 10 && y >= 0 && y <= 11;
}

function isSeaSquare(x: number): boolean {
  return x <= 1; // Cột 0 và 1 là biển sâu
}

/**
 * Generate legal actions matching exact game rules
 */
export function getMockLegalActions(
  selectedPiece: PieceState,
  allPieces: PieceState[]
): LegalAction[] {
  if (!selectedPiece.is_alive) return [];

  // 1. Sở chỉ huy là vật cản cố định, đứng yên, không có nước đi
  if (selectedPiece.type === 'HEADQUARTERS') {
    return [];
  }

  const actions: LegalAction[] = [];
  const { x, y } = selectedPiece.position;
  const side = selectedPiece.side;
  const fromNot = formatCoordinateNotation({ x, y });
  const pieceName = PIECE_VIETNAMESE_NAMES[selectedPiece.type] || selectedPiece.type;
  const pieceSymbol = PIECE_NOTATION_SYMBOL[selectedPiece.type] || selectedPiece.type;

  const getPieceAt = (px: number, py: number) =>
    allPieces.find((p) => p.is_alive && p.position.x === px && p.position.y === py);

  const canOccupySquare = (nx: number, _ny: number): boolean => {
    // Quân hải quân chỉ đi biển (x<=2) hoặc dải sông (y=5,6)
    if (selectedPiece.type === 'NAVY') {
      return nx <= 2 || _ny === 5 || _ny === 6;
    }
    // Máy bay và Tên lửa bay qua cả biển và đất
    if (selectedPiece.type === 'AIRCRAFT' || selectedPiece.type === 'MISSILE') {
      return true;
    }
    // Các quân bộ binh không được đứng trên biển sâu
    return !isSeaSquare(nx);
  };

  // Helper tạo action MOVE theo chuẩn docs/MOVE_NOTATION.md: <QUÂN> [y ; x] _ [y ; x]
  const pushMove = (nx: number, ny: number) => {
    const toNot = formatCoordinateNotation({ x: nx, y: ny });
    actions.push({
      action_id: `m_${selectedPiece.piece_id}_${nx}_${ny}`,
      action_type: 'MOVE',
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { x: nx, y: ny },
      target_piece_id: null,
      notation: `${pieceSymbol} ${fromNot} _ ${toNot}`,
      description: `${pieceName} tiến đến ${toNot}`,
    });
  };

  // Helper tạo action CAPTURE theo chuẩn docs/MOVE_NOTATION.md:
  // Thế chỗ: <QUÂN> [nguồn] @ <QUÂN_ĐỊCH> [đích]
  // Không thế chỗ: <QUÂN> [nguồn] _@_ <QUÂN_ĐỊCH> [đích]
  const pushCapture = (
    nx: number,
    ny: number,
    target: PieceState,
    actType: ActionType,
    labelSuffix = ''
  ) => {
    const toNot = formatCoordinateNotation({ x: nx, y: ny });
    const targetSymbol = PIECE_NOTATION_SYMBOL[target.type] || target.type;
    const enemyName = PIECE_VIETNAMESE_NAMES[target.type] || target.type;
    const isStand = actType === 'CAPTURE_STAND';
    const actionSymbol = isStand ? '_@_' : '@';
    actions.push({
      action_id: `c_${selectedPiece.piece_id}_${target.piece_id}_${actType}`,
      action_type: actType,
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { x: nx, y: ny },
      target_piece_id: target.piece_id,
      notation: `${pieceSymbol} ${fromNot} ${actionSymbol} ${targetSymbol} ${toNot}`,
      description: `${pieceName} ${
        isStand ? 'ném bom/bắn hỏa lực diệt' : 'tấn công bắt'
      } ${enemyName} tại ${toNot}${labelSuffix}`,
    });
  };

  // =========================================================================
  // 2. DÂN QUÂN (MILITIA): Đi và ăn ngang / dọc / chéo 1 đoạn (ALL_8, range 1)
  // =========================================================================
  if (selectedPiece.type === 'MILITIA') {
    for (const [dx, dy] of ALL_8) {
      const nx = x + dx;
      const ny = y + dy;
      if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) continue;

      const occ = getPieceAt(nx, ny);
      if (!occ) {
        pushMove(nx, ny);
      } else if (occ.side !== side) {
        pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
      }
    }
    return actions;
  }

  // =========================================================================
  // 3. BỘ BINH, CÔNG BINH, CAO XẠ: Đi và ăn ngang / dọc 1 đoạn (ORTHOGONAL, range 1)
  // =========================================================================
  if (
    selectedPiece.type === 'INFANTRY' ||
    selectedPiece.type === 'ENGINEER' ||
    selectedPiece.type === 'ANTI_AIR'
  ) {
    for (const [dx, dy] of ORTHOGONAL) {
      const nx = x + dx;
      const ny = y + dy;
      if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) continue;

      const occ = getPieceAt(nx, ny);
      if (!occ) {
        pushMove(nx, ny);
      } else if (occ.side !== side) {
        pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
      }
    }
    return actions;
  }

  // =========================================================================
  // 4. XE TĂNG (TANK): Đi và ăn ngang / dọc 1–2 đoạn (bị cản bởi quân ở giữa)
  // =========================================================================
  if (selectedPiece.type === 'TANK') {
    for (const [dx, dy] of ORTHOGONAL) {
      for (let step = 1; step <= 2; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
          }
          break; // Bị cản, không đi tiếp step 2
        }
      }
    }
    return actions;
  }

  // =========================================================================
  // 5. TÊN LỬA (MISSILE): Đi và ăn ngang/dọc 1–2 đoạn, chéo 1 đoạn
  // =========================================================================
  if (selectedPiece.type === 'MISSILE') {
    // Ngang/dọc 1–2 đoạn
    for (const [dx, dy] of ORTHOGONAL) {
      for (let step = 1; step <= 2; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
          }
          break;
        }
      }
    }
    // Chéo 1 đoạn
    for (const [dx, dy] of DIAGONAL) {
      const nx = x + dx;
      const ny = y + dy;
      if (!isInsideBoard(nx, ny)) continue;

      const occ = getPieceAt(nx, ny);
      if (!occ) {
        pushMove(nx, ny);
      } else if (occ.side !== side) {
        pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
      }
    }
    return actions;
  }

  // =========================================================================
  // 6. PHÁO BINH (ARTILLERY): Đi và ăn ngang / dọc / chéo 1–3 đoạn
  // - Di chuyển: Bị cản bởi quân ở giữa (không đi xuyên).
  // - Bắn ăn quân: ĐƯỢC BẮN XUYÊN QUA QUÂN CẢN trong tầm 1–3 đoạn!
  // =========================================================================
  if (selectedPiece.type === 'ARTILLERY') {
    for (const [dx, dy] of ALL_8) {
      // Nhánh 1: Di chuyển ô trống (bị cản)
      for (let step = 1; step <= 3; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          break; // Có quân cản, không đi ô trống phía sau được
        }
      }

      // Nhánh 2: Bắn ăn quân (BẮN XUYÊN QUÂN CẢN trong tầm 3 đoạn)
      for (let step = 1; step <= 3; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (occ && occ.side !== side) {
          // Bắn tàu ngoài biển: không thế chỗ
          if (isSeaSquare(nx)) {
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (bắn pháo bờ biển)');
          } else {
            // Trên bộ: có thể ăn thế chỗ hoặc bắn hỏa lực tại chỗ
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (thế chỗ)');
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (bắn hỏa lực tại chỗ)');
          }
        }
      }
    }
    return actions;
  }

  // =========================================================================
  // 7. MÁY BAY (AIRCRAFT): Đi và ăn ngang / dọc / chéo 1–4 đoạn
  // - Có thể bay và ăn XUYÊN QUÂN (không bị cản bởi quân ở giữa).
  // - Ăn máy bay địch: BẮT BUỘC THẾ CHỖ.
  // - Ăn quân khác: NÉM BOM (không thế chỗ) hoặc OANH TẠC (thế chỗ).
  // =========================================================================
  if (selectedPiece.type === 'AIRCRAFT') {
    for (const [dx, dy] of ALL_8) {
      for (let step = 1; step <= 4; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          // Bay xuyên qua quân khác đến ô trống
          pushMove(nx, ny);
        } else if (occ.side !== side) {
          // Gặp quân địch:
          if (occ.type === 'AIRCRAFT') {
            // Không chiến với máy bay địch: BẮT BUỘC THẾ CHỖ
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (không chiến bắt buộc thế chỗ)');
          } else {
            // Ăn quân mặt đất / mặt nước: Ném bom (không thế chỗ) hoặc Thế chỗ
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' 💣 (ném bom tại chỗ)');
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' 🎯 (oanh tạc thế chỗ)');
          }
        }
        // Quân cùng phe: Máy bay bay xuyên qua, tiếp tục vòng lặp step tiếp theo!
      }
    }
    return actions;
  }

  // =========================================================================
  // 8. TƯ LỆNH (COMMANDER):
  // - Đi thường: Ngang / dọc không giới hạn đoạn đến khi gặp vật cản.
  // - Ăn quân: Ngang / dọc 1 đoạn (thế chỗ).
  // =========================================================================
  if (selectedPiece.type === 'COMMANDER') {
    for (const [dx, dy] of ORTHOGONAL) {
      for (let step = 1; step <= 11; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          // Ăn quân chỉ trong tầm 1 đoạn
          if (step === 1 && occ.side !== side) {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
          }
          break; // Bị cản
        }
      }
    }
    return actions;
  }

  // =========================================================================
  // 9. HẢI QUÂN (NAVY): Đi và ăn trên biển / sông 8 hướng 1–4 đoạn
  // =========================================================================
  if (selectedPiece.type === 'NAVY') {
    for (const [dx, dy] of ALL_8) {
      for (let step = 1; step <= 4; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
          }
          break;
        }
      }
    }
    return actions;
  }

  return actions;
}

/**
 * Apply action and update board state
 */
export function applyMockAction(
  action: LegalAction,
  pieces: PieceState[]
): {
  nextPieces: PieceState[];
  event: GameEvent;
  capturedPiece: PieceState | null;
} {
  const actor = pieces.find((p) => p.piece_id === action.piece_id);
  let captured: PieceState | null = null;
  const scoreDelta: { RED: number; BLUE: number } = { RED: 0, BLUE: 0 };

  const nextPieces = pieces.map((p) => {
    // Nếu quân này bị tiêu diệt
    if (action.target_piece_id && p.piece_id === action.target_piece_id) {
      captured = { ...p, is_alive: false };
      const scoreValue = PIECE_SCORES[p.type] || 10;
      if (actor && actor.side === 'RED') {
        scoreDelta.RED += scoreValue;
      } else if (actor && actor.side === 'BLUE') {
        scoreDelta.BLUE += scoreValue;
      }
      return { ...p, is_alive: false };
    }

    // Nếu là quân thực hiện hành động
    if (p.piece_id === action.piece_id) {
      if (action.action_type === 'CAPTURE_STAND') {
        // Ném bom hoặc bắn hỏa lực tại chỗ: Giữ nguyên vị trí quân
        return p;
      }
      // Nước đi hoặc ăn quân thế chỗ: Cập nhật vị trí mới
      return {
        ...p,
        position: { ...action.to_pos },
      };
    }

    return p;
  });

  const event: GameEvent = {
    event_id: `evt_${Date.now()}`,
    event_type: captured ? 'PIECE_CAPTURED' : 'PIECE_MOVED',
    actor_id: action.piece_id,
    target_id: action.target_piece_id || null,
    notation: action.notation,
    score_delta: scoreDelta,
    details: {
      action_type: action.action_type,
    },
  };

  return {
    nextPieces,
    event,
    capturedPiece: captured,
  };
}
