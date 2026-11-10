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
 * specified in docs/GAME_RULES.md, docs/BUG_REPORT.md, and
 * confirmed in docs/OPEN_QUESTIONS.md (Q5 - Q9).
 */

import { PieceState, LegalAction, ActionType, GameEvent, Position, EventType, ActiveCompoundState } from '../types';
import { formatCoordinateNotation } from '../utils/coordinates';
import { PIECE_VIETNAMESE_NAMES, PIECE_NOTATION_SYMBOL } from '../utils/assets';

export const PIECE_SCORES: Record<string, number> = {
  COMMANDER: 100,
  HEADQUARTERS: 100,
  AIRCRAFT: 40,
  NAVY: 80,
  MISSILE: 20,
  TANK: 20,
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

// 8 điểm dạng kỵ mã cho Vành đai lửa Tên lửa Anh hùng (Q6)
const KNIGHT_OFFSETS: [number, number][] = [
  [-1, -2], [1, -2], [-1, 2], [1, 2],
  [-2, -1], [2, -1], [-2, 1], [2, 1]
];

export function isInsideBoard(x: number, y: number): boolean {
  return x >= 0 && x <= 10 && y >= 0 && y <= 11;
}

export function isSeaSquare(x: number): boolean {
  return x <= 1; // Cột 0 và 1 là biển sâu (chỉ Hải quân, Máy bay, Tên lửa hoạt động)
}

export function isFordSquare(x: number, y: number): boolean {
  // Hai bến sông ngầm qua sông: (5, 5)-(6, 5) và (5, 7)-(6, 7) (BUG-NAVY-001 & RULE-RIVER-001)
  return (x === 5 || x === 7) && (y === 5 || y === 6);
}

export function isShoreSquare(x: number, y: number): boolean {
  // Bờ biển: x = 2. Bờ sông: y = 5 hoặc y = 6 (từ x = 2 đến x = 10, trừ sông ngầm) (Q8)
  return x === 2 || ((y === 5 || y === 6) && x >= 2 && x <= 10 && !isFordSquare(x, y));
}

export function isRiverSquare(x: number, y: number): boolean {
  return (y === 5 || y === 6) && x >= 2 && x <= 10;
}

export function isCrossingRiver(fromY: number, toY: number): boolean {
  return (fromY <= 5 && toY >= 6) || (fromY >= 6 && toY <= 5);
}

export function canNavyOccupySquare(nx: number, ny: number): boolean {
  // Tàu chiến chỉ đi biển (x<=1), bờ biển (x=2) hoặc dải sông (y=5,6).
  // CẤM đi vào hoặc đi qua sông ngầm (BUG-NAVY-001)
  if (isFordSquare(nx, ny)) return false;
  return nx <= 2 || ny === 5 || ny === 6;
}

/**
 * Kiểm tra xem bước đi chéo của Hải quân có cắt qua vùng đất liền giữa bờ biển và bờ sông hay không.
 * Ví dụ: giữa (x=2, y=7) và (x=3, y=6) thuộc đất liền bên Xanh (không thể đi đến (6, 3) hoặc (5, 4)).
 * Giữa (x=2, y=4) và (x=3, y=5) thuộc đất liền bên Đỏ.
 */
export function isNavyLandDiagonal(x1: number, y1: number, x2: number, y2: number): boolean {
  if (x1 === x2 || y1 === y2) return false;
  // Phía bắc sông: x >= 2 và cắt qua biên giới y=6 và y=7 (đất liền bên Xanh)
  if (Math.min(x1, x2) >= 2 && ((y1 >= 7 && y2 <= 6) || (y2 >= 7 && y1 <= 6))) {
    return true;
  }
  // Phía nam sông: x >= 2 và cắt qua biên giới y=4 và y=5 (đất liền bên Đỏ)
  if (Math.min(x1, x2) >= 2 && ((y1 <= 4 && y2 >= 5) || (y2 <= 4 && y1 >= 5))) {
    return true;
  }
  return false;
}

/**
 * Kiểm tra xem quân có được tự vượt sông sâu sang ô trống không (RULE-RIVER-001)
 * - Sông ngầm: Chỉ đi qua theo ĐƯỜNG THẲNG tại cột x = 5 và x = 7 (fromX === toX && (fromX === 5 || fromX === 7)).
 * - Tên lửa, pháo binh không thể đi qua sông sâu theo đường chéo sang ô trống.
 * - Muốn đi qua sông sâu chỉ có thể nhờ công binh chở qua hoặc ăn quân thế chỗ bên kia sông.
 */
export function canPieceCrossRiverToEmpty(
  pieceType: string,
  fromX: number,
  fromY: number,
  toX: number,
  toY: number
): boolean {
  if (!isCrossingRiver(fromY, toY)) return true;

  // Sông ngầm: Chỉ đi qua theo ĐƯỜNG THẲNG tại x = 5 và x = 7
  if (fromX === toX && (fromX === 5 || fromX === 7)) return true;

  // Các quân nặng không thể tự vượt sông sâu sang ô trống (cần Công binh chở qua hoặc ăn quân thế chỗ)
  if (pieceType === 'ANTI_AIR' || pieceType === 'ARTILLERY' || pieceType === 'MISSILE') {
    return false;
  }

  return true;
}

/**
 * Kiểm tra khả năng chở quân / lên phương tiện (RULE-TRANSPORT-001 & BUG-HQ-001)
 */
export function canBoardCarrier(passenger: PieceState, carrier: PieceState): boolean {
  if (carrier.side !== passenger.side || !carrier.is_alive || !passenger.is_alive) return false;
  if (carrier.carried_by_id != null) return false;
  if (passenger.piece_id === carrier.piece_id) return false;

  const currentPassengers = carrier.carrying_piece_ids ? carrier.carrying_piece_ids.length : 0;

  if (carrier.type === 'TANK') {
    return (
      currentPassengers < 2 &&
      (passenger.type === 'INFANTRY' || passenger.type === 'MILITIA' || passenger.type === 'COMMANDER')
    );
  }

  if (carrier.type === 'AIRCRAFT') {
    return (
      currentPassengers < 2 &&
      (passenger.type === 'INFANTRY' ||
        passenger.type === 'MILITIA' ||
        passenger.type === 'COMMANDER' ||
        passenger.type === 'TANK')
    );
  }

  if (carrier.type === 'NAVY') {
    return (
      currentPassengers < 2 &&
      (passenger.type === 'INFANTRY' ||
        passenger.type === 'MILITIA' ||
        passenger.type === 'COMMANDER' ||
        passenger.type === 'TANK' ||
        passenger.type === 'AIRCRAFT')
    );
  }

  if (carrier.type === 'ENGINEER') {
    const isAtRiverBank = carrier.position.y === 5 || carrier.position.y === 6;
    return (
      isAtRiverBank &&
      currentPassengers < 1 &&
      (passenger.type === 'ARTILLERY' || passenger.type === 'ANTI_AIR' || passenger.type === 'MISSILE')
    );
  }

  if (carrier.type === 'HEADQUARTERS') {
    if (carrier.is_hero) return false; // Sở chỉ huy Anh hùng không còn cho ẩn nấp
    return currentPassengers < 1 && passenger.type === 'COMMANDER';
  }

  return false;
}

/**
 * Tìm quân gốc đang đứng trực tiếp trên bàn cờ
 */
export function getRootCarrier(piece: PieceState, allPieces: PieceState[]): PieceState {
  const byId = new Map<string, PieceState>();
  for (const p of allPieces) {
    if (p.is_alive) byId.set(p.piece_id, p);
  }
  let cursor = piece;
  const seen = new Set<string>([piece.piece_id]);
  while (cursor.carried_by_id != null) {
    const parent = byId.get(cursor.carried_by_id);
    if (!parent || seen.has(parent.piece_id)) break;
    seen.add(parent.piece_id);
    cursor = parent;
  }
  return cursor;
}

/**
 * Quy tắc phong Anh hùng trễ cho Sở chỉ huy duy nhất:
 * Khi phe chỉ còn Tư lệnh + 1 Sở chỉ huy (chưa Anh hùng) và Tư lệnh đang trú trong Sở chỉ huy đó,
 * Sở chỉ huy CHƯA phong Anh hùng; người chơi chỉ được đi nước đưa Tư lệnh rời khỏi Sở chỉ huy.
 */
export function delayedSolitaryHqCommanderId(
  allPieces: PieceState[],
  side: 'RED' | 'BLUE'
): string | null {
  const alive = allPieces.filter((p) => p.is_alive && p.side === side);
  const nonCmdNonHq = alive.filter((p) => p.type !== 'COMMANDER' && p.type !== 'HEADQUARTERS');
  const hqPieces = alive.filter((p) => p.type === 'HEADQUARTERS');
  const cmd = alive.find((p) => p.type === 'COMMANDER');
  if (
    cmd &&
    nonCmdNonHq.length === 0 &&
    hqPieces.length === 1 &&
    !hqPieces[0].is_hero &&
    cmd.carried_by_id === hqPieces[0].piece_id
  ) {
    return cmd.piece_id;
  }
  return null;
}

/**
 * Tính toán toàn bộ các giao điểm thuộc Vành đai lửa phòng không của một phe (RULE-AA-001, RULE-HERO-003, Q6)
 */
export function getAirDefenseZones(targetSide: 'RED' | 'BLUE', allPieces: PieceState[]): { x: number; y: number }[] {
  const aaUnits = allPieces.filter(
    (p) =>
      p.is_alive &&
      !p.carried_by_id &&
      p.side === targetSide &&
      (p.type === 'ANTI_AIR' || p.type === 'MISSILE' || p.type === 'NAVY')
  );

  const zoneMap = new Map<string, { x: number; y: number }>();

  for (const unit of aaUnits) {
    const { x, y } = unit.position;

    // 1. Cao xạ: Ngang/dọc 1 đoạn (Anh hùng: ngang/dọc 2 đoạn, chéo 1 đoạn)
    if (unit.type === 'ANTI_AIR') {
      const maxStraight = unit.is_hero ? 2 : 1;
      for (const [dx, dy] of ORTHOGONAL) {
        for (let r = 1; r <= maxStraight; r++) {
          const nx = x + dx * r;
          const ny = y + dy * r;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
      if (unit.is_hero) {
        for (const [dx, dy] of DIAGONAL) {
          const nx = x + dx;
          const ny = y + dy;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
    }

    // 2. Hải quân (Cao xạ hạm): Ngang/dọc 1 đoạn (Anh hùng: ngang/dọc 2 đoạn, chéo 1 đoạn)
    if (unit.type === 'NAVY') {
      const maxStraight = unit.is_hero ? 2 : 1;
      for (const [dx, dy] of ORTHOGONAL) {
        for (let r = 1; r <= maxStraight; r++) {
          const nx = x + dx * r;
          const ny = y + dy * r;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
      if (unit.is_hero) {
        for (const [dx, dy] of DIAGONAL) {
          const nx = x + dx;
          const ny = y + dy;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
    }

    // 3. Tên lửa: Ngang/dọc 2 đoạn, chéo 1 đoạn (Anh hùng: ngang/dọc 3, chéo 2 + 8 điểm kỵ mã Q6)
    if (unit.type === 'MISSILE') {
      const straightRange = unit.is_hero ? 3 : 2;
      const diagRange = unit.is_hero ? 2 : 1;
      for (const [dx, dy] of ORTHOGONAL) {
        for (let r = 1; r <= straightRange; r++) {
          const nx = x + dx * r;
          const ny = y + dy * r;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
      for (const [dx, dy] of DIAGONAL) {
        for (let r = 1; r <= diagRange; r++) {
          const nx = x + dx * r;
          const ny = y + dy * r;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
      if (unit.is_hero) {
        for (const [dx, dy] of KNIGHT_OFFSETS) {
          const nx = x + dx;
          const ny = y + dy;
          if (isInsideBoard(nx, ny)) zoneMap.set(`${nx},${ny}`, { x: nx, y: ny });
        }
      }
    }
  }

  return Array.from(zoneMap.values());
}

/**
 * Kiểm tra xem toàn bộ hành trình bay (từ fromPos đến toPos) có cắt qua hoặc nằm trong
 * vành đai lửa phòng không hay không (AIR-01, Q11).
 */
export function isAircraftFlightAffectedByAa(
  fromPos: Position,
  toPos: Position,
  enemyAaZones: { x: number; y: number }[],
  enemyAaUnits?: PieceState[]
): boolean {
  const isAaPoint = (x: number, y: number) => {
    if (enemyAaZones.some((z) => z.x === x && z.y === y)) return true;
    if (
      enemyAaUnits &&
      enemyAaUnits.some(
        (u) => u.is_alive && u.position.x === x && u.position.y === y
      )
    ) {
      return true;
    }
    return false;
  };

  // 1. Nếu điểm xuất phát hoặc điểm đến nằm trong vành đai lửa / trên đầu đơn vị phòng không
  if (isAaPoint(fromPos.x, fromPos.y)) return true;
  if (isAaPoint(toPos.x, toPos.y)) return true;

  // 2. Kiểm tra các giao điểm trung gian trên đường bay
  const stepX = Math.sign(toPos.x - fromPos.x);
  const stepY = Math.sign(toPos.y - fromPos.y);
  const totalSteps = Math.max(Math.abs(toPos.x - fromPos.x), Math.abs(toPos.y - fromPos.y));
  for (let s = 1; s < totalSteps; s++) {
    const interX = fromPos.x + stepX * s;
    const interY = fromPos.y + stepY * s;
    if (isAaPoint(interX, interY)) {
      return true;
    }
  }
  return false;
}

/**
 * Kiểm tra xem hai Tư lệnh có đang đối mặt nhau trên cùng hàng/cột không (BUG-CMD-001)
 * Tư lệnh nằm trên phương tiện (Xe tăng, Máy bay, Tàu chiến) hoặc trong Sở chỉ huy đều chặn đối mặt!
 */
export function isCommandersFacing(allPieces: PieceState[]): boolean {
  const redCmd = allPieces.find((p) => p.is_alive && p.side === 'RED' && p.type === 'COMMANDER');
  const blueCmd = allPieces.find((p) => p.is_alive && p.side === 'BLUE' && p.type === 'COMMANDER');

  if (!redCmd || !blueCmd) return false;

  if (redCmd.carried_by_id != null && allPieces.some((p) => p.is_alive && p.piece_id === redCmd.carried_by_id)) {
    return false;
  }
  if (blueCmd.carried_by_id != null && allPieces.some((p) => p.is_alive && p.piece_id === blueCmd.carried_by_id)) {
    return false;
  }

  const visible = allPieces.filter((p) => p.is_alive && !p.carried_by_id);

  // 1. Cùng cột dọc (x giống nhau)
  if (redCmd.position.x === blueCmd.position.x) {
    const x = redCmd.position.x;
    const minY = Math.min(redCmd.position.y, blueCmd.position.y);
    const maxY = Math.max(redCmd.position.y, blueCmd.position.y);

    const hasObstacle = visible.some(
      (p) => p.position.x === x && p.position.y > minY && p.position.y < maxY
    );
    if (!hasObstacle) return true; // Lộ mặt Tư lệnh trên cột dọc!
  }

  // 2. Cùng hàng ngang (y giống nhau)
  if (redCmd.position.y === blueCmd.position.y) {
    const y = redCmd.position.y;
    const minX = Math.min(redCmd.position.x, blueCmd.position.x);
    const maxX = Math.max(redCmd.position.x, blueCmd.position.x);

    const hasObstacle = visible.some(
      (p) => p.position.y === y && p.position.x > minX && p.position.x < maxX
    );
    if (!hasObstacle) return true; // Lộ mặt Tư lệnh trên hàng ngang!
  }

  return false;
}

/**
 * Kiểm tra xem Sở chỉ huy có đang nằm trên đường nhìn thẳng của Tư lệnh đối phương không (Q9)
 */
export function isHqFacingEnemyCommander(
  hq: PieceState,
  enemyCmd: PieceState,
  allPieces: PieceState[]
): boolean {
  if (!enemyCmd.is_alive || enemyCmd.carried_by_id != null) return false;
  const visible = allPieces.filter((p) => p.is_alive && !p.carried_by_id);
  if (hq.position.x === enemyCmd.position.x) {
    const x = hq.position.x;
    const minY = Math.min(hq.position.y, enemyCmd.position.y);
    const maxY = Math.max(hq.position.y, enemyCmd.position.y);
    const hasObstacle = visible.some(
      (p) =>
        p.position.x === x &&
        p.position.y > minY &&
        p.position.y < maxY &&
        p.piece_id !== hq.piece_id &&
        p.piece_id !== enemyCmd.piece_id
    );
    if (!hasObstacle) return true;
  }
  if (hq.position.y === enemyCmd.position.y) {
    const y = hq.position.y;
    const minX = Math.min(hq.position.x, enemyCmd.position.x);
    const maxX = Math.max(hq.position.x, enemyCmd.position.x);
    const hasObstacle = visible.some(
      (p) =>
        p.position.y === y &&
        p.position.x > minX &&
        p.position.x < maxX &&
        p.piece_id !== hq.piece_id &&
        p.piece_id !== enemyCmd.piece_id
    );
    if (!hasObstacle) return true;
  }
  return false;
}

/**
 * Kiểm tra xem Sở chỉ huy mục tiêu có đang che chở Tư lệnh bên trong không (Q9)
 */
export function isHqShelteringCommander(target: PieceState, allPieces: PieceState[]): boolean {
  if (target.type !== 'HEADQUARTERS') return false;
  return allPieces.some(
    (p) => p.is_alive && p.type === 'COMMANDER' && p.carried_by_id === target.piece_id
  );
}

function pieceThreatensSquare(
  pieces: PieceState[],
  p: PieceState,
  targetX: number,
  targetY: number,
  pieceMap: Map<string, PieceState>
): boolean {
  if (p.type === 'HEADQUARTERS' && !p.is_hero) return false;

  const originPiece = p.carried_by_id != null ? getRootCarrier(p, pieces) : p;
  const px = originPiece.position.x;
  const py = originPiece.position.y;
  if (px === targetX && py === targetY) return false;

  // Quân đang ngồi trên phương tiện địch muốn triển khai ăn trực tiếp: không thể thế chỗ trên biển (trừ Navy)
  if (p.carried_by_id != null && isSeaSquare(targetX) && p.type !== 'NAVY') {
    return false;
  }

  const dx = targetX - px;
  const dy = targetY - py;
  const adx = Math.abs(dx);
  const ady = Math.abs(dy);
  const isOrth = adx === 0 || ady === 0;
  const isDiag = adx === ady;
  if (!isOrth && !isDiag) return false;

  const dist = Math.max(adx, ady);
  const stepX = dx === 0 ? 0 : dx > 0 ? 1 : -1;
  const stepY = dy === 0 ? 0 : dy > 0 ? 1 : -1;

  let blocked = false;
  for (let s = 1; s < dist; s++) {
    if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
      blocked = true;
      break;
    }
  }

  if (p.type === 'COMMANDER') {
    if (p.is_hero) return dist <= 2 && !blocked;
    return isOrth && dist === 1;
  }
  if (p.type === 'INFANTRY' || p.type === 'ENGINEER' || p.type === 'ANTI_AIR') {
    const dirsOk = p.is_hero ? true : isOrth;
    const maxR = p.is_hero ? 2 : 1;
    return dirsOk && dist <= maxR && !blocked;
  }
  if (p.type === 'MILITIA') {
    return dist <= (p.is_hero ? 2 : 1) && !blocked;
  }
  if (p.type === 'TANK') {
    const dirsOk = p.is_hero ? true : isOrth;
    const maxR = p.is_hero ? 3 : 2;
    return dirsOk && dist <= maxR && !blocked;
  }
  if (p.type === 'MISSILE') {
    // Tên lửa được phép ăn xuyên vật cản (ngang/dọc và chéo)
    const maxR = isOrth ? (p.is_hero ? 3 : 2) : (p.is_hero ? 2 : 1);
    return dist <= maxR;
  }
  if (p.type === 'ARTILLERY') {
    return dist <= (p.is_hero ? 4 : 3);
  }
  if (p.type === 'AIRCRAFT') {
    return dist <= (p.is_hero ? 5 : 4);
  }
  if (p.type === 'NAVY') {
    if (!canNavyOccupySquare(px, py)) return false;
    const targetOcc = pieceMap.get(`${targetX},${targetY}`);
    if (targetOcc && targetOcc.type === 'NAVY') {
      const maxNav = p.is_hero ? 5 : 4;
      if (dist > maxNav) return false;
      for (let s = 1; s <= dist; s++) {
        const nx = px + stepX * s;
        const ny = py + stepY * s;
        const prevX = px + stepX * (s - 1);
        const prevY = py + stepY * (s - 1);
        if (isFordSquare(nx, ny) || !canNavyOccupySquare(nx, ny)) return false;
        if (isNavyLandDiagonal(prevX, prevY, nx, ny)) return false;
        if (s < dist) {
          const occ = pieceMap.get(`${nx},${ny}`);
          if (occ && (occ.type === 'NAVY' || occ.side !== p.side)) return false;
        }
      }
      return true;
    }
    // Pháo hạm bắn vào đất liền / mục tiêu khác (tầm 3, Anh hùng 4), vượt đất liền/vật cản
    return dist <= (p.is_hero ? 4 : 3);
  }
  if (p.type === 'HEADQUARTERS') {
    return p.is_hero && dist <= 2 && !blocked;
  }

  return false;
}

/**
 * Kiểm tra xem một ô (targetX, targetY) có đang bị bất kỳ quân địch nào tấn công/chiếu không
 * (bao gồm cả quân địch đang ngồi trên phương tiện triển khai ăn trực tiếp).
 */
export function isSquareAttackedByEnemy(
  pieces: PieceState[],
  targetX: number,
  targetY: number,
  enemySide: 'RED' | 'BLUE'
): boolean {
  const pieceMap = new Map<string, PieceState>();
  for (const p of pieces) {
    if (p.is_alive && !p.carried_by_id) {
      pieceMap.set(`${p.position.x},${p.position.y}`, p);
    }
  }

  for (const p of pieces) {
    if (!p.is_alive || p.side !== enemySide) continue;
    if (pieceThreatensSquare(pieces, p, targetX, targetY, pieceMap)) {
      return true;
    }
  }

  return false;
}

/**
 * Kiểm tra xem Tư lệnh của một phe có đang bị chiếu không (nằm trong tầm ăn của quân địch)
 */
export function isCommanderInCheck(pieces: PieceState[], side: 'RED' | 'BLUE'): boolean {
  const cmd = pieces.find((p) => p.is_alive && p.side === side && p.type === 'COMMANDER');
  if (!cmd) return false;
  const enemySide = side === 'RED' ? 'BLUE' : 'RED';
  if (cmd.carried_by_id) {
    const carrier = pieces.find((p) => p.is_alive && p.piece_id === cmd.carried_by_id);
    if (!carrier) return false;
    if (carrier.type === 'HEADQUARTERS' && !carrier.is_hero) {
      return false; // Trú ẩn an toàn trong Sở chỉ huy thường
    }
    const root = getRootCarrier(carrier, pieces);
    return isSquareAttackedByEnemy(pieces, root.position.x, root.position.y, enemySide);
  }
  return isSquareAttackedByEnemy(pieces, cmd.position.x, cmd.position.y, enemySide);
}

/**
 * Mô phỏng danh sách quân cờ sau khi một hành động được thực thi
 */
export function simulateActionOnPieces(pieces: PieceState[], action: LegalAction): PieceState[] {
  const newPieces: PieceState[] = [];
  for (const p of pieces) {
    if (!p.is_alive) continue;
    if (action.target_piece_id && p.piece_id === action.target_piece_id) {
      if (action.action_type === 'CAPTURE_REPLACE' || action.action_type === 'CAPTURE_STAND') {
        if (p.type === 'HEADQUARTERS') {
          // Sở chỉ huy bị diệt, nhưng Tư lệnh bên trong sống sót
          continue;
        }
        continue;
      }
    }
    if (p.piece_id === action.piece_id) {
      if (action.action_type === 'BOARD') {
        newPieces.push({
          ...p,
          position: { ...action.to_pos },
          carried_by_id: action.target_piece_id || null,
        });
      } else {
        newPieces.push({
          ...p,
          position: { ...action.to_pos },
        });
      }
    } else {
      newPieces.push(p);
    }
  }
  return newPieces;
}

/**
 * Lấy danh sách ID của toàn bộ các quân đang được cõng (trực tiếp và gián tiếp/lồng nhau)
 */
export function getAllCarriedPieceIds(carrierId: string, allPieces: PieceState[]): string[] {
  const result: string[] = [];
  const queue = [carrierId];
  while (queue.length > 0) {
    const curId = queue.shift()!;
    for (const p of allPieces) {
      if (p.is_alive && p.carried_by_id === curId && !result.includes(p.piece_id)) {
        result.push(p.piece_id);
        queue.push(p.piece_id);
      }
    }
  }
  return result;
}

function canNestPair(
  inner: PieceState,
  outer: PieceState,
  allPieces: PieceState[],
  originY: number
): boolean {
  const outerFree: PieceState = { ...outer, carried_by_id: null, carrying_piece_ids: [] };
  const innerFree: PieceState = { ...inner, carried_by_id: null };
  if (!canBoardCarrier(innerFree, outerFree)) return false;
  if (outer.type === 'ENGINEER' && originY !== 5 && originY !== 6) return false;
  const totalNested = 1 + getAllCarriedPieceIds(inner.piece_id, allPieces).length;
  const maxCap = outer.type === 'ENGINEER' || outer.type === 'HEADQUARTERS' ? 1 : 2;
  return totalNested <= maxCap;
}

function detachCargoMap(
  actor: PieceState,
  origin: Position,
  allPieces: PieceState[]
): Map<string, { carriedById: string | null; position: Position }> {
  const result = new Map<string, { carriedById: string | null; position: Position }>();
  const direct = allPieces.filter((p) => p.is_alive && p.carried_by_id === actor.piece_id);
  if (direct.length === 0) return result;
  if (direct.length === 1) {
    result.set(direct[0].piece_id, { carriedById: null, position: { ...origin } });
    for (const subId of getAllCarriedPieceIds(direct[0].piece_id, allPieces)) {
      const subP = allPieces.find((x) => x.piece_id === subId);
      if (subP) {
        result.set(subId, { carriedById: subP.carried_by_id ?? null, position: { ...origin } });
      }
    }
    return result;
  }
  const [p1, p2] = direct;
  const [rootP, nestedP] = canNestPair(p2, p1, allPieces, origin.y) ? [p1, p2] : [p2, p1];
  result.set(rootP.piece_id, { carriedById: null, position: { ...origin } });
  result.set(nestedP.piece_id, { carriedById: rootP.piece_id, position: { ...origin } });
  for (const subId of getAllCarriedPieceIds(nestedP.piece_id, allPieces)) {
    const subP = allPieces.find((x) => x.piece_id === subId);
    if (subP) {
      result.set(subId, { carriedById: subP.carried_by_id ?? null, position: { ...origin } });
    }
  }
  return result;
}

export function applyHeroPromotions(pieces: PieceState[]): PieceState[] {
  let updated = pieces;
  for (const side of ['RED', 'BLUE'] as const) {
    const alivePieces = updated.filter((p) => p.is_alive && p.side === side);
    const nonCmdNonHq = alivePieces.filter((p) => p.type !== 'COMMANDER' && p.type !== 'HEADQUARTERS');
    const hqPieces = alivePieces.filter((p) => p.type === 'HEADQUARTERS');
    const cmd = alivePieces.find((p) => p.type === 'COMMANDER');

    if (nonCmdNonHq.length === 1 && !nonCmdNonHq[0].is_hero) {
      const heroId = nonCmdNonHq[0].piece_id;
      updated = updated.map((p) => (p.piece_id === heroId ? { ...p, is_hero: true } : p));
    } else if (nonCmdNonHq.length === 0 && hqPieces.length === 1 && !hqPieces[0].is_hero) {
      const soleHq = hqPieces[0];
      if (cmd && cmd.carried_by_id === soleHq.piece_id) {
        continue; // Phong trễ: chờ Tư lệnh bước ra khỏi Sở chỉ huy
      }
      const heroHqId = soleHq.piece_id;
      updated = updated.map((p) => (p.piece_id === heroHqId ? { ...p, is_hero: true } : p));
    }
  }
  return updated;
}

/**
 * Mô phỏng trạng thái sau hành động để kiểm tra tính hợp lệ
 */
export function simulateAction(action: LegalAction, pieces: PieceState[]): PieceState[] {
  if (action.action_type === 'END_TURN') return pieces;

  const actor = pieces.find((p) => p.is_alive && p.piece_id === action.piece_id);
  if (!actor) return pieces;
  const target = action.target_piece_id
    ? pieces.find((p) => p.is_alive && p.piece_id === action.target_piece_id)
    : undefined;
  const isCarrierPickingUp =
    action.action_type === 'BOARD' &&
    target != null &&
    canBoardCarrier(target, actor);

  const actorOrigin = getRootCarrier(actor, pieces).position;
  const enemySide = actor.side === 'RED' ? 'BLUE' : 'RED';
  const enemyAaZone = getAirDefenseZones(enemySide, pieces);
  const enemyAaUnits = pieces.filter(
    (p) =>
      p.is_alive &&
      !p.carried_by_id &&
      p.side === enemySide &&
      (p.type === 'ANTI_AIR' || p.type === 'MISSILE' || p.type === 'NAVY')
  );
  const isActorAircraft = actor.type === 'AIRCRAFT' && !actor.is_hero;
  const isTargetAaUnit = enemyAaUnits.some(
    (u) => u.position.x === action.to_pos.x && u.position.y === action.to_pos.y
  );
  const isInAaZone =
    isActorAircraft &&
    (isTargetAaUnit || isAircraftFlightAffectedByAa(actorOrigin, action.to_pos, enemyAaZone, enemyAaUnits));

  const actorDescendants = new Set(getAllCarriedPieceIds(actor.piece_id, pieces));
  const targetDescendants = new Set(target ? getAllCarriedPieceIds(target.piece_id, pieces) : []);

  const leaveBehind =
    (action.carry_cargo === false &&
      (action.action_type === 'MOVE' || action.action_type === 'CAPTURE_REPLACE') &&
      actorDescendants.size > 0) ||
    (actor.type === 'HEADQUARTERS' &&
      (action.action_type === 'MOVE' || action.action_type === 'CAPTURE_REPLACE') &&
      actorDescendants.size > 0);
  const detachedMap = leaveBehind ? detachCargoMap(actor, actorOrigin, pieces) : new Map();

  const updated = pieces.map((p) => {
    if (action.action_type === 'BOARD' && isCarrierPickingUp) {
      if (p.piece_id === action.piece_id) {
        return { ...p, position: { ...action.to_pos }, carried_by_id: null };
      }
      if (p.piece_id === action.target_piece_id) {
        return { ...p, position: { ...action.to_pos }, carried_by_id: action.piece_id };
      }
      if (actorDescendants.has(p.piece_id) || targetDescendants.has(p.piece_id)) {
        return { ...p, position: { ...action.to_pos } };
      }
      return p;
    }

    if (action.target_piece_id && p.piece_id === action.target_piece_id) {
      if (action.action_type === 'BOARD') {
        const cur = p.carrying_piece_ids || [];
        return {
          ...p,
          carrying_piece_ids: cur.includes(action.piece_id) ? cur : [...cur, action.piece_id],
        };
      }
      return { ...p, is_alive: false, carried_by_id: null };
    }

    if (
      action.target_piece_id &&
      action.action_type !== 'BOARD' &&
      targetDescendants.has(p.piece_id)
    ) {
      if (target && target.type === 'HEADQUARTERS') {
        if (p.carried_by_id === target.piece_id) {
          return { ...p, carried_by_id: null, is_alive: true, position: { ...target.position } };
        }
        return { ...p, position: { ...target.position } };
      }
      return { ...p, is_alive: false, carried_by_id: null };
    }

    if (p.piece_id === action.piece_id) {
      if (isInAaZone) {
        return { ...p, is_alive: false, position: { ...action.to_pos }, carried_by_id: null };
      }
      if (action.action_type === 'CAPTURE_STAND') return p;
      if (action.action_type === 'BOARD') {
        return { ...p, position: { ...action.to_pos }, carried_by_id: action.target_piece_id || null };
      }
      return { ...p, position: { ...action.to_pos }, carried_by_id: null };
    }

    if (actorDescendants.has(p.piece_id)) {
      const detached = detachedMap.get(p.piece_id);
      if (detached) {
        return { ...p, carried_by_id: detached.carriedById, position: { ...detached.position } };
      }
      if (isInAaZone) {
        return { ...p, is_alive: false, carried_by_id: null };
      }
      if (action.action_type === 'CAPTURE_STAND') return p;
      return { ...p, position: { ...action.to_pos } };
    }

    return p;
  });

  // Đồng bộ 2 chiều và tọa độ quân được chở theo quân gốc
  const synced = updated.map((p) => {
    const cargo = updated
      .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
      .map((other) => other.piece_id);
    if (p.is_alive && p.carried_by_id != null) {
      const root = getRootCarrier(p, updated);
      return { ...p, carrying_piece_ids: cargo, position: { ...root.position } };
    }
    return { ...p, carrying_piece_ids: cargo };
  });

  return applyHeroPromotions(synced);
}

/**
 * Kiểm tra xem phương tiện có thể đi một mình và để lại quân cõng ở vị trí xuất phát không
 * (Quy tắc 2: Cấm tách lẻ bỏ lại 2 quân không có khả năng chở lẫn nhau mà không có phương tiện)
 */
export function canCarrierLeaveCargoBehind(carrier: PieceState, allPieces: PieceState[]): boolean {
  const directPassengers = allPieces.filter(
    (p) => p.is_alive && p.carried_by_id === carrier.piece_id
  );
  if (directPassengers.length === 0) return true;
  const root = getRootCarrier(carrier, allPieces);
  if (isSeaSquare(root.position.x)) return false;
  if (directPassengers.length === 1) return true;
  if (directPassengers.length === 2) {
    const [p1, p2] = directPassengers;
    return (
      canNestPair(p2, p1, allPieces, root.position.y) ||
      canNestPair(p1, p2, allPieces, root.position.y)
    );
  }
  return false;
}

/**
 * Generate legal actions matching exact game rules
 */
export function getMockLegalActions(
  selectedPiece: PieceState,
  allPieces: PieceState[],
  carryCargo: boolean = true
): LegalAction[] {
  if (!selectedPiece.is_alive) return [];

  const side = selectedPiece.side;
  const trapCmdId = delayedSolitaryHqCommanderId(allPieces, side);
  if (trapCmdId !== null && selectedPiece.piece_id !== trapCmdId) {
    return [];
  }

  const candidateActions: LegalAction[] = [];
  const isCarried = selectedPiece.carried_by_id != null;
  const root = isCarried ? getRootCarrier(selectedPiece, allPieces) : selectedPiece;
  const { x, y } = root.position;
  const enemySide = side === 'RED' ? 'BLUE' : 'RED';
  const fromNot = formatCoordinateNotation({ x, y });
  const pieceName = PIECE_VIETNAMESE_NAMES[selectedPiece.type] || selectedPiece.type;
  const pieceSymbol = PIECE_NOTATION_SYMBOL[selectedPiece.type] || selectedPiece.type;

  const enemyCmd = allPieces.find((p) => p.is_alive && p.side === enemySide && p.type === 'COMMANDER');
  const enemyAaZone = getAirDefenseZones(enemySide, allPieces);
  const isEnemyAaSquare = (qx: number, qy: number) =>
    enemyAaZone.some((pos) => pos.x === qx && pos.y === qy) ||
    allPieces.some(
      (p) =>
        p.is_alive &&
        !p.carried_by_id &&
        p.side === enemySide &&
        (p.type === 'ANTI_AIR' || p.type === 'MISSILE' || p.type === 'NAVY') &&
        p.position.x === qx &&
        p.position.y === qy
    );

  const getPieceAt = (px: number, py: number) =>
    allPieces.find(
      (p) => p.is_alive && !p.carried_by_id && p.position.x === px && p.position.y === py
    );

  const canOccupySquare = (nx: number, ny: number): boolean => {
    if (selectedPiece.type === 'NAVY') {
      return canNavyOccupySquare(nx, ny);
    }
    if (isSeaSquare(nx)) {
      const occ = getPieceAt(nx, ny);
      if (occ) {
        if (occ.side !== side || canBoardCarrier(selectedPiece, occ)) {
          return true;
        }
      }
      return false;
    }
    return true;
  };

  const canSplitSolo =
    !isCarried &&
    selectedPiece.type !== 'HEADQUARTERS' &&
    Boolean(selectedPiece.carrying_piece_ids && selectedPiece.carrying_piece_ids.length > 0) &&
    canCarrierLeaveCargoBehind(selectedPiece, allPieces);
  const effectiveCarryCargo =
    selectedPiece.type === 'HEADQUARTERS' ? false : carryCargo || !canSplitSolo;

  const pushMove = (nx: number, ny: number, labelSuffix: string = '') => {
    const toNot = formatCoordinateNotation({ x: nx, y: ny });
    const isCarrier =
      selectedPiece.type !== 'HEADQUARTERS' &&
      selectedPiece.carrying_piece_ids &&
      selectedPiece.carrying_piece_ids.length > 0;
    const carryDesc = isCarrier
      ? (effectiveCarryCargo ? ' (mang theo quân cõng)' : ' (tách lẻ đi một mình, để lại quân)')
      : '';
    candidateActions.push({
      action_id: `m_${selectedPiece.piece_id}_${nx}_${ny}_${effectiveCarryCargo ? 'with' : 'solo'}`,
      action_type: 'MOVE',
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { x: nx, y: ny },
      target_piece_id: null,
      notation: `${pieceSymbol} ${fromNot} _ ${toNot}`,
      description: `${pieceName} ${selectedPiece.carried_by_id ? 'triển khai rời phương tiện đến' : 'tiến đến'} ${toNot}${carryDesc}${labelSuffix}`,
      carry_cargo: effectiveCarryCargo,
    });
  };

  const pushCapture = (
    nx: number,
    ny: number,
    target: PieceState,
    actType: ActionType,
    labelSuffix = ''
  ) => {
    if (isCarried && actType === 'CAPTURE_STAND') return;
    const toNot = formatCoordinateNotation({ x: nx, y: ny });
    const targetSymbol = PIECE_NOTATION_SYMBOL[target.type] || target.type;
    const enemyName = PIECE_VIETNAMESE_NAMES[target.type] || target.type;
    const isStand = actType === 'CAPTURE_STAND';
    const actionSymbol = isStand ? '_@_' : '@';
    const isCarrier =
      selectedPiece.type !== 'HEADQUARTERS' &&
      selectedPiece.carrying_piece_ids &&
      selectedPiece.carrying_piece_ids.length > 0;
    const carryDesc = isCarrier && !isStand
      ? (effectiveCarryCargo ? ' (mang theo quân cõng)' : ' (tách lẻ đi một mình, để lại quân)')
      : '';
    candidateActions.push({
      action_id: `c_${selectedPiece.piece_id}_${target.piece_id}_${actType}_${effectiveCarryCargo ? 'with' : 'solo'}`,
      action_type: actType,
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { x: nx, y: ny },
      target_piece_id: target.piece_id,
      notation: `${pieceSymbol} ${fromNot} ${actionSymbol} ${targetSymbol} ${toNot}`,
      description: `${pieceName} ${isStand ? 'tấn công tại chỗ tiêu diệt' : 'tiến công bắt'
        } ${enemyName} tại ${toNot}${carryDesc}${labelSuffix}`,
      carry_cargo: isStand ? false : effectiveCarryCargo,
    });
  };

  const pushBoard = (carrier: PieceState) => {
    if (trapCmdId !== null && carrier.type === 'HEADQUARTERS') return;
    const carrierName = PIECE_VIETNAMESE_NAMES[carrier.type] || carrier.type;
    const carrierSymbol = PIECE_NOTATION_SYMBOL[carrier.type] || carrier.type;
    const toNot = formatCoordinateNotation(carrier.position);
    candidateActions.push({
      action_id: `b_${selectedPiece.piece_id}_${carrier.piece_id}`,
      action_type: 'BOARD',
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { ...carrier.position },
      target_piece_id: carrier.piece_id,
      notation: `${pieceSymbol} ${fromNot} ^ ${carrierSymbol} ${toNot}`,
      description: `${pieceName} lên ${carrierName} tại ${toNot} (Cõng quân/Ẩn nấp)`,
    });
  };

  const pushPickup = (passenger: PieceState) => {
    if (isCarried) return;
    const passengerName = PIECE_VIETNAMESE_NAMES[passenger.type] || passenger.type;
    const passengerSymbol = PIECE_NOTATION_SYMBOL[passenger.type] || passenger.type;
    const toNot = formatCoordinateNotation(passenger.position);
    candidateActions.push({
      action_id: `p_${selectedPiece.piece_id}_${passenger.piece_id}`,
      action_type: 'BOARD',
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { ...passenger.position },
      target_piece_id: passenger.piece_id,
      notation: `${pieceSymbol} ${fromNot} ^ ${passengerSymbol} ${toNot}`,
      description: `${pieceName} đến cõng ${passengerName} tại ${toNot} (Đón cõng quân)`,
    });
  };

  // =========================================================================
  // 1. SỞ CHỈ HUY (HEADQUARTERS):
  // - Bình thường: Đứng yên, không di chuyển.
  // - Khi được phong Bộ binh Anh hùng (khi chỉ còn Tư lệnh + HQ):
  //   Di chuyển và ăn quân 8 hướng 1–2 đoạn như Bộ binh Anh hùng!
  // =========================================================================
  if (selectedPiece.type === 'HEADQUARTERS') {
    if (!selectedPiece.is_hero) {
      return [];
    }
    // Sở chỉ huy Anh hùng = Bộ binh Anh hùng (ALL_8, range 1–2)
    for (const [dx, dy] of ALL_8) {
      for (let step = 1; step <= 2; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (bắn tàu ngoài biển)' : '');
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
            }
          }
          break;
        }
      }
    }
  }

  // =========================================================================
  // 2. DÂN QUÂN (MILITIA):
  // - Đi và ăn 8 hướng 1 đoạn (Anh hùng: 1–2 đoạn).
  // =========================================================================
  if (selectedPiece.type === 'MILITIA') {
    const maxRange = selectedPiece.is_hero ? 2 : 1;
    for (const [dx, dy] of ALL_8) {
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (bắn tàu ngoài biển)' : '');
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
            }
          } else if (canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break;
        }
      }
    }
  }

  // =========================================================================
  // 3. BỘ BINH & CÔNG BINH:
  // - Đi và ăn ngang / dọc 1 đoạn (Anh hùng: 8 hướng 1–2 đoạn).
  // =========================================================================
  if (selectedPiece.type === 'INFANTRY' || selectedPiece.type === 'ENGINEER') {
    const dirs = selectedPiece.is_hero ? ALL_8 : ORTHOGONAL;
    const maxRange = selectedPiece.is_hero ? 2 : 1;
    for (const [dx, dy] of dirs) {
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (bắn tàu ngoài biển)' : '');
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
            }
          } else if (selectedPiece.type === 'ENGINEER' && canBoardCarrier(occ, selectedPiece) && !occ.carried_by_id) {
            pushPickup(occ);
          } else if (canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break;
        }
      }
    }
  }

  // =========================================================================
  // 4. CAO XẠ (ANTI_AIR):
  // - Đi và ăn ngang / dọc 1 đoạn (Anh hùng: 8 hướng 1–2 đoạn).
  // - Vượt sông: Cần Công binh sang ô trống; ăn quân bờ bên kia được thế chỗ (RULE-RIVER-001).
  // =========================================================================
  if (selectedPiece.type === 'ANTI_AIR') {
    const dirs = selectedPiece.is_hero ? ALL_8 : ORTHOGONAL;
    const maxRange = selectedPiece.is_hero ? 2 : 1;
    for (const [dx, dy] of dirs) {
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          if (canPieceCrossRiverToEmpty('ANTI_AIR', x, y, nx, ny)) {
            pushMove(nx, ny);
          }
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (bắn tàu ngoài biển)' : '');
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
            }
          } else if (canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break;
        }
      }
    }
  }

  // =========================================================================
  // 5. XE TĂNG (TANK):
  // - Đi và ăn ngang / dọc 1–2 đoạn (Anh hùng: 8 hướng 1–3 đoạn).
  // - Tự do vượt sông sâu.
  // =========================================================================
  if (selectedPiece.type === 'TANK') {
    const dirs = selectedPiece.is_hero ? ALL_8 : ORTHOGONAL;
    const maxRange = selectedPiece.is_hero ? 3 : 2;
    for (const [dx, dy] of dirs) {
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (bắn tàu ngoài biển)' : '');
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
            }
          } else if (canBoardCarrier(occ, selectedPiece) && !occ.carried_by_id) {
            pushPickup(occ);
          } else if (canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break; // Bị cản
        }
      }
    }
  }

  // =========================================================================
  // 6. TÊN LỬA (MISSILE):
  // - Ngang / dọc 1–2 đoạn, chéo 1 đoạn (Anh hùng: ngang/dọc 1–3 đoạn, chéo 1–2 đoạn).
  // - KHÔNG được di chuyển hoặc BOARD xuyên vật cản; ĐƯỢC PHÉP ăn xuyên vật cản!
  // - Không vào biển trống; vượt sông sâu sang ô trống bị cấm (trừ ngầm đá x=5,7 hoặc khi ăn quân).
  // =========================================================================
  if (selectedPiece.type === 'MISSILE') {
    const straightRange = selectedPiece.is_hero ? 3 : 2;
    const diagRange = selectedPiece.is_hero ? 2 : 1;

    for (const [dx, dy] of ORTHOGONAL) {
      // Pha 1: Di chuyển & Lên xe (bị cản bởi vật cản và biển)
      for (let step = 1; step <= straightRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;
        const occ = getPieceAt(nx, ny);
        if (!occ) {
          if (isSeaSquare(nx)) break;
          if (canPieceCrossRiverToEmpty('MISSILE', x, y, nx, ny)) {
            pushMove(nx, ny);
          }
        } else {
          if (occ.side === side && canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break;
        }
      }
      // Pha 2: Phóng tên lửa ăn xuyên vật cản & vượt sông sâu
      for (let step = 1; step <= straightRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;
        const occ = getPieceAt(nx, ny);
        if (occ && occ.side !== side) {
          if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (phóng tên lửa diệt tàu biển tại chỗ)' : '');
          } else {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (phóng tên lửa xuyên vật cản)');
          }
        }
      }
    }

    for (const [dx, dy] of DIAGONAL) {
      // Pha 1: Di chuyển & Lên xe chéo (bị cản)
      for (let step = 1; step <= diagRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;
        const occ = getPieceAt(nx, ny);
        if (!occ) {
          if (isSeaSquare(nx)) break;
          if (canPieceCrossRiverToEmpty('MISSILE', x, y, nx, ny)) {
            pushMove(nx, ny);
          }
        } else {
          if (occ.side === side && canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break;
        }
      }
      // Pha 2: Ăn xuyên vật cản chéo
      for (let step = 1; step <= diagRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;
        const occ = getPieceAt(nx, ny);
        if (occ && occ.side !== side) {
          if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (phóng tên lửa diệt tàu biển tại chỗ)' : '');
          } else {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (phóng tên lửa xuyên vật cản)');
          }
        }
      }
    }
  }

  // =========================================================================
  // 7. PHÁO BINH (ARTILLERY):
  // - Di chuyển: 8 hướng 1–3 đoạn (bị cản, không tự vượt sông sâu sang ô trống).
  // - Bắn ăn quân: 8 hướng 1–3 đoạn BẮN XUYÊN QUA QUÂN CẢN!
  // =========================================================================
  if (selectedPiece.type === 'ARTILLERY') {
    const maxRange = selectedPiece.is_hero ? 4 : 3;

    // Nhánh 1: Di chuyển ô trống (bị cản)
    for (const [dx, dy] of ALL_8) {
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          if (canPieceCrossRiverToEmpty('ARTILLERY', x, y, nx, ny)) {
            pushMove(nx, ny);
          }
        } else {
          if (step === 1 && canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
          break; // Bị cản
        }
      }

      // Nhánh 2: Bắn ăn quân (BẮN XUYÊN QUÂN CẢN)
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (occ && occ.side !== side) {
          if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', isSeaSquare(nx) ? ' (pháo kích diệt tàu biển tại chỗ)' : '');
          } else {
            // Pháo binh chỉ có thể ăn thế chỗ, không thể thả bom / bắn tại chỗ như máy bay
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (bắn ăn quân thế chỗ)');
          }
        }
      }
    }
  }

  // =========================================================================
  // 8. MÁY BAY (AIRCRAFT):
  // - Đi và ăn 8 hướng 1–4 đoạn, BAY VÀ ĂN XUYÊN QUÂN CÙNG PHE LẪN ĐỐI PHƯƠNG.
  // - Máy bay Anh hùng là Máy bay tàng hình: MIỄN NHIỄM VÀNH ĐAI LỬA (RULE-HERO-002).
  // =========================================================================
  if (selectedPiece.type === 'AIRCRAFT') {
    const maxRange = selectedPiece.is_hero ? 5 : 4;
    const fromInAa = isEnemyAaSquare(x, y) && !selectedPiece.is_hero;
    for (const [dx, dy] of ALL_8) {
      let pathCrossedAa = fromInAa;
      for (let step = 1; step <= maxRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        const squareInAa = isEnemyAaSquare(nx, ny) && !selectedPiece.is_hero;
        if (squareInAa) {
          pathCrossedAa = true;
        }
        const inAa = pathCrossedAa;
        const aaWarn = inAa ? ' ⚠️ (1 đổi 1 phòng không: bị tiêu diệt cùng mục tiêu)' : '';
        const aaMoveWarn = inAa ? ' ⚠️ (Bị phòng không bắn hạ ngay lập tức nếu bay vào/xuyên qua đây!)' : '';

        if (!occ) {
          // Máy bay KHÔNG thể đáp/dừng trên biển trống (x <= 1)
          if (!isSeaSquare(nx)) {
            pushMove(nx, ny, aaMoveWarn);
          }
          // Được phép bay qua biển để tới tàu chiến hoặc bờ bên kia
        } else if (occ.side === side) {
          if (canBoardCarrier(occ, selectedPiece) && !occ.carried_by_id && !isSeaSquare(nx)) {
            pushPickup(occ);
          } else if (occ.type === 'NAVY' && canBoardCarrier(selectedPiece, occ)) {
            pushBoard(occ);
          }
        } else {
          // Quân địch
          if (isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces)) {
            // Mục tiêu trên biển hoặc Sở chỉ huy đang che chở Tư lệnh: Bắt buộc thả bom tại chỗ
            pushCapture(
              nx,
              ny,
              occ,
              'CAPTURE_STAND',
              `${isSeaSquare(nx) ? ' 💣 (ném bom tàu biển tại chỗ)' : ' 💣 (ném bom tại chỗ)'}${aaWarn}`
            );
          } else {
            if (occ.type === 'AIRCRAFT') {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ` (không chiến bắt buộc thế chỗ)${aaWarn}`);
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ` 💣 (ném bom tại chỗ)${aaWarn}`);
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ` 🎯 (oanh tạc thế chỗ)${aaWarn}`);
            }
          }
        }
      }
    }
  }

  // =========================================================================
  // 9. TƯ LỆNH (COMMANDER):
  // - Đi thường: Ngang/dọc không giới hạn đoạn.
  // - BUG-CMD-001: Chặn mọi nước đi/hành trình tạo thế lộ mặt trực tiếp với Tư lệnh địch!
  // - Bắt quân: Ngang/dọc 1 đoạn.
  // - Vào Sở chỉ huy (BOARD): Kề cận và HQ không nằm trên đường nhìn của Tư lệnh địch (Q9).
  // =========================================================================
  if (selectedPiece.type === 'COMMANDER') {
    for (const [dx, dy] of ORTHOGONAL) {
      for (let step = 1; step <= 11; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || !canOccupySquare(nx, ny)) break;

        // Mô phỏng nước đi tới (nx, ny) (rời khỏi phương tiện nếu đang cõng) để kiểm tra đối mặt
        const simPieces = allPieces.map((p) =>
          p.piece_id === selectedPiece.piece_id
            ? { ...p, position: { x: nx, y: ny }, carried_by_id: null }
            : p
        );

        // BUG-CMD-001: Nếu ô này tạo thế lộ mặt, CHẶN ô này VÀ CHẶN cả đường phía sau!
        if (isCommandersFacing(simPieces)) {
          break; // Không sinh nước đi và không cho đi tiếp qua đoạn này
        }

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else {
          if (step === 1 && occ.side !== side) {
            pushCapture(
              nx,
              ny,
              occ,
              isSeaSquare(nx) || isHqShelteringCommander(occ, allPieces) ? 'CAPTURE_STAND' : 'CAPTURE_REPLACE'
            );
          } else if (step === 1 && occ.side === side) {
            // Vào Sở chỉ huy (Q9)
            if (occ.type === 'HEADQUARTERS' && !occ.is_hero) {
              if (!enemyCmd || !isHqFacingEnemyCommander(occ, enemyCmd, allPieces)) {
                pushBoard(occ);
              }
            } else if (canBoardCarrier(selectedPiece, occ)) {
              pushBoard(occ);
            }
          }
          break; // Bị cản
        }
      }
    }
  }

  // =========================================================================
  // 10. HẢI QUÂN (NAVY):
  // - BUG-NAVY-001: CẤM vào hoặc đi xuyên qua sông ngầm (isFordSquare).
  // - BUG-NAVY-002 & Q8: Bắn quân bờ (isShoreSquare) thế chỗ (trừ HQ đang che Tư lệnh). Đất liền sâu bắn tại chỗ.
  // - BUG-NAVY-003: Tầm đánh Hải quân địch <= 4 (Anh hùng: 5); Pháo hạm bắn đất liền <= 3 (Anh hùng: 4).
  // - Hải quân ĐƯỢC PHÉP đi vượt quân ta (không phải tàu chiến) ở bờ biển / bờ sông!
  // - Pháo hạm ĐƯỢC PHÉP bắn vào đất liền vượt vật cản / ngầm / đất liền trong tầm 3 (Anh hùng: 4)!
  // =========================================================================
  if (selectedPiece.type === 'NAVY') {
    const maxStraight = selectedPiece.is_hero ? 5 : 4;
    const maxGun = selectedPiece.is_hero ? 4 : 3;
    const shoreCaptureCoords = new Set<string>();

    for (const [dx, dy] of ALL_8) {
      // Pha 1: Hải lộ trên biển / sông / bờ (vượt quân ta trên bờ không phải Hải quân)
      for (let step = 1; step <= maxStraight; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny) || isFordSquare(nx, ny)) break;

        const prevX = x + dx * (step - 1);
        const prevY = y + dy * (step - 1);
        if (isNavyLandDiagonal(prevX, prevY, nx, ny)) {
          break;
        }
        if (!canNavyOccupySquare(nx, ny)) {
          break;
        }

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          pushMove(nx, ny);
        } else if (occ.side === side) {
          if (occ.type === 'NAVY') {
            break; // Bị tàu chiến cùng phe cản hoàn toàn
          }
          if (canBoardCarrier(occ, selectedPiece) && !occ.carried_by_id) {
            pushPickup(occ);
          }
          continue; // Đi vượt quân đất liền cùng phe ở bờ biển/bờ sông!
        } else {
          if (occ.type === 'NAVY') {
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (hải chiến bắt buộc thế chỗ)');
          } else if (step <= maxGun) {
            if (isHqShelteringCommander(occ, allPieces)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (pháo hạm bắn đất liền tại chỗ)');
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (hải quân đổ bộ lên bờ)');
            }
            shoreCaptureCoords.add(`${nx},${ny}`);
          }
          break; // Bị tàu/quân địch ở hải lộ cản lại
        }
      }

      // Pha 2: Pháo hạm bắn vào đất liền / mục tiêu khác (tầm 3, Anh hùng: 4) xuyên vật cản/đất liền
      for (let step = 1; step <= maxGun; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;
        if (shoreCaptureCoords.has(`${nx},${ny}`)) continue;
        const occ = getPieceAt(nx, ny);
        if (occ && occ.side !== side && occ.type !== 'NAVY') {
          pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (pháo hạm bắn đất liền tại chỗ)');
        }
      }
    }
  }

  // =========================================================================
  // BỘ LỌC TỐI THƯỢNG: Loại bỏ mọi nước đi khiến Tư lệnh phe mình chết,
  // 2 Tư lệnh đối mặt nhau trực tiếp, hoặc để lộ Tư lệnh bị chiếu / bị ăn (DEC-019)
  // =========================================================================
  const ownCmdBefore = allPieces.find((p) => p.is_alive && p.side === side && p.type === 'COMMANDER');
  const legalActions = candidateActions.filter((act) => {
    const simPieces = simulateAction(act, allPieces);
    if (ownCmdBefore && !simPieces.some((p) => p.is_alive && p.piece_id === ownCmdBefore.piece_id)) {
      return false;
    }
    if (isCommandersFacing(simPieces)) return false;
    if (isCommanderInCheck(simPieces, side)) return false;
    return true;
  });

  return legalActions;
}

export function evaluateTurnHandoffOutcome(
  pieces: PieceState[],
  nextSide: 'RED' | 'BLUE'
): {
  enemyHasLegalMove: boolean;
  isEnemyInCheck: boolean;
  isCheckmate: boolean;
  isStalemate: boolean;
} {
  const hasCmd = pieces.some((p) => p.is_alive && p.side === nextSide && p.type === 'COMMANDER');
  const isEnemyInCheck = hasCmd ? isCommanderInCheck(pieces, nextSide) : false;
  if (!hasCmd) {
    return {
      enemyHasLegalMove: true,
      isEnemyInCheck: false,
      isCheckmate: false,
      isStalemate: false,
    };
  }
  const enemyAllAlive = pieces.filter((p) => p.is_alive && p.side === nextSide);
  let enemyHasLegalMove = false;
  for (const ep of enemyAllAlive) {
    if (getMockLegalActions(ep, pieces, true).length > 0) {
      enemyHasLegalMove = true;
      break;
    }
    if (
      ep.carried_by_id == null &&
      ep.carrying_piece_ids &&
      ep.carrying_piece_ids.length > 0 &&
      canCarrierLeaveCargoBehind(ep, pieces) &&
      getMockLegalActions(ep, pieces, false).length > 0
    ) {
      enemyHasLegalMove = true;
      break;
    }
  }
  const isCheckmate = !enemyHasLegalMove && isEnemyInCheck;
  const isStalemate = !enemyHasLegalMove && !isEnemyInCheck;
  return { enemyHasLegalMove, isEnemyInCheck, isCheckmate, isStalemate };
}

/**
 * Apply action, auto-promote heroes, and update board state
 */
export function applyMockAction(
  action: LegalAction,
  pieces: PieceState[],
  evaluateTurnEnd: boolean = true
): {
  nextPieces: PieceState[];
  event: GameEvent;
  capturedPiece: PieceState | null;
} {
  if (action.action_type === 'END_TURN') {
    const activeSide: 'RED' | 'BLUE' =
      (pieces.find((p) => p.is_alive && p.piece_id === action.piece_id)?.side) || 'RED';
    const nextSide = activeSide === 'RED' ? 'BLUE' : 'RED';
    const outcome = evaluateTurnEnd
      ? evaluateTurnHandoffOutcome(pieces, nextSide)
      : { enemyHasLegalMove: true, isEnemyInCheck: false, isCheckmate: false, isStalemate: false };
    const scoreDelta = { RED: 0, BLUE: 0 };
    let notation = action.notation || 'CONFIRM_DEPLOYMENT';
    if (outcome.isCheckmate) {
      scoreDelta[activeSide] += 50;
      if (!notation.includes('#')) notation = `${notation} #`;
    }
    return {
      nextPieces: pieces,
      capturedPiece: null,
      event: {
        event_id: `evt_${Date.now()}`,
        event_type: 'PIECE_MOVED',
        actor_id: action.piece_id || 'COMPOUND',
        target_id: null,
        notation,
        score_delta: scoreDelta,
        details: {
          action_type: 'END_TURN',
          is_check: outcome.isEnemyInCheck,
          is_checkmate: outcome.isCheckmate,
          is_stalemate: outcome.isStalemate,
          hero_promoted: false,
        },
      },
    };
  }

  const actor = pieces.find((p) => p.piece_id === action.piece_id);
  let captured: PieceState | null = null;
  const scoreDelta: { RED: number; BLUE: number } = { RED: 0, BLUE: 0 };
  const enemySide = actor ? (actor.side === 'RED' ? 'BLUE' : 'RED') : 'BLUE';
  const actorOrigin = actor ? getRootCarrier(actor, pieces).position : action.from_pos;

  const enemyAaZone = actor ? getAirDefenseZones(enemySide, pieces) : [];
  const enemyAaUnits = actor
    ? pieces.filter(
      (p) =>
        p.is_alive &&
        !p.carried_by_id &&
        p.side === enemySide &&
        (p.type === 'ANTI_AIR' || p.type === 'MISSILE' || p.type === 'NAVY')
    )
    : [];
  const isActorAircraft = actor && actor.type === 'AIRCRAFT' && !actor.is_hero;
  const isTargetAaUnit = enemyAaUnits.some(
    (u) => u.position.x === action.to_pos.x && u.position.y === action.to_pos.y
  );
  const isInAaZone =
    isActorAircraft &&
    actor &&
    (isTargetAaUnit || isAircraftFlightAffectedByAa(actorOrigin, action.to_pos, enemyAaZone, enemyAaUnits));

  const allCarriedIds = getAllCarriedPieceIds(action.piece_id, pieces);
  const allCarriedSet = new Set(allCarriedIds);
  const target = action.target_piece_id
    ? pieces.find((p) => p.piece_id === action.target_piece_id)
    : undefined;
  const targetDescendants = new Set(target ? getAllCarriedPieceIds(target.piece_id, pieces) : []);
  const isCarrierPickingUp =
    action.action_type === 'BOARD' &&
    actor != null &&
    target != null &&
    canBoardCarrier(target, actor);

  const leaveBehind =
    actor != null &&
    ((action.carry_cargo === false &&
      (action.action_type === 'MOVE' || action.action_type === 'CAPTURE_REPLACE') &&
      allCarriedSet.size > 0) ||
      (actor.type === 'HEADQUARTERS' &&
        (action.action_type === 'MOVE' || action.action_type === 'CAPTURE_REPLACE') &&
        allCarriedSet.size > 0));
  const detachedMap = leaveBehind && actor ? detachCargoMap(actor, actorOrigin, pieces) : new Map();

  let nextPieces = pieces.map((p) => {
    if (
      (p.carrying_piece_ids && p.carrying_piece_ids.includes(action.piece_id)) ||
      (actor && actor.carried_by_id === p.piece_id)
    ) {
      return {
        ...p,
        carrying_piece_ids: (p.carrying_piece_ids || []).filter((id) => id !== action.piece_id),
      };
    }

    // 1. Hành động BOARD (Lên phương tiện / Trú ẩn Sở chỉ huy / Phương tiện đón cõng quân)
    if (action.action_type === 'BOARD') {
      if (isCarrierPickingUp) {
        if (p.piece_id === action.piece_id) {
          return { ...p, position: { ...action.to_pos }, carried_by_id: null };
        }
        if (p.piece_id === action.target_piece_id) {
          return { ...p, position: { ...action.to_pos }, carried_by_id: action.piece_id };
        }
        if (allCarriedSet.has(p.piece_id) || targetDescendants.has(p.piece_id)) {
          return { ...p, position: { ...action.to_pos } };
        }
      } else {
        if (p.piece_id === action.piece_id) {
          return {
            ...p,
            carried_by_id: action.target_piece_id || null,
            position: { ...action.to_pos },
          };
        }
        if (p.piece_id === action.target_piece_id) {
          const cur = p.carrying_piece_ids || [];
          return {
            ...p,
            carrying_piece_ids: cur.includes(action.piece_id) ? cur : [...cur, action.piece_id],
          };
        }
        if (allCarriedSet.has(p.piece_id)) {
          return { ...p, position: { ...action.to_pos } };
        }
      }
      return p;
    }

    // 2. Quân này là mục tiêu bị tấn công
    if (action.target_piece_id && p.piece_id === action.target_piece_id) {
      captured = { ...p, is_alive: false, carried_by_id: null };
      let scoreValue = (PIECE_SCORES[p.type] || 10) + (p.is_hero ? 10 : 0);
      if (p.type === 'COMMANDER') {
        scoreValue += 50;
      }
      if (actor) {
        scoreDelta[actor.side] += scoreValue;
      }
      return { ...p, is_alive: false, carried_by_id: null };
    }

    // 3 & 4. Quân đang ngồi trên mục tiêu bị tấn công (kể cả lồng nhau)
    if (
      action.target_piece_id &&
      targetDescendants.has(p.piece_id)
    ) {
      if (target && target.type === 'HEADQUARTERS') {
        if (p.carried_by_id === target.piece_id) {
          return { ...p, carried_by_id: null, is_alive: true, position: { ...target.position } };
        }
        return { ...p, position: { ...target.position } };
      }
      const scoreValue = (PIECE_SCORES[p.type] || 10) + (p.is_hero ? 10 : 0);
      if (actor) {
        scoreDelta[actor.side] += scoreValue;
      }
      return { ...p, is_alive: false, carried_by_id: null };
    }

    // 5. Quân thực hiện hành động
    if (p.piece_id === action.piece_id) {
      if (isInAaZone) {
        scoreDelta[enemySide] += PIECE_SCORES.AIRCRAFT;
        return {
          ...p,
          is_alive: false,
          position: { ...action.to_pos },
          carried_by_id: null,
        };
      }
      if (action.action_type === 'CAPTURE_STAND') {
        return p;
      }
      return {
        ...p,
        position: { ...action.to_pos },
        carried_by_id: null,
      };
    }

    // 6. Quân đang được cõng bởi phương tiện di chuyển (hoặc chết theo nếu máy bay bị bắn hạ)
    if (allCarriedSet.has(p.piece_id) && action.action_type !== 'CAPTURE_STAND') {
      const detached = detachedMap.get(p.piece_id);
      if (detached) {
        return {
          ...p,
          carried_by_id: detached.carriedById,
          position: { ...detached.position },
        };
      }
      if (isInAaZone) {
        scoreDelta[enemySide] += (PIECE_SCORES[p.type] || 10) + (p.is_hero ? 10 : 0);
        return { ...p, is_alive: false, carried_by_id: null };
      }
      return {
        ...p,
        position: { ...action.to_pos },
      };
    }

    return p;
  });

  // Đồng bộ 2 chiều và tọa độ quân được chở theo quân gốc
  nextPieces = nextPieces.map((p) => {
    const cargo = nextPieces
      .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
      .map((other) => other.piece_id);
    if (p.is_alive && p.carried_by_id != null) {
      const root = getRootCarrier(p, nextPieces);
      return { ...p, carrying_piece_ids: cargo, position: { ...root.position } };
    }
    return { ...p, carrying_piece_ids: cargo };
  });

  // =========================================================================
  // TỰ ĐỘNG PHONG ANH HÙNG (RULE-HERO-001, BUG-HQ-001, DEC-015 & Phong trễ HQ)
  // =========================================================================
  nextPieces = applyHeroPromotions(nextPieces);

  // =========================================================================
  // PHONG ANH HÙNG KHI CHIẾU TƯ LỆNH ĐỐI PHƯƠNG (RULE-HERO-CHECK)
  // =========================================================================
  const actorSide = actor ? actor.side : 'RED';
  const enemySideOfActor = actorSide === 'RED' ? 'BLUE' : 'RED';
  const enemyCmd = nextPieces.find(
    (p) => p.is_alive && p.side === enemySideOfActor && p.type === 'COMMANDER'
  );

  let actorCheckedCommander = false;
  let actorWasPromoted = false;

  if (enemyCmd && isCommanderInCheck(nextPieces, enemySideOfActor)) {
    const cmdOrigin = getRootCarrier(enemyCmd, nextPieces).position;
    const pieceMapAfter = new Map<string, PieceState>();
    for (const np of nextPieces) {
      if (np.is_alive && !np.carried_by_id) {
        pieceMapAfter.set(`${np.position.x},${np.position.y}`, np);
      }
    }
    const checkingPieceIds = new Set<string>();
    for (const np of nextPieces) {
      if (np.is_alive && np.side === actorSide && np.type !== 'COMMANDER') {
        if (pieceThreatensSquare(nextPieces, np, cmdOrigin.x, cmdOrigin.y, pieceMapAfter)) {
          checkingPieceIds.add(np.piece_id);
          if (np.piece_id === action.piece_id) {
            actorCheckedCommander = true;
          }
        }
      }
    }

    if (checkingPieceIds.size > 0) {
      nextPieces = nextPieces.map((p) => {
        if (checkingPieceIds.has(p.piece_id) && p.type !== 'COMMANDER') {
          if (!p.is_hero && p.piece_id === action.piece_id) {
            actorWasPromoted = true;
          }
          return { ...p, is_hero: true };
        }
        return p;
      });
    }
  }

  let eventType: EventType = captured ? 'PIECE_CAPTURED' : 'PIECE_MOVED';
  let notation = action.notation;
  let deadPieceForRecord: PieceState | null = captured;

  if (actorCheckedCommander) {
    const actorSym = (actor && PIECE_NOTATION_SYMBOL[actor.type]) || 'B';
    if (!notation.includes('>')) {
      if (actorWasPromoted) {
        notation = `${notation} > **${actorSym}**`;
      } else {
        notation = `${notation} >`;
      }
    }
    if (eventType === 'PIECE_MOVED') {
      eventType = 'HERO_PROMOTION';
    }
  }

  if (isInAaZone && isActorAircraft && actor) {
    const actorSym = PIECE_NOTATION_SYMBOL[actor.type] || 'K';
    const fromNot = formatCoordinateNotation(actorOrigin);
    const toNot = formatCoordinateNotation(action.to_pos);

    if (captured || action.target_piece_id) {
      eventType = 'AIR_EXCHANGE';
      const targetUnit: PieceState | undefined = (captured as PieceState | null) || (action.target_piece_id ? pieces.find((p) => p.piece_id === action.target_piece_id) : undefined);
      const targetSym = targetUnit ? (PIECE_NOTATION_SYMBOL[targetUnit.type] || 'B') : 'B';
      notation = `${actorSym} ${fromNot} >< ${targetSym} ${toNot}`;
    } else {
      eventType = 'AIR_SHOT_DOWN';
      notation = `${actorSym} ${fromNot} @" ${toNot}`;
      deadPieceForRecord = { ...actor, is_alive: false, position: { ...action.to_pos } };
    }
  }

  // =========================================================================
  // CHIẾU HẾT TƯ LỆNH (CHECKMATE) & HÒA CỜ BÍ (STALEMATE - DEC-020)
  // =========================================================================
  const deadTarget = (captured as PieceState | null) || deadPieceForRecord;
  let isEnemyInCheck = isCommanderInCheck(nextPieces, enemySideOfActor);
  let isCheckmate = false;
  let isStalemate = false;

  if (evaluateTurnEnd && !(deadTarget && deadTarget.type === 'COMMANDER')) {
    const outcome = evaluateTurnHandoffOutcome(nextPieces, enemySideOfActor);
    isEnemyInCheck = outcome.isEnemyInCheck;
    isCheckmate = outcome.isCheckmate;
    isStalemate = outcome.isStalemate;
    if (isCheckmate) {
      scoreDelta[actorSide] += 50;
      if (!notation.includes('#')) {
        notation = `${notation} #`;
      }
    }
  }

  const event: GameEvent = {
    event_id: `evt_${Date.now()}`,
    event_type: eventType,
    actor_id: action.piece_id,
    target_id: action.target_piece_id || (isInAaZone ? action.piece_id : null),
    notation,
    score_delta: scoreDelta,
    details: {
      action_type: action.action_type,
      is_check: actorCheckedCommander || isEnemyInCheck,
      is_checkmate: isCheckmate,
      is_stalemate: isStalemate,
      hero_promoted: actorWasPromoted,
    },
  };

  return {
    nextPieces,
    event,
    capturedPiece: captured || deadPieceForRecord,
  };
}

/**
 * Lựa chọn nước đi hợp lệ và an toàn cho tác tử AI (DEC-019, DEC-020 & Tổ hợp cõng quân):
 * - Thu thập toàn bộ nước đi hợp lệ ở trạng thái hiện tại, bao gồm cả quân đang được cõng,
 *   cả lựa chọn cõng quân đi cùng lẫn tách lẻ bỏ lại quân (carry_cargo = true/false),
 *   và các nước đi tiếp theo / END_TURN khi đang ở lượt tổ hợp STACK_ACTIVE.
 * - Tuyệt đối không fallback sang nước đi tự sát / lộ Tư lệnh cho đối phương ăn.
 */
export function selectSmartAiAction(
  pieces: PieceState[],
  side: 'RED' | 'BLUE',
  activeCompound: ActiveCompoundState | null = null
): LegalAction | null {
  const allAliveSide = pieces.filter((p) => p.side === side && p.is_alive);
  let candidatePoolPieces = allAliveSide;

  if (activeCompound) {
    candidatePoolPieces = allAliveSide.filter(
      (p) =>
        activeCompound.memberIds.includes(p.piece_id) &&
        !activeCompound.movedPieceIds.includes(p.piece_id) &&
        p.position.x === activeCompound.originPos.x &&
        p.position.y === activeCompound.originPos.y
    );
  }

  const allActions: LegalAction[] = [];
  const seenKeys = new Set<string>();
  const addUniqueActions = (list: LegalAction[]) => {
    for (const act of list) {
      const key = `${act.action_type}|${act.piece_id}|${act.to_pos.x},${act.to_pos.y}|${act.target_piece_id || ''}|${act.carry_cargo ?? true}`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        allActions.push(act);
      }
    }
  };

  for (const ap of candidatePoolPieces) {
    addUniqueActions(getMockLegalActions(ap, pieces, true));
    if (
      ap.carried_by_id == null &&
      ap.type !== 'HEADQUARTERS' &&
      ap.carrying_piece_ids &&
      ap.carrying_piece_ids.length > 0 &&
      canCarrierLeaveCargoBehind(ap, pieces)
    ) {
      addUniqueActions(getMockLegalActions(ap, pieces, false));
    }
  }

  const cmd = pieces.find((p) => p.is_alive && p.side === side && p.type === 'COMMANDER');

  const safeActions: LegalAction[] = [];
  for (const act of allActions) {
    const sim = simulateAction(act, pieces);
    if (cmd && !sim.some((p) => p.is_alive && p.piece_id === cmd.piece_id)) continue;
    if (isCommandersFacing(sim) || isCommanderInCheck(sim, side)) continue;
    safeActions.push(act);
  }

  if (activeCompound) {
    const stackPool: LegalAction[] = [...safeActions];
    if (!isCommandersFacing(pieces) && !isCommanderInCheck(pieces, side)) {
      stackPool.push({
        action_id: `end_turn_${side}_${Date.now()}`,
        action_type: 'END_TURN',
        piece_id: candidatePoolPieces[0]?.piece_id || activeCompound.memberIds[0] || 'COMPOUND',
        from_pos: { ...activeCompound.originPos },
        to_pos: { ...activeCompound.originPos },
        target_piece_id: null,
        notation: 'CONFIRM_DEPLOYMENT',
        description: 'Hoàn tất lượt tổ hợp',
        carry_cargo: true,
      });
    }
    if (stackPool.length === 0) return null;
    return stackPool[Math.floor(Math.random() * stackPool.length)];
  }

  if (safeActions.length === 0) return null;

  const isInCheck = isCommanderInCheck(pieces, side);

  if (isInCheck) {
    const blockingOrCapturing = safeActions.filter((a) => !cmd || a.piece_id !== cmd.piece_id);
    const shelterActions = safeActions.filter(
      (a) => cmd && a.piece_id === cmd.piece_id && a.action_type === 'BOARD'
    );
    const cmdEscapeActions = safeActions.filter(
      (a) => cmd && a.piece_id === cmd.piece_id && a.action_type !== 'BOARD'
    );

    if (blockingOrCapturing.length > 0) {
      const preferred = [...blockingOrCapturing, ...shelterActions, ...cmdEscapeActions];
      return preferred[Math.floor(Math.random() * preferred.length)];
    } else if (shelterActions.length > 0) {
      return shelterActions[Math.floor(Math.random() * shelterActions.length)];
    } else if (cmdEscapeActions.length > 0) {
      return cmdEscapeActions[Math.floor(Math.random() * cmdEscapeActions.length)];
    }
    return safeActions[Math.floor(Math.random() * safeActions.length)];
  } else {
    const tacticalActions = safeActions.filter((a) => !cmd || a.piece_id !== cmd.piece_id);
    const shelterActions = safeActions.filter(
      (a) => cmd && a.piece_id === cmd.piece_id && a.action_type === 'BOARD'
    );

    if (tacticalActions.length > 0) {
      const preferred = [...tacticalActions, ...shelterActions];
      return preferred[Math.floor(Math.random() * preferred.length)];
    }
    return safeActions[Math.floor(Math.random() * safeActions.length)];
  }
}
