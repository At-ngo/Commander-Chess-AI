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

import { PieceState, LegalAction, ActionType, GameEvent, Position, EventType } from '../types';
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
 * Tính toán toàn bộ các giao điểm thuộc Vành đai lửa phòng không của một phe (RULE-AA-001, RULE-HERO-003, Q6)
 */
export function getAirDefenseZones(targetSide: 'RED' | 'BLUE', allPieces: PieceState[]): { x: number; y: number }[] {
  const aaUnits = allPieces.filter(
    (p) =>
      p.is_alive &&
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
 */
export function isCommandersFacing(allPieces: PieceState[]): boolean {
  const redCmd = allPieces.find((p) => p.is_alive && p.side === 'RED' && p.type === 'COMMANDER');
  const blueCmd = allPieces.find((p) => p.is_alive && p.side === 'BLUE' && p.type === 'COMMANDER');

  if (!redCmd || !blueCmd) return false;

  // Nếu một trong hai Tư lệnh đang trú ẩn trong Sở chỉ huy thì Sở chỉ huy che chở hoàn toàn (Q9)
  const isRedInHq = allPieces.some(
    (p) =>
      p.is_alive &&
      p.side === 'RED' &&
      p.type === 'HEADQUARTERS' &&
      p.position.x === redCmd.position.x &&
      p.position.y === redCmd.position.y &&
      redCmd.carried_by_id === p.piece_id
  );
  const isBlueInHq = allPieces.some(
    (p) =>
      p.is_alive &&
      p.side === 'BLUE' &&
      p.type === 'HEADQUARTERS' &&
      p.position.x === blueCmd.position.x &&
      p.position.y === blueCmd.position.y &&
      blueCmd.carried_by_id === p.piece_id
  );
  if (isRedInHq || isBlueInHq) return false;

  // 1. Cùng cột dọc (x giống nhau)
  if (redCmd.position.x === blueCmd.position.x) {
    const x = redCmd.position.x;
    const minY = Math.min(redCmd.position.y, blueCmd.position.y);
    const maxY = Math.max(redCmd.position.y, blueCmd.position.y);

    const hasObstacle = allPieces.some(
      (p) => p.is_alive && p.position.x === x && p.position.y > minY && p.position.y < maxY
    );
    if (!hasObstacle) return true; // Lộ mặt Tư lệnh trên cột dọc!
  }

  // 2. Cùng hàng ngang (y giống nhau)
  if (redCmd.position.y === blueCmd.position.y) {
    const y = redCmd.position.y;
    const minX = Math.min(redCmd.position.x, blueCmd.position.x);
    const maxX = Math.max(redCmd.position.x, blueCmd.position.x);

    const hasObstacle = allPieces.some(
      (p) => p.is_alive && p.position.y === y && p.position.x > minX && p.position.x < maxX
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
  if (hq.position.x === enemyCmd.position.x) {
    const x = hq.position.x;
    const minY = Math.min(hq.position.y, enemyCmd.position.y);
    const maxY = Math.max(hq.position.y, enemyCmd.position.y);
    const hasObstacle = allPieces.some(
      (p) =>
        p.is_alive &&
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
    const hasObstacle = allPieces.some(
      (p) =>
        p.is_alive &&
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
 * Kiểm tra xem một ô (targetX, targetY) có đang bị bất kỳ quân địch nào tấn công/chiếu không.
 * (Dùng để ngăn Tư lệnh di chuyển vào ô bị đối phương ăn, kiểm tra Chiếu và Chiếu hết)
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
    if (!p.is_alive || p.side !== enemySide || p.carried_by_id) continue;

    const px = p.position.x;
    const py = p.position.y;
    const dx = targetX - px;
    const dy = targetY - py;
    const adx = Math.abs(dx);
    const ady = Math.abs(dy);

    if (adx === 0 && ady === 0) continue;

    const isOrth = adx === 0 || ady === 0;
    const isDiag = adx === ady;
    if (!isOrth && !isDiag) continue;

    const dist = Math.max(adx, ady);
    const stepX = dx === 0 ? 0 : dx > 0 ? 1 : -1;
    const stepY = dy === 0 ? 0 : dy > 0 ? 1 : -1;

    // 1. COMMANDER
    if (p.type === 'COMMANDER') {
      if (isOrth) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
      if ((isOrth && dist === 1) || (p.is_hero && dist <= 2)) {
        return true;
      }
    }

    // 2. INFANTRY & ENGINEER
    else if (p.type === 'INFANTRY' || p.type === 'ENGINEER') {
      const dirsOk = p.is_hero ? true : isOrth;
      const maxR = p.is_hero ? 2 : 1;
      if (dirsOk && dist <= maxR) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
    }

    // 3. MILITIA
    else if (p.type === 'MILITIA') {
      const maxR = p.is_hero ? 2 : 1;
      if (dist <= maxR) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
    }

    // 4. ANTI_AIR
    else if (p.type === 'ANTI_AIR') {
      const dirsOk = p.is_hero ? true : isOrth;
      const maxR = p.is_hero ? 2 : 1;
      if (dirsOk && dist <= maxR) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
    }

    // 5. TANK
    else if (p.type === 'TANK') {
      const dirsOk = p.is_hero ? true : isOrth;
      const maxR = p.is_hero ? 3 : 2;
      if (dirsOk && dist <= maxR) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
    }

    // 6. MISSILE
    else if (p.type === 'MISSILE') {
      const maxR = isOrth ? (p.is_hero ? 3 : 2) : (p.is_hero ? 2 : 1);
      if (dist <= maxR) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
    }

    // 7. ARTILLERY
    else if (p.type === 'ARTILLERY') {
      const maxR = p.is_hero ? 4 : 3;
      if (dist <= maxR) {
        // Pháo binh bắn xuyên qua mọi vật cản khi ăn quân!
        return true;
      }
    }

    // 8. AIRCRAFT
    else if (p.type === 'AIRCRAFT') {
      const maxR = p.is_hero ? 5 : 4;
      if (dist <= maxR) {
        // Máy bay bay xuyên qua mọi vật cản!
        return true;
      }
    }

    // 9. NAVY
    else if (p.type === 'NAVY') {
      const maxR = p.is_hero ? 4 : 3;
      if (dist <= maxR && canNavyOccupySquare(px, py)) {
        if (isDiag && isNavyLandDiagonal(px, py, targetX, targetY)) {
          continue;
        }
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          const occ = pieceMap.get(`${px + stepX * s},${py + stepY * s}`);
          if (occ && occ.type === 'NAVY') {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
    }

    // 10. HEADQUARTERS
    else if (p.type === 'HEADQUARTERS') {
      if (p.is_hero && dist <= 2) {
        let blocked = false;
        for (let s = 1; s < dist; s++) {
          if (pieceMap.has(`${px + stepX * s},${py + stepY * s}`)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) return true;
      }
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
  if (cmd.carried_by_id) {
    const carrier = pieces.find((p) => p.is_alive && p.piece_id === cmd.carried_by_id);
    if (!carrier) return false;
    if (carrier.type === 'HEADQUARTERS') {
      return false; // Trú ẩn an toàn trong Sở chỉ huy (phải diệt Sở chỉ huy trước)
    }
    const enemySide = side === 'RED' ? 'BLUE' : 'RED';
    return isSquareAttackedByEnemy(pieces, carrier.position.x, carrier.position.y, enemySide);
  }
  const enemySide = side === 'RED' ? 'BLUE' : 'RED';
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

/**
 * Mô phỏng trạng thái sau hành động để kiểm tra tính hợp lệ
 */
function simulateAction(action: LegalAction, pieces: PieceState[]): PieceState[] {
  const actor = pieces.find((p) => p.piece_id === action.piece_id);
  const target = action.target_piece_id
    ? pieces.find((p) => p.piece_id === action.target_piece_id)
    : undefined;
  const isCarrierPickingUp =
    action.action_type === 'BOARD' &&
    actor != null &&
    target != null &&
    canBoardCarrier(target, actor);
  const allCarriedIds = getAllCarriedPieceIds(action.piece_id, pieces);

  const updated = pieces.map((p) => {
    // Nếu phương tiện đang chở quân vừa tách ra di chuyển/triển khai
    if (
      (p.carrying_piece_ids && p.carrying_piece_ids.includes(action.piece_id)) ||
      (actor && actor.carried_by_id === p.piece_id)
    ) {
      return {
        ...p,
        carrying_piece_ids: (p.carrying_piece_ids || []).filter((id) => id !== action.piece_id),
      };
    }
    if (action.target_piece_id && p.piece_id === action.target_piece_id) {
      if (action.action_type === 'BOARD') {
        if (isCarrierPickingUp) {
          return {
            ...p,
            position: { ...action.to_pos },
            carried_by_id: action.piece_id,
          };
        } else {
          const cur = p.carrying_piece_ids || [];
          return {
            ...p,
            carrying_piece_ids: cur.includes(action.piece_id) ? cur : [...cur, action.piece_id],
          };
        }
      }
      return { ...p, is_alive: false };
    }
    if (p.piece_id === action.piece_id) {
      if (action.action_type === 'CAPTURE_STAND') return p;
      if (action.action_type === 'BOARD') {
        if (isCarrierPickingUp) {
          return {
            ...p,
            position: { ...action.to_pos },
            carried_by_id: null,
          };
        } else {
          return {
            ...p,
            position: { ...action.to_pos },
            carried_by_id: action.target_piece_id || null,
          };
        }
      }
      return { ...p, position: { ...action.to_pos }, carried_by_id: null };
    }
    // Quân được cõng bởi phương tiện di chuyển
    if (allCarriedIds.includes(p.piece_id) && action.action_type !== 'CAPTURE_STAND') {
      if (action.carry_cargo === false) {
        // Phương tiện đi một mình, để lại quân cõng ở vị trí xuất phát!
        if (p.carried_by_id === action.piece_id) {
          const otherCarriersAtOrigin = pieces.filter(
            (other) =>
              other.is_alive &&
              other.piece_id !== action.piece_id &&
              !allCarriedIds.includes(other.piece_id) &&
              other.position.x === action.from_pos.x &&
              other.position.y === action.from_pos.y &&
              (other.type === 'AIRCRAFT' || other.type === 'NAVY' || other.type === 'TANK')
          );
          const newCarrier = otherCarriersAtOrigin.find((c) => canBoardCarrier(p, c));
          return {
            ...p,
            position: { ...action.from_pos },
            carried_by_id: newCarrier ? newCarrier.piece_id : null,
          };
        }
        return {
          ...p,
          position: { ...action.from_pos },
        };
      }
      return { ...p, position: { ...action.to_pos } };
    }
    return p;
  });

  // Đồng bộ tính nhất quán 2 chiều tuyệt đối giữa carried_by_id và carrying_piece_ids
  return updated.map((p) => ({
    ...p,
    carrying_piece_ids: updated
      .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
      .map((other) => other.piece_id),
  }));
}

/**
 * Kiểm tra xem phương tiện có thể đi một mình và để lại quân cõng ở vị trí xuất phát không
 * (Quy tắc 2: Cấm tách lẻ bỏ lại 2 quân không có khả năng chở lẫn nhau mà không có phương tiện)
 */
export function canCarrierLeaveCargoBehind(carrier: PieceState, allPieces: PieceState[]): boolean {
  const directPassengers = allPieces.filter(
    (p) => p.is_alive && p.carried_by_id === carrier.piece_id
  );
  if (directPassengers.length === 0) {
    return true;
  }
  // Nếu phương tiện đang ở ngoài biển (x <= 1): không thể bỏ lại quân bộ trên biển nếu không có tàu chiến khác đón
  if (isSeaSquare(carrier.position.x)) {
    const hasOtherNavy = allPieces.some(
      (p) =>
        p.is_alive &&
        p.piece_id !== carrier.piece_id &&
        p.position.x === carrier.position.x &&
        p.position.y === carrier.position.y &&
        p.type === 'NAVY'
    );
    if (!hasOtherNavy) return false;
  }
  if (directPassengers.length === 1) {
    return true;
  }
  // Nếu có từ 2 quân trở lên: kiểm tra xem tại vị trí xuất phát có phương tiện nào khác không
  const otherCarriersAtOrigin = allPieces.filter(
    (p) =>
      p.is_alive &&
      p.piece_id !== carrier.piece_id &&
      p.position.x === carrier.position.x &&
      p.position.y === carrier.position.y &&
      (p.type === 'AIRCRAFT' || p.type === 'NAVY' || p.type === 'TANK')
  );
  if (otherCarriersAtOrigin.length > 0) {
    return true; // Có phương tiện khác ở lại để nhận cõng
  }
  const [p1, p2] = directPassengers;
  return canBoardCarrier(p2, p1) || canBoardCarrier(p1, p2);
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

  const candidateActions: LegalAction[] = [];
  const { x, y } = selectedPiece.position;
  const side = selectedPiece.side;
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
    // Tên lửa và máy bay KHÔNG thể di chuyển/đáp trên biển trống (x <= 1)
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

  const pushMove = (nx: number, ny: number, labelSuffix: string = '') => {
    const toNot = formatCoordinateNotation({ x: nx, y: ny });
    const isCarrier = selectedPiece.carrying_piece_ids && selectedPiece.carrying_piece_ids.length > 0;
    const carryDesc = isCarrier
      ? (carryCargo ? ' (mang theo quân cõng)' : ' (tách lẻ đi một mình, để lại quân)')
      : '';
    candidateActions.push({
      action_id: `m_${selectedPiece.piece_id}_${nx}_${ny}_${carryCargo ? 'with' : 'solo'}`,
      action_type: 'MOVE',
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { x: nx, y: ny },
      target_piece_id: null,
      notation: `${pieceSymbol} ${fromNot} _ ${toNot}`,
      description: `${pieceName} ${selectedPiece.carried_by_id ? 'triển khai rời phương tiện đến' : 'tiến đến'} ${toNot}${carryDesc}${labelSuffix}`,
      carry_cargo: carryCargo,
    });
  };

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
    const isCarrier = selectedPiece.carrying_piece_ids && selectedPiece.carrying_piece_ids.length > 0;
    const carryDesc = isCarrier && !isStand
      ? (carryCargo ? ' (mang theo quân cõng)' : ' (tách lẻ đi một mình, để lại quân)')
      : '';
    candidateActions.push({
      action_id: `c_${selectedPiece.piece_id}_${target.piece_id}_${actType}_${carryCargo ? 'with' : 'solo'}`,
      action_type: actType,
      piece_id: selectedPiece.piece_id,
      from_pos: { x, y },
      to_pos: { x: nx, y: ny },
      target_piece_id: target.piece_id,
      notation: `${pieceSymbol} ${fromNot} ${actionSymbol} ${targetSymbol} ${toNot}`,
      description: `${pieceName} ${isStand ? 'tấn công tại chỗ tiêu diệt' : 'tiến công bắt'
        } ${enemyName} tại ${toNot}${carryDesc}${labelSuffix}`,
      carry_cargo: isStand ? false : carryCargo,
    });
  };

  const pushBoard = (carrier: PieceState) => {
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
    const passengerName = PIECE_VIETNAMESE_NAMES[passenger.type] || passenger.type;
    const passengerSymbol = PIECE_NOTATION_SYMBOL[passenger.type] || passenger.type;
    const toNot = formatCoordinateNotation(passenger.position);
    candidateActions.push({
      action_id: `b_${selectedPiece.piece_id}_${passenger.piece_id}`,
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
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
          }
          break;
        }
      }
    }
    return candidateActions;
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
            if (isSeaSquare(nx)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (bắn tàu ngoài biển)');
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
            if (isSeaSquare(nx)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (bắn tàu ngoài biển)');
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
            if (isSeaSquare(nx)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (bắn tàu ngoài biển)');
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
            if (isSeaSquare(nx)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (bắn tàu ngoài biển)');
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
  // - Bắn tàu ngoài biển không thế chỗ; vượt sông sâu sang ô trống bị cấm (trừ khi ăn quân).
  // =========================================================================
  if (selectedPiece.type === 'MISSILE') {
    const straightRange = selectedPiece.is_hero ? 3 : 2;
    const diagRange = selectedPiece.is_hero ? 2 : 1;

    for (const [dx, dy] of ORTHOGONAL) {
      for (let step = 1; step <= straightRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          if (isSeaSquare(nx)) break; // Tên lửa không thể di chuyển trên biển
          if (canPieceCrossRiverToEmpty('MISSILE', x, y, nx, ny)) {
            pushMove(nx, ny);
          }
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (phóng tên lửa diệt tàu biển tại chỗ)');
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

    for (const [dx, dy] of DIAGONAL) {
      for (let step = 1; step <= diagRange; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        const occ = getPieceAt(nx, ny);
        if (!occ) {
          if (isSeaSquare(nx)) break; // Tên lửa không thể di chuyển trên biển
          if (canPieceCrossRiverToEmpty('MISSILE', x, y, nx, ny)) {
            pushMove(nx, ny);
          }
        } else {
          if (occ.side !== side) {
            if (isSeaSquare(nx)) {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (phóng tên lửa diệt tàu biển tại chỗ)');
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
          if (isSeaSquare(nx)) {
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (pháo kích diệt tàu biển tại chỗ)');
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
  // - Đi và ăn 8 hướng 1–4 đoạn, BAY VÀ ĂN XUYÊN QUÂN.
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
          break; // Không bay xuyên qua quân cùng phe
        } else {
          // Quân địch
          if (isSeaSquare(nx)) {
            // Mục tiêu trên biển: Bắt buộc thả bom tại chỗ (không thể thế chỗ vào nước)
            pushCapture(nx, ny, occ, 'CAPTURE_STAND', ` 💣 (ném bom tàu biển tại chỗ)${aaWarn}`);
          } else {
            if (occ.type === 'AIRCRAFT') {
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ` (không chiến bắt buộc thế chỗ)${aaWarn}`);
            } else {
              pushCapture(nx, ny, occ, 'CAPTURE_STAND', ` 💣 (ném bom tại chỗ)${aaWarn}`);
              pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ` 🎯 (oanh tạc thế chỗ)${aaWarn}`);
            }
          }
          break; // Dừng lại ở quân địch
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

        // Mô phỏng nước đi tới (nx, ny) để kiểm tra đối mặt Tư lệnh địch
        const simPieces = allPieces.map((p) =>
          p.piece_id === selectedPiece.piece_id ? { ...p, position: { x: nx, y: ny } } : p
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
            pushCapture(nx, ny, occ, 'CAPTURE_REPLACE');
          } else if (step === 1 && occ.side === side) {
            // Vào Sở chỉ huy (Q9)
            if (occ.type === 'HEADQUARTERS' && !occ.is_hero) {
              if (enemyCmd && !isHqFacingEnemyCommander(occ, enemyCmd, allPieces)) {
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
  // - BUG-NAVY-002 & Q8: Bắn quân bờ (isShoreSquare) BẮT BUỘC THẾ CHỖ. Bắn đất liền sâu BẮN TẠI CHỖ.
  // - BUG-NAVY-003: Tầm đánh Hải quân địch <= 4; Tầm đánh quân khác <= 3.
  // - BUG-NAVY-004: Đi xuyên qua quân đất liền trên bờ; BỊ CHẶN bởi Tàu chiến.
  // - BUG-NAVY-005 & Q5: Hải quân chỉ đánh hải quân địch ở phía trước (tàu đầu tiên chặn tàu sau).
  // =========================================================================
  if (selectedPiece.type === 'NAVY') {
    const maxStraight = selectedPiece.is_hero ? 5 : 4;

    for (const [dx, dy] of ALL_8) {
      let enemyNavyEncountered = false;

      for (let step = 1; step <= maxStraight; step++) {
        const nx = x + dx * step;
        const ny = y + dy * step;
        if (!isInsideBoard(nx, ny)) break;

        // CẤM di chuyển vào hoặc đi xuyên qua sông ngầm (BUG-NAVY-001)
        if (isFordSquare(nx, ny)) break;

        // CẤM di chuyển hoặc đi xuyên qua đường chéo thuộc đất liền (ví dụ (7, 2) đến (6, 3))
        const prevX = x + dx * (step - 1);
        const prevY = y + dy * (step - 1);
        if (isNavyLandDiagonal(prevX, prevY, nx, ny)) {
          break; // Bị đất liền chặn dừng tia ngay lập tức
        }

        const occ = getPieceAt(nx, ny);
        const isWater = canNavyOccupySquare(nx, ny);

        if (!occ) {
          if (!isWater) {
            // Giữa đường vướng đất liền: tàu chiến dừng tia ngay lập tức, không thể đi xuyên qua đất liền (RULE-NAVY-002)
            break;
          }
          if (!enemyNavyEncountered) {
            pushMove(nx, ny);
          }
        } else {
          if (occ.side === side) {
            if (occ.type === 'NAVY') {
              break; // Bị tàu chiến cùng phe cản hoàn toàn
            } else if (isWater && canBoardCarrier(occ, selectedPiece) && !occ.carried_by_id) {
              pushPickup(occ);
              break;
            } else {
              // Quân đất liền cùng phe trên bờ: chỉ đi xuyên qua nếu ô này là nước (RULE-SHORE-001)
              if (!isWater) break;
              continue;
            }
          } else {
            // Quân địch
            if (occ.type === 'NAVY') {
              if (!isWater) break;
              if (!enemyNavyEncountered) {
                // Tấn công tàu chiến địch (tối đa 4 đoạn)
                pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (hải chiến bắt buộc thế chỗ)');
                enemyNavyEncountered = true; // Chặn các tàu chiến địch phía sau trên tia này (Q5)
              }
              continue; // Tàu chiến cản bước di chuyển
            } else {
              // Quân địch trên đất liền hoặc máy bay (tối đa 3 đoạn, Anh hùng: 4 đoạn - BUG-NAVY-003)
              const maxLandStep = selectedPiece.is_hero ? 4 : 3;
              if (step <= maxLandStep) {
                if (isShoreSquare(nx, ny)) {
                  // Mục tiêu ở ngay bờ: BẮT BUỘC THẾ CHỖ (Q8)
                  pushCapture(nx, ny, occ, 'CAPTURE_REPLACE', ' (hải quân đổ bộ lên bờ)');
                } else {
                  // Mục tiêu ở đất liền sâu: BẮT BUỘC BẮN TẠI CHỖ (Q8 & BUG-NAVY-002)
                  pushCapture(nx, ny, occ, 'CAPTURE_STAND', ' (pháo hạm bắn đất liền tại chỗ)');
                }
              }
              if (!isWater) break; // Nếu không phải ô nước thì tia dừng lại
            }
          }
        }
      }
    }
  }

  // =========================================================================
  // BỘ LỌC TỐI THƯỢNG: Loại bỏ mọi nước đi khiến 2 Tư lệnh đối mặt nhau trực tiếp
  // hoặc khiến Tư lệnh phe mình rơi vào ô bị chiếu / bị ăn (DEC-019)
  // =========================================================================
  const legalActions = candidateActions.filter((act) => {
    const simPieces = simulateAction(act, allPieces);
    if (isCommandersFacing(simPieces)) return false;
    if (isCommanderInCheck(simPieces, side)) return false;
    return true;
  });

  return legalActions;
}

/**
 * Apply action, auto-promote heroes, and update board state
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
  const enemySide = actor ? (actor.side === 'RED' ? 'BLUE' : 'RED') : 'BLUE';

  const enemyAaZone = actor ? getAirDefenseZones(enemySide, pieces) : [];
  const enemyAaUnits = actor
    ? pieces.filter(
      (p) =>
        p.is_alive &&
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
    (isTargetAaUnit || isAircraftFlightAffectedByAa(actor.position, action.to_pos, enemyAaZone, enemyAaUnits));

  const allCarriedIds = getAllCarriedPieceIds(action.piece_id, pieces);
  const target = action.target_piece_id
    ? pieces.find((p) => p.piece_id === action.target_piece_id)
    : undefined;
  const isCarrierPickingUp =
    action.action_type === 'BOARD' &&
    actor != null &&
    target != null &&
    canBoardCarrier(target, actor);

  let nextPieces = pieces.map((p) => {
    // Nếu p là phương tiện đang cõng quân actor mà actor vừa tách ra di chuyển/triển khai
    if (
      (p.carrying_piece_ids && p.carrying_piece_ids.includes(action.piece_id)) ||
      (actor && actor.carried_by_id === p.piece_id)
    ) {
      return {
        ...p,
        carrying_piece_ids: (p.carrying_piece_ids || []).filter((id) => id !== action.piece_id),
      };
    }

    // 1. Nếu là hành động BOARD (Lên phương tiện / Trú ẩn Sở chỉ huy / Phương tiện đón cõng quân)
    if (action.action_type === 'BOARD') {
      if (isCarrierPickingUp) {
        if (p.piece_id === action.piece_id) {
          return {
            ...p,
            position: { ...action.to_pos },
            carried_by_id: null,
          };
        }
        if (p.piece_id === action.target_piece_id) {
          return {
            ...p,
            position: { ...action.to_pos },
            carried_by_id: action.piece_id,
          };
        }
        if (allCarriedIds.includes(p.piece_id)) {
          return {
            ...p,
            position: { ...action.to_pos },
          };
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
      }
      return p;
    }

    // 2. Nếu quân này là mục tiêu bị tấn công
    if (action.target_piece_id && p.piece_id === action.target_piece_id) {
      // NGOẠI LỆ ĐẶC BIỆT CHO SỞ CHỈ HUY (Q9 & BUG-HQ-001):
      // Nếu Tư lệnh đang trú ẩn trong HQ, HQ bị phá hủy nhưng Tư lệnh sống sót và lộ diện!
      const hasCommanderInside = pieces.some(
        (other) => other.is_alive && other.type === 'COMMANDER' && other.carried_by_id === p.piece_id
      );

      if (p.type === 'HEADQUARTERS' && hasCommanderInside) {
        captured = { ...p, is_alive: false };
        if (actor) {
          scoreDelta[actor.side] += PIECE_SCORES.HEADQUARTERS;
        }
        return { ...p, is_alive: false };
      }

      captured = { ...p, is_alive: false };
      let scoreValue = PIECE_SCORES[p.type] || 10;
      if (p.type === 'COMMANDER') {
        scoreValue += 50; // Thưởng 50 điểm khi tiêu diệt Tư lệnh
      }
      if (actor) {
        scoreDelta[actor.side] += scoreValue;
      }
      return { ...p, is_alive: false };
    }

    // 3. Nếu là Tư lệnh trong Sở chỉ huy bị phá hủy: Tư lệnh sống sót và lộ diện (Q9)
    if (
      action.target_piece_id &&
      p.type === 'COMMANDER' &&
      p.carried_by_id === action.target_piece_id
    ) {
      const targetUnit = pieces.find((u) => u.piece_id === action.target_piece_id);
      if (targetUnit && targetUnit.type === 'HEADQUARTERS') {
        return { ...p, carried_by_id: null, is_alive: true };
      }
    }

    // 4. Nếu là quân trên phương tiện khác bị phá hủy: bị tiêu diệt theo (RULE-TRANSPORT-001)
    if (action.target_piece_id && p.carried_by_id === action.target_piece_id) {
      const targetUnit = pieces.find((u) => u.piece_id === action.target_piece_id);
      if (targetUnit && targetUnit.type !== 'HEADQUARTERS') {
        const scoreValue = PIECE_SCORES[p.type] || 10;
        if (actor) {
          scoreDelta[actor.side] += scoreValue;
        }
        return { ...p, is_alive: false, carried_by_id: null };
      }
    }

    // 5. Nếu là quân thực hiện hành động
    if (p.piece_id === action.piece_id) {
      // Nếu máy bay thường bay vào vùng cấm bay:
      // a) Tấn công: 1 ĐỔI 1 (tiêu diệt mục tiêu VÀ máy bay bị diệt)
      // b) Di chuyển (MOVE): máy bay bị bắn hạ ngay lập tức
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
      // Nước đi hoặc ăn quân thế chỗ: Cập nhật vị trí mới
      return {
        ...p,
        position: { ...action.to_pos },
        carried_by_id: null,
      };
    }

    // 6. Nếu là quân đang được cõng bởi phương tiện di chuyển
    if (allCarriedIds.includes(p.piece_id) && action.action_type !== 'CAPTURE_STAND') {
      if (action.carry_cargo === false) {
        // Phương tiện đi một mình, để lại quân cõng ở vị trí xuất phát!
        if (p.carried_by_id === action.piece_id) {
          const otherCarriersAtOrigin = pieces.filter(
            (other) =>
              other.is_alive &&
              other.piece_id !== action.piece_id &&
              !allCarriedIds.includes(other.piece_id) &&
              other.position.x === action.from_pos.x &&
              other.position.y === action.from_pos.y &&
              (other.type === 'AIRCRAFT' || other.type === 'NAVY' || other.type === 'TANK')
          );
          const newCarrier = otherCarriersAtOrigin.find((c) => canBoardCarrier(p, c));
          return {
            ...p,
            position: { ...action.from_pos },
            carried_by_id: newCarrier ? newCarrier.piece_id : null,
          };
        }
        return {
          ...p,
          position: { ...action.from_pos },
        };
      }
      return {
        ...p,
        position: { ...action.to_pos },
      };
    }

    return p;
  });

  // Đảm bảo tính nhất quán 2 chiều tuyệt đối giữa carried_by_id và carrying_piece_ids:
  // Nếu quân được chở rời đi (carried_by_id == null) hoặc bị tiêu diệt (is_alive == false),
  // quân chở ngay lập tức trở về trạng thái bình thường (xóa sạch ID khỏi carrying_piece_ids, không còn +1/+2)!
  nextPieces = nextPieces.map((p) => ({
    ...p,
    carrying_piece_ids: nextPieces
      .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
      .map((other) => other.piece_id),
  }));

  // =========================================================================
  // TỰ ĐỘNG PHONG ANH HÙNG (RULE-HERO-001, BUG-HQ-001 & DEC-015):
  // 1. Quân cuối cùng bảo vệ Tư lệnh (không tính HQ) được phong Anh hùng!
  // 2. Chỉ khi còn duy nhất 1 Sở chỉ huy và Tư lệnh thì Sở chỉ huy mới được phong Anh hùng!
  //    Nếu còn 2 Sở chỉ huy thì KHÔNG phong Anh hùng cho Sở chỉ huy nào cả (DEC-015).
  // =========================================================================
  for (const side of ['RED', 'BLUE'] as const) {
    const alivePieces = nextPieces.filter((p) => p.is_alive && p.side === side);
    const nonCmdNonHq = alivePieces.filter((p) => p.type !== 'COMMANDER' && p.type !== 'HEADQUARTERS');
    const hqPieces = alivePieces.filter((p) => p.type === 'HEADQUARTERS');

    if (nonCmdNonHq.length === 1 && !nonCmdNonHq[0].is_hero) {
      // Phong anh hùng cho quân bảo vệ cuối cùng
      const heroId = nonCmdNonHq[0].piece_id;
      nextPieces = nextPieces.map((p) => (p.piece_id === heroId ? { ...p, is_hero: true } : p));
    } else if (nonCmdNonHq.length === 0 && hqPieces.length === 1 && !hqPieces[0].is_hero) {
      // Chỉ còn duy nhất 1 Sở chỉ huy và Tư lệnh -> Phong HQ thành Bộ binh Anh hùng
      const heroHqId = hqPieces[0].piece_id;
      nextPieces = nextPieces.map((p) => (p.piece_id === heroHqId ? { ...p, is_hero: true } : p));
    }
  }

  // =========================================================================
  // 3. PHONG ANH HÙNG KHI CHIẾU TƯ LỆNH ĐỐI PHƯƠNG (RULE-HERO-CHECK):
  // Khi một quân bất kỳ chiếu được Tư lệnh đối phương, nó sẽ được phong Anh hùng!
  // =========================================================================
  const actorSide = actor ? actor.side : 'RED';
  const enemySideOfActor = actorSide === 'RED' ? 'BLUE' : 'RED';
  const enemyCmd = nextPieces.find(
    (p) => p.is_alive && p.side === enemySideOfActor && p.type === 'COMMANDER' && !p.carried_by_id
  );

  let actorCheckedCommander = false;
  let actorWasPromoted = false;

  if (enemyCmd) {
    const checkingPieceIds = new Set<string>();
    for (const p of nextPieces) {
      if (p.is_alive && p.side === actorSide && !p.carried_by_id && p.type !== 'COMMANDER') {
        const candidateMoves = getMockLegalActions(p, nextPieces, false);
        const canHitCmd = candidateMoves.some(
          (m) =>
            (m.action_type === 'CAPTURE_REPLACE' || m.action_type === 'CAPTURE_STAND') &&
            (m.target_piece_id === enemyCmd.piece_id ||
              (m.to_pos.x === enemyCmd.position.x && m.to_pos.y === enemyCmd.position.y))
        );
        if (canHitCmd) {
          checkingPieceIds.add(p.piece_id);
          if (p.piece_id === action.piece_id) {
            actorCheckedCommander = true;
          }
        }
      }
    }

    if (checkingPieceIds.size > 0) {
      nextPieces = nextPieces.map((p) => {
        if (checkingPieceIds.has(p.piece_id)) {
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
    const fromNot = formatCoordinateNotation(actor.position);
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
  // CHIẾU HẾT TƯ LỆNH ĐỐI PHƯƠNG (CHECKMATE - DEC-019)
  // Khi Tư lệnh đối phương bị chiếu và toàn bộ các quân phe đó không còn nước đi hợp lệ
  // =========================================================================
  const isEnemyInCheck = isCommanderInCheck(nextPieces, enemySideOfActor);
  let isCheckmate = false;
  const deadTarget = (captured as PieceState | null) || deadPieceForRecord;

  if (isEnemyInCheck && !(deadTarget && deadTarget.type === 'COMMANDER')) {
    const enemyActivePieces = nextPieces.filter(
      (p) => p.is_alive && p.side === enemySideOfActor && !p.carried_by_id
    );
    let enemyHasLegalMove = false;
    for (const ep of enemyActivePieces) {
      const epMoves = getMockLegalActions(ep, nextPieces, true);
      if (epMoves.length > 0) {
        enemyHasLegalMove = true;
        break;
      }
    }
    if (!enemyHasLegalMove) {
      isCheckmate = true;
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
 * Lựa chọn nước đi thông minh và an toàn cho tác tử AI (DEC-019 & AI-KING-SAFETY):
 * 1. Khi Tư lệnh KHÔNG bị chiếu:
 *    - Ưu tiên 100% các quân tác chiến hoặc trú ẩn vào Sở chỉ huy.
 *    - Tuyệt đối không chọn nước đi của Tư lệnh lang thang ra ngoài bàn cờ cho đối phương ăn.
 *    - Nếu toàn bộ quân khác hết nước đi, Tư lệnh chỉ được đi vào ô hoàn toàn an toàn mà đối phương không thể ăn được!
 * 2. Khi Tư lệnh ĐANG BỊ CHIẾU:
 *    - Bắt buộc chọn nước đi hóa giải chiếu:
 *      a) Dùng quân khác chặn đường chiếu (nếu quân đối phương chiếu từ xa và đường chiếu có thể bị chặn).
 *      b) Dùng quân khác hoặc chính Tư lệnh ăn quân địch đang chiếu.
 *      c) Chạy Tư lệnh sang ô an toàn không bị đối phương ăn.
 *      d) Đưa Tư lệnh trú ẩn vào Sở chỉ huy.
 */
export function selectSmartAiAction(
  pieces: PieceState[],
  side: 'RED' | 'BLUE'
): LegalAction | null {
  const activePieces = pieces.filter((p) => p.side === side && p.is_alive && !p.carried_by_id);
  const allActions: LegalAction[] = [];
  for (const ap of activePieces) {
    allActions.push(...getMockLegalActions(ap, pieces, true));
  }
  if (allActions.length === 0) return null;

  const cmd = pieces.find((p) => p.is_alive && p.side === side && p.type === 'COMMANDER');
  const enemySide = side === 'RED' ? 'BLUE' : 'RED';

  // 1. Lọc an toàn tuyệt đối: Không để Tư lệnh bị chiếu sau nước đi,
  // và nếu Tư lệnh di chuyển thì ô đến tuyệt đối không bị đối phương ăn!
  const safeActions: LegalAction[] = [];
  for (const act of allActions) {
    const sim = simulateAction(act, pieces);
    if (isCommanderInCheck(sim, side)) continue;
    if (cmd && act.piece_id === cmd.piece_id && act.action_type !== 'BOARD') {
      if (isSquareAttackedByEnemy(sim, act.to_pos.x, act.to_pos.y, enemySide)) {
        continue;
      }
    }
    safeActions.push(act);
  }

  const pool = safeActions.length > 0 ? safeActions : allActions;
  const isInCheck = isCommanderInCheck(pieces, side);

  if (isInCheck) {
    // TÌNH HUỐNG 1: ĐANG BỊ CHIẾU
    // a) Dùng quân khác chặn đường chiếu hoặc ăn quân đang chiếu
    const blockingOrCapturing = pool.filter((a) => cmd && a.piece_id !== cmd.piece_id);
    // b) Tư lệnh trú ẩn vào Sở chỉ huy
    const shelterActions = pool.filter(
      (a) => cmd && a.piece_id === cmd.piece_id && a.action_type === 'BOARD'
    );
    // c) Tư lệnh chạy sang ô an toàn (không bị ăn)
    const cmdEscapeActions = pool.filter(
      (a) => cmd && a.piece_id === cmd.piece_id && a.action_type !== 'BOARD'
    );

    if (blockingOrCapturing.length > 0) {
      const preferred = [...blockingOrCapturing, ...shelterActions, ...cmdEscapeActions];
      return preferred[Math.floor(Math.random() * preferred.length)];
    } else if (shelterActions.length > 0) {
      return shelterActions[Math.floor(Math.random() * shelterActions.length)];
    } else if (cmdEscapeActions.length > 0) {
      return cmdEscapeActions[Math.floor(Math.random() * cmdEscapeActions.length)];
    } else {
      return pool[Math.floor(Math.random() * pool.length)];
    }
  } else {
    // TÌNH HUỐNG 2: KHÔNG BỊ CHIẾU
    // Ưu tiên các quân tác chiến hoặc trú ẩn, tuyệt đối không đi Tư lệnh lang thang cho đối phương ăn
    const tacticalActions = pool.filter((a) => cmd && a.piece_id !== cmd.piece_id);
    const shelterActions = pool.filter(
      (a) => cmd && a.piece_id === cmd.piece_id && a.action_type === 'BOARD'
    );

    if (tacticalActions.length > 0) {
      const preferred = [...tacticalActions, ...shelterActions];
      return preferred[Math.floor(Math.random() * preferred.length)];
    } else {
      return pool[Math.floor(Math.random() * pool.length)];
    }
  }
}
