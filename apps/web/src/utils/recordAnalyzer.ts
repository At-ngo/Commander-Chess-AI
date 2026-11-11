/**
 * Record Parser & Match Reconstructor for Game Analysis Record.
 * Supports:
 * 1. Research AI vs AI JSON logs (research/experiments/.../game_records/*.json)
 * 2. JSONL logs (one game record per line or one MoveRecord per line)
 * 3. Agent selected_action streams (MOVE:..., CAPTURE:..., CMD:END_TURN)
 * 4. COTULENH-NOTATION v1 (.ctn / .txt) and copied Action Log text
 */

import {
  ActiveCompoundState,
  ActionType,
  LegalAction,
  MoveRecord,
  PieceState,
  PieceType,
  Position,
  Side,
} from '../types';
import { getInitialPieces } from './initialBoard';
import { formatCoordinateNotation, isValidCoordinate } from './coordinates';
import { PIECE_NOTATION_SYMBOL } from './assets';
import {
  applyMockAction,
  canBoardCarrier,
  getAllCarriedPieceIds,
  getRootCarrier,
} from '../services/mockGameService';

export type RecordFormat =
  | 'AI_JSON_RECORD'
  | 'AI_JSONL'
  | 'SELECTED_ACTION_STREAM'
  | 'COTULENH_NOTATION'
  | 'ACTION_LOG_TEXT';

export type CompoundEventTag =
  | 'BOARD'
  | 'PICKUP'
  | 'CARRY_MOVE'
  | 'SOLO_SPLIT'
  | 'DEPLOY'
  | 'END_TURN';

export interface DecisionTelemetry {
  stepIndex?: number;
  turnNumber?: number;
  agentName?: string;
  agentConfigId?: string;
  selectedAction?: string;
  ruleTriggered?: string | null;
  heuristicScore?: number | null;
  heuristicComponents?: Record<string, number> | null;
  decisionTimeMs?: number | null;
  nodesVisited?: number | null;
  simulations?: number | null;
  legalActionCount?: number | null;
  stateHash?: string | null;
  events?: string[];
  rawActionType?: string;
  error?: string | null;
  overBudget?: boolean;
}

export interface AnalysisFrame {
  stepIndex: number;
  turnNumber: number;
  sideToMove: Side;
  pieces: PieceState[];
  scores: { RED: number; BLUE: number };
  capturedPieces: PieceState[];
  lastMove: MoveRecord | null;
  activeCompound: ActiveCompoundState | null;
  telemetry: DecisionTelemetry | null;
  compoundEventTag?: CompoundEventTag | null;
  carriedCount?: number;
  focusPieceId?: string | null;
}

export interface ParsedMatchMetadata {
  format: RecordFormat;
  gameId?: string;
  event?: string;
  date?: string;
  redAgent?: string;
  blueAgent?: string;
  redConfigId?: string;
  blueConfigId?: string;
  winner?: string | null;
  resultStatus?: string;
  terminationReason?: string;
  seed?: number | null;
  turnCount?: number | null;
  durationSec?: number | null;
  reportedFinalScores?: { RED?: number; BLUE?: number } | null;
}

export interface AnalysisResult {
  success: boolean;
  error?: string;
  warnings: string[];
  metadata: ParsedMatchMetadata;
  frames: AnalysisFrame[];
  normalizedNotationLines: string[];
}

interface ParsedStep {
  kind: 'ACTION' | 'END_TURN';
  side?: Side;
  tentativeSide?: Side;
  turnNumber?: number;
  actionType?: ActionType;
  rawActionType?: string;
  pieceId?: string | null;
  pieceType?: PieceType;
  fromPos?: Position | null;
  toPos?: Position | null;
  targetPieceId?: string | null;
  targetPieceType?: PieceType;
  carryCargo?: boolean;
  notationHint?: string;
  telemetry?: DecisionTelemetry | null;
}

const SYMBOL_TO_PIECE_TYPE: Record<string, PieceType> = {
  '⋆': 'COMMANDER',
  '★': 'COMMANDER',
  '*': 'COMMANDER',
  TL: 'COMMANDER',
  '\\STAR': 'COMMANDER',
  S: 'HEADQUARTERS',
  T: 'TANK',
  K: 'AIRCRAFT',
  B: 'INFANTRY',
  H: 'NAVY',
  F: 'ANTI_AIR',
  L: 'MISSILE',
  C: 'ENGINEER',
  D: 'MILITIA',
  A: 'ARTILLERY',
};

export const SAMPLE_NOTATION_RECORD = `[Format "COTULENH-NOTATION"]
[Version "1"]
[Event "Sample Tactical Opening"]
[Red "Human / RuleBased"]
[Blue "Human / Heuristic"]
[Result "*"]

1. Đỏ:  T [3 ; 5] _ [4 ; 5]
   Xanh: B [7 ; 2] _ [6 ; 2]
2. Đỏ:  D [4 ; 6] ^ T [4 ; 5]
   Xanh: T [8 ; 5] _ [7 ; 5]
3. Đỏ:  T [4 ; 5] _ [4 ; 4]
   Xanh: B [6 ; 2] _ [5 ; 2]
4. Đỏ:  B [4 ; 2] @ B [5 ; 2]
   Xanh: A [9 ; 3] _ [7 ; 3]
5. Đỏ:  D [4 ; 4] _ [5 ; 4] {action=DEPLOY}
        T [4 ; 4] _ [4 ; 5] {action=STACK_MOVE}
   Xanh: T [7 ; 5] _ [6 ; 5]`;

export const SAMPLE_AI_VS_AI_JSON_RECORD = JSON.stringify(
  {
    run_id: 'sample_ai_eval_01',
    game_id: 'game_0001',
    seed: 2026,
    budget_mode: 'default',
    agent_red: 'HeuristicAgent',
    agent_blue: 'RuleBasedAgent',
    red_config_id: 'balanced_v1',
    blue_config_id: 'ruleset_b',
    winner: null,
    result_status: 'in_progress_sample',
    termination_reason: 'SAMPLE_EXCERPT',
    turn_count: 4,
    total_decisions: 7,
    total_atomic_actions: 7,
    duration_sec: 0.142,
    final_scores: { red: 10, blue: 0 },
    moves: [
      {
        step_index: 1,
        turn_number: 1,
        player: 'red',
        action_type: 'move',
        piece_id: 'red_tank_1',
        start: [3, 5],
        end: [4, 5],
        target_piece_id: null,
        carry_cargo: true,
        decision_time_ms: 18.4,
        agent_name: 'HeuristicAgent',
        agent_config_id: 'balanced_v1',
        selected_action: 'MOVE:red_tank_1@(3,5)->(4,5)',
        rule_triggered: null,
        heuristic_score: 18.4,
        heuristic_components: { advancement: 6.2, mobility: 4.5, safety: 7.7 },
        nodes_visited: 142,
        simulations: 0,
      },
      {
        step_index: 2,
        turn_number: 1,
        player: 'blue',
        action_type: 'move',
        piece_id: 'blue_infantry_1',
        start: [7, 2],
        end: [6, 2],
        target_piece_id: null,
        carry_cargo: true,
        decision_time_ms: 6.1,
        agent_name: 'RuleBasedAgent',
        agent_config_id: 'ruleset_b',
        selected_action: 'MOVE:blue_infantry_1@(7,2)->(6,2)',
        rule_triggered: 'FALLBACK',
        heuristic_score: null,
        nodes_visited: null,
        simulations: null,
      },
      {
        step_index: 3,
        turn_number: 2,
        player: 'red',
        action_type: 'board',
        piece_id: 'red_militia_1',
        start: [4, 6],
        end: [4, 5],
        target_piece_id: 'red_tank_1',
        carry_cargo: true,
        decision_time_ms: 21.7,
        agent_name: 'HeuristicAgent',
        agent_config_id: 'balanced_v1',
        selected_action: 'BOARD:red_militia_1@(4,6)->(4,5)#carrier=red_tank_1',
        heuristic_score: 24.1,
        heuristic_components: { coordination: 8.5, safety: 15.6 },
        nodes_visited: 164,
        simulations: 0,
      },
      {
        step_index: 4,
        turn_number: 2,
        player: 'blue',
        action_type: 'move',
        piece_id: 'blue_tank_1',
        start: [8, 5],
        end: [7, 5],
        target_piece_id: null,
        carry_cargo: true,
        decision_time_ms: 5.8,
        agent_name: 'RuleBasedAgent',
        agent_config_id: 'ruleset_b',
        selected_action: 'MOVE:blue_tank_1@(8,5)->(7,5)',
        rule_triggered: 'FALLBACK',
      },
      {
        step_index: 5,
        turn_number: 3,
        player: 'red',
        action_type: 'move',
        piece_id: 'red_tank_1',
        start: [4, 5],
        end: [4, 4],
        target_piece_id: null,
        carry_cargo: true,
        decision_time_ms: 25.3,
        agent_name: 'HeuristicAgent',
        agent_config_id: 'balanced_v1',
        selected_action: 'MOVE:red_tank_1@(4,5)->(4,4)',
        heuristic_score: 31.2,
        heuristic_components: { threat: 12.0, advancement: 10.4, safety: 8.8 },
        nodes_visited: 198,
        simulations: 0,
      },
      {
        step_index: 6,
        turn_number: 3,
        player: 'blue',
        action_type: 'move',
        piece_id: 'blue_infantry_1',
        start: [6, 2],
        end: [5, 2],
        target_piece_id: null,
        carry_cargo: true,
        decision_time_ms: 7.4,
        agent_name: 'RuleBasedAgent',
        agent_config_id: 'ruleset_b',
        selected_action: 'MOVE:blue_infantry_1@(6,2)->(5,2)',
        rule_triggered: 'FALLBACK',
      },
      {
        step_index: 7,
        turn_number: 4,
        player: 'red',
        action_type: 'capture',
        piece_id: 'red_infantry_1',
        start: [4, 2],
        end: [5, 2],
        target_piece_id: 'blue_infantry_1',
        carry_cargo: true,
        decision_time_ms: 19.2,
        agent_name: 'HeuristicAgent',
        agent_config_id: 'balanced_v1',
        selected_action: 'CAPTURE:red_infantry_1@(4,2)->(5,2)#target=blue_infantry_1',
        rule_triggered: 'CAPTURE_HIGH_VALUE',
        heuristic_score: 54.8,
        heuristic_components: { material: 20.0, river_control: 14.8, safety: 20.0 },
        nodes_visited: 155,
        simulations: 0,
      },
    ],
  },
  null,
  2
);

function clonePieces(list: PieceState[]): PieceState[] {
  return list.map((p) => ({
    ...p,
    position: { ...p.position },
    carrying_piece_ids: [...(p.carrying_piece_ids || [])],
  }));
}

export function normalizePieceId(id?: string | null): string | null {
  if (!id || typeof id !== 'string') return null;
  const trimmed = id.trim();
  if (!trimmed) return null;
  return trimmed
    .toLowerCase()
    .replace(/-/g, '_')
    .replace(/_anti_aircraft_/g, '_anti_air_');
}

function mapPieceType(raw?: string | null): PieceType | undefined {
  if (!raw || typeof raw !== 'string') return undefined;
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  const upper = trimmed.toUpperCase().replace(/-/g, '_');
  if (SYMBOL_TO_PIECE_TYPE[upper]) return SYMBOL_TO_PIECE_TYPE[upper];
  if (SYMBOL_TO_PIECE_TYPE[trimmed]) return SYMBOL_TO_PIECE_TYPE[trimmed];
  if (upper === 'ANTI_AIRCRAFT' || upper === 'ANTI_AIR') return 'ANTI_AIR';
  if (
    upper === 'COMMANDER' ||
    upper === 'HEADQUARTERS' ||
    upper === 'INFANTRY' ||
    upper === 'MILITIA' ||
    upper === 'TANK' ||
    upper === 'ARTILLERY' ||
    upper === 'MISSILE' ||
    upper === 'AIRCRAFT' ||
    upper === 'NAVY' ||
    upper === 'ENGINEER'
  ) {
    return upper as PieceType;
  }
  return undefined;
}

function normalizeSide(val?: string | null): Side | undefined {
  if (!val || typeof val !== 'string') return undefined;
  const upper = val.trim().toUpperCase();
  if (upper === 'RED' || upper === 'ĐỎ' || upper === 'DO') return 'RED';
  if (upper === 'BLUE' || upper === 'XANH') return 'BLUE';
  return undefined;
}

function parseCoord(val: unknown): Position | null {
  if (Array.isArray(val) && val.length >= 2) {
    // Python engine records coordinates as [y, x]
    const y = Number(val[0]);
    const x = Number(val[1]);
    if (Number.isFinite(x) && Number.isFinite(y) && isValidCoordinate(x, y)) {
      return { x, y };
    }
    return null;
  }
  if (val && typeof val === 'object') {
    const obj = val as Record<string, unknown>;
    if (obj.x !== undefined && obj.y !== undefined) {
      const x = Number(obj.x);
      const y = Number(obj.y);
      if (Number.isFinite(x) && Number.isFinite(y) && isValidCoordinate(x, y)) {
        return { x, y };
      }
    }
  }
  return null;
}

function mapActionType(raw?: string | null): ActionType | 'END_TURN' {
  const upper = (raw || '').trim().toUpperCase();
  if (
    upper === 'END_TURN' ||
    upper === 'CONFIRM_DEPLOYMENT' ||
    upper === 'CMD:END_TURN' ||
    upper === 'CMD:CONFIRM_DEPLOYMENT'
  ) {
    return 'END_TURN';
  }
  if (upper === 'MOVE' || upper === 'STACK_MOVE' || upper === 'DEPLOY') return 'MOVE';
  if (upper === 'CAPTURE' || upper === 'CAPTURE_REPLACE') return 'CAPTURE_REPLACE';
  if (upper === 'BOMB' || upper === 'BOMBARD' || upper === 'CAPTURE_STAND') {
    return 'CAPTURE_STAND';
  }
  if (upper === 'BOARD' || upper === 'PICKUP') return 'BOARD';
  return 'MOVE';
}

function stripBoldMarkers(sym: string): string {
  let s = sym.trim();
  if (s.toLowerCase() === '\\star') return '⋆';
  if (s.startsWith('**') && s.endsWith('**') && s.length > 4) {
    s = s.slice(2, -2).trim();
  } else if (s.startsWith('*') && s.endsWith('*') && s.length > 2) {
    s = s.slice(1, -1).trim();
  }
  if (s.length > 1) {
    s = s.replace(/^[★☆]+|[★☆]+$/g, '').trim();
  }
  return s;
}

function parseSelectedActionString(
  raw: string,
  extraSide?: Side,
  telemetry?: DecisionTelemetry | null
): ParsedStep | null {
  const cleaned = raw.trim();
  if (!cleaned) return null;

  if (/^CMD\s*:/i.test(cleaned) || /^(?:END_TURN|CONFIRM_DEPLOYMENT)$/i.test(cleaned)) {
    return {
      kind: 'END_TURN',
      side: extraSide,
      actionType: 'END_TURN',
      rawActionType: cleaned,
      notationHint: 'CONFIRM_DEPLOYMENT',
      telemetry,
    };
  }

  const headMatch = cleaned.match(/^([A-Z_]+)\s*:\s*([^@;#\s]+)/i);
  if (!headMatch) return null;

  const rawAct = headMatch[1].toUpperCase();
  const pieceId = normalizePieceId(headMatch[2]);
  const startMatch = cleaned.match(/@\(\s*(\d+)\s*,\s*(\d+)\s*\)/);
  const endMatch = cleaned.match(/->\(\s*(\d+)\s*,\s*(\d+)\s*\)/);
  const targetMatch = cleaned.match(/#target=([^#;\s]+)/);
  const carrierMatch = cleaned.match(/#carrier=([^#;\s]+)/);
  const passengerMatch = cleaned.match(/#passenger=([^#;\s]+)/);
  const carryOffMatch = /(?:;|#|\s)carry=(?:0|false)\b/i.test(cleaned);
  const carryOnMatch = /(?:;|#|\s)carry=(?:1|true)\b/i.test(cleaned);

  const fromPos = startMatch
    ? { x: Number(startMatch[2]), y: Number(startMatch[1]) }
    : null;
  const toPos = endMatch
    ? { x: Number(endMatch[2]), y: Number(endMatch[1]) }
    : null;

  const resolvedTargetId = normalizePieceId(
    targetMatch?.[1] || carrierMatch?.[1] || passengerMatch?.[1] || null
  );

  let inferredSide = extraSide;
  if (!inferredSide && pieceId) {
    if (pieceId.startsWith('red_')) inferredSide = 'RED';
    else if (pieceId.startsWith('blue_')) inferredSide = 'BLUE';
  }

  const mappedAction = mapActionType(rawAct);
  if (mappedAction === 'END_TURN') {
    return {
      kind: 'END_TURN',
      side: inferredSide,
      actionType: 'END_TURN',
      rawActionType: rawAct.toLowerCase(),
      notationHint: 'CONFIRM_DEPLOYMENT',
      telemetry,
    };
  }

  return {
    kind: 'ACTION',
    side: inferredSide,
    actionType: mappedAction as ActionType,
    rawActionType: rawAct.toLowerCase(),
    pieceId,
    fromPos,
    toPos,
    targetPieceId: resolvedTargetId,
    carryCargo: carryOffMatch ? false : carryOnMatch ? true : undefined,
    telemetry,
  };
}

function parseJsonMoveItem(item: Record<string, unknown>): ParsedStep | null {
  const itemTurnNum =
    typeof item.turn_number === 'number'
      ? item.turn_number
      : typeof item.turn_id === 'number'
      ? item.turn_id
      : undefined;

  // Handle frontend GameEvent/MoveRecord style if present
  if (item.action && typeof item.action === 'object') {
    const act = item.action as Record<string, unknown>;
    const side = normalizeSide((item.side as string) || (act.side as string));
    const actType = mapActionType(act.action_type as string);
    if (actType === 'END_TURN') {
      return {
        kind: 'END_TURN',
        side,
        turnNumber: itemTurnNum,
        actionType: 'END_TURN',
        notationHint: (item.notation as string) || (act.notation as string) || 'CONFIRM_DEPLOYMENT',
      };
    }
    return {
      kind: 'ACTION',
      side,
      turnNumber: itemTurnNum,
      actionType: actType,
      rawActionType: String(act.action_type || ''),
      pieceId: normalizePieceId(act.piece_id as string),
      pieceType: mapPieceType((act.piece_type as string) || undefined),
      fromPos: parseCoord(act.from_pos),
      toPos: parseCoord(act.to_pos),
      targetPieceId: normalizePieceId(act.target_piece_id as string),
      targetPieceType: mapPieceType((act.target_piece_type as string) || undefined),
      carryCargo:
        act.carry_cargo === undefined || act.carry_cargo === null
          ? undefined
          : Boolean(act.carry_cargo),
      notationHint: (item.notation as string) || (act.notation as string),
    };
  }

  // Handle Research AI vs AI game_records MoveRecord & MOVE_NOTATION §7 Event Log JSON
  const rawType = String(item.action_type || '').trim();
  const mappedType = mapActionType(rawType);
  const side = normalizeSide((item.player as string) || (item.side as string));
  const actorObj =
    item.actor && typeof item.actor === 'object'
      ? (item.actor as Record<string, unknown>)
      : null;
  const selectedActionStr =
    typeof item.selected_action === 'string' ? item.selected_action : undefined;

  const telemetry: DecisionTelemetry = {
    stepIndex: typeof item.step_index === 'number' ? item.step_index : undefined,
    turnNumber: itemTurnNum,
    agentName: typeof item.agent_name === 'string' ? item.agent_name : undefined,
    agentConfigId: typeof item.agent_config_id === 'string' ? item.agent_config_id : undefined,
    selectedAction: selectedActionStr,
    ruleTriggered:
      typeof item.rule_triggered === 'string' ? item.rule_triggered : null,
    heuristicScore:
      typeof item.heuristic_score === 'number' ? item.heuristic_score : null,
    heuristicComponents:
      item.heuristic_components && typeof item.heuristic_components === 'object'
        ? (item.heuristic_components as Record<string, number>)
        : null,
    decisionTimeMs:
      typeof item.decision_time_ms === 'number' ? item.decision_time_ms : null,
    nodesVisited:
      typeof item.nodes_visited === 'number' ? item.nodes_visited : null,
    simulations:
      typeof item.simulations === 'number' ? item.simulations : null,
    legalActionCount:
      typeof item.legal_action_count === 'number' ? item.legal_action_count : null,
    stateHash: typeof item.state_hash === 'string' ? item.state_hash : null,
    events: Array.isArray(item.events) ? item.events.map(String) : undefined,
    rawActionType: rawType || mappedType,
    error: typeof item.error === 'string' ? item.error : null,
    overBudget: Boolean(item.over_budget),
  };

  if (mappedType === 'END_TURN') {
    return {
      kind: 'END_TURN',
      side,
      turnNumber: telemetry.turnNumber,
      actionType: 'END_TURN',
      rawActionType: rawType,
      notationHint:
        typeof item.notation === 'string' ? item.notation : 'CONFIRM_DEPLOYMENT',
      telemetry,
    };
  }

  let parsedFromSelected: ParsedStep | null = null;
  if (selectedActionStr) {
    parsedFromSelected = parseSelectedActionString(selectedActionStr, side, telemetry);
  }

  const targetsArr = Array.isArray(item.targets) ? item.targets : null;
  const firstTarget =
    targetsArr && targetsArr[0] && typeof targetsArr[0] === 'object'
      ? (targetsArr[0] as Record<string, unknown>)
      : null;

  const pieceId = normalizePieceId(
    (item.piece_id as string) ||
      (actorObj?.piece_id as string) ||
      parsedFromSelected?.pieceId ||
      null
  );

  const pieceType =
    mapPieceType(
      (item.piece_type as string) ||
        (actorObj?.piece_type as string) ||
        (actorObj?.notation_symbol as string) ||
        null
    ) || parsedFromSelected?.pieceType;

  const targetPieceId = normalizePieceId(
    (item.target_piece_id as string) ||
      (item.carrier_id as string) ||
      (item.passenger_id as string) ||
      (firstTarget?.piece_id as string) ||
      parsedFromSelected?.targetPieceId ||
      null
  );

  const targetPieceType =
    mapPieceType(
      (item.target_piece_type as string) ||
        (firstTarget?.piece_type as string) ||
        (firstTarget?.notation_symbol as string) ||
        null
    ) || parsedFromSelected?.targetPieceType;

  const fromPos =
    parseCoord(item.start ?? item.from ?? item.from_pos) ?? parsedFromSelected?.fromPos ?? null;
  const toPos =
    parseCoord(item.end ?? item.to ?? item.to_pos) ?? parsedFromSelected?.toPos ?? null;

  const rawNotationStr = typeof item.notation === 'string' ? item.notation : undefined;
  let carryCargo: boolean | undefined = undefined;
  if (item.carry_cargo !== undefined && item.carry_cargo !== null) {
    carryCargo = Boolean(item.carry_cargo);
  } else if (parsedFromSelected?.carryCargo !== undefined) {
    carryCargo = parsedFromSelected.carryCargo;
  } else if (rawType.toUpperCase() === 'STACK_MOVE') {
    carryCargo = true;
  } else if (rawNotationStr && /\{[^}]*carry(?:_cargo)?\s*=\s*(?:false|0)/i.test(rawNotationStr)) {
    carryCargo = false;
  } else if (rawNotationStr && /\{[^}]*carry(?:_cargo)?\s*=\s*(?:true|1)/i.test(rawNotationStr)) {
    carryCargo = true;
  }

  if (!pieceId && !pieceType && !fromPos) {
    return parsedFromSelected;
  }

  return {
    kind: 'ACTION',
    side: side || parsedFromSelected?.side,
    turnNumber: telemetry.turnNumber,
    actionType: mappedType,
    rawActionType: rawType.toLowerCase(),
    pieceId,
    pieceType,
    fromPos,
    toPos,
    targetPieceId,
    targetPieceType,
    carryCargo,
    notationHint: rawNotationStr,
    telemetry,
  };
}

function splitOutsideBrackets(text: string): string[] {
  const parts: string[] = [];
  let buf = '';
  let sqDepth = 0;
  let parenDepth = 0;
  let braceDepth = 0;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '[') sqDepth += 1;
    else if (ch === ']') sqDepth = Math.max(0, sqDepth - 1);
    else if (ch === '(') parenDepth += 1;
    else if (ch === ')') parenDepth = Math.max(0, parenDepth - 1);
    else if (ch === '{') braceDepth += 1;
    else if (ch === '}') braceDepth = Math.max(0, braceDepth - 1);

    if (sqDepth === 0 && parenDepth === 0 && braceDepth === 0) {
      if (ch === ';') {
        if (buf.trim()) parts.push(buf.trim());
        buf = '';
        continue;
      }
      if (
        ch === '/' &&
        i > 0 &&
        i + 1 < text.length &&
        /\s/.test(text[i - 1]) &&
        /\s/.test(text[i + 1])
      ) {
        if (buf.trim()) parts.push(buf.trim());
        buf = '';
        continue;
      }
    }
    buf += ch;
  }
  if (buf.trim()) parts.push(buf.trim());
  return parts;
}

function parseNotationLineSegment(
  segment: string,
  inheritedSide: Side | undefined,
  turnNumber: number | undefined
): ParsedStep | null {
  let text = segment.trim().replace(/^[;|+]+\s*/, '').trim();
  if (!text) return null;

  // Extract optional {...} project metadata anywhere in segment (e.g. {carry=0}, {action=DEPLOY})
  let carryCargoHint: boolean | undefined;
  let metaActionHint: string | undefined;
  text = text
    .replace(/\{([^}]+)\}/g, (_full, metaBody: string) => {
      if (/\bcarry(?:_cargo)?\s*=\s*(?:false|0)\b/i.test(metaBody)) {
        carryCargoHint = false;
      } else if (/\bcarry(?:_cargo)?\s*=\s*(?:true|1)\b/i.test(metaBody)) {
        carryCargoHint = true;
      }
      const actM = metaBody.match(/\baction\s*=\s*([A-Z_]+)/i);
      if (actM) metaActionHint = actM[1].toUpperCase();
      return ' ';
    })
    .replace(/\s+/g, ' ')
    .trim();

  if (
    /^(?:CONFIRM_DEPLOYMENT|END_TURN|CMD\s*:\s*(?:END_TURN|CONFIRM_DEPLOYMENT)|HOÀN\s*TẤT(?:\s+LƯỢT)?(?:\s+TỔ\s+HỢP)?|KẾT\s*THÚC(?:\s+LƯỢT)?(?:\s+TỔ\s+HỢP)?)(?:\s*[#?!+]+)?$/i.test(
      text
    ) ||
    metaActionHint === 'END_TURN' ||
    metaActionHint === 'CONFIRM_DEPLOYMENT'
  ) {
    return {
      kind: 'END_TURN',
      side: inheritedSide,
      turnNumber,
      actionType: 'END_TURN',
      notationHint: text || 'CONFIRM_DEPLOYMENT',
    };
  }

  // Also check if user pasted a selected_action token inside mixed log
  const selectedTry = parseSelectedActionString(text, inheritedSide, null);
  if (selectedTry) {
    return { ...selectedTry, turnNumber };
  }

  const normalizedTexText = text.replace(/\\star/gi, '⋆');
  const PIECE_PAT = String.raw`(?:\*\*[^*\s]+\*\*|\*[^*\s]+\*|TL|[⋆★][A-Za-z]?|[A-Za-z]★?|[*])`;
  const COORD_PAT = String.raw`(?:\[\s*(\d+)\s*[;,]\s*(\d+)\s*\]|\(\s*(\d+)\s*[;,]\s*(\d+)\s*\))`;
  const OP_PAT = String.raw`(_@_|\^|><|@["”']|@|->|_|-|\+)`;
  const moveRegex = new RegExp(
    `^(${PIECE_PAT})\\s*${COORD_PAT}\\s*${OP_PAT}\\s*(?:(${PIECE_PAT})\\s*)?${COORD_PAT}`
  );
  const match = normalizedTexText.match(moveRegex);
  if (!match) return null;

  const rawActorSym = stripBoldMarkers(match[1]);
  const fromY = Number(match[2] ?? match[4]);
  const fromX = Number(match[3] ?? match[5]);
  const op = match[6];
  const rawTargetSym = match[7] ? stripBoldMarkers(match[7]) : undefined;
  const toY = Number(match[8] ?? match[10]);
  const toX = Number(match[9] ?? match[11]);

  if (!isValidCoordinate(fromX, fromY) || !isValidCoordinate(toX, toY)) {
    return null;
  }

  const pieceType =
    SYMBOL_TO_PIECE_TYPE[rawActorSym.toUpperCase()] || SYMBOL_TO_PIECE_TYPE[rawActorSym];
  const targetPieceType = rawTargetSym
    ? SYMBOL_TO_PIECE_TYPE[rawTargetSym.toUpperCase()] || SYMBOL_TO_PIECE_TYPE[rawTargetSym]
    : undefined;

  let actionType: ActionType = 'MOVE';
  if (metaActionHint === 'BOARD' || metaActionHint === 'PICKUP') {
    actionType = 'BOARD';
  } else if (
    metaActionHint === 'CAPTURE_STAND' ||
    metaActionHint === 'BOMB' ||
    metaActionHint === 'BOMBARD'
  ) {
    actionType = 'CAPTURE_STAND';
  } else if (metaActionHint === 'CAPTURE' || metaActionHint === 'CAPTURE_REPLACE') {
    actionType = 'CAPTURE_REPLACE';
  } else if (op === '_@_') {
    actionType = 'CAPTURE_STAND';
  } else if (op === '^' || op === '+') {
    actionType = 'BOARD';
  } else if (op === '@' || op === '><') {
    actionType = 'CAPTURE_REPLACE';
  } else if (op === '@"' || op === '@”' || op === "@'") {
    actionType = targetPieceType ? 'CAPTURE_REPLACE' : 'MOVE';
  } else if (op === '_' || op === '-' || op === '->') {
    actionType = 'MOVE';
  }

  if (metaActionHint === 'STACK_MOVE' && carryCargoHint === undefined) {
    carryCargoHint = true;
  }

  return {
    kind: 'ACTION',
    side: inheritedSide,
    turnNumber,
    actionType,
    rawActionType: actionType.toLowerCase(),
    pieceType,
    fromPos: { x: fromX, y: fromY },
    toPos: { x: toX, y: toY },
    targetPieceType,
    carryCargo: carryCargoHint,
    notationHint: normalizedTexText,
  };
}

function splitNotationText(raw: string): {
  metadata: Partial<ParsedMatchMetadata>;
  steps: ParsedStep[];
  warnings: string[];
  format: RecordFormat;
} {
  const metadata: Partial<ParsedMatchMetadata> = {};
  const steps: ParsedStep[] = [];
  const warnings: string[] = [];
  let hasCtnHeader = false;
  let currentTurn = 1;
  let lastExplicitSide: Side | undefined;
  let pendingSideHeader: Side | undefined;

  const lines = raw.split(/\r?\n/);
  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const rawLine = lines[lineIdx];
    const hasLeadingIndent = /^\s+\S/.test(rawLine);
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || line.startsWith('//') || /^[-=]{3,}$/.test(line)) {
      continue;
    }

    // Header tags: [Key "Value"]
    const tagMatch = line.match(/^\[\s*([A-Za-z0-9_]+)\s+"([^"]*)"\s*\]$/);
    if (tagMatch) {
      hasCtnHeader = true;
      const key = tagMatch[1].toLowerCase();
      const val = tagMatch[2];
      if (key === 'event') metadata.event = val;
      else if (key === 'date') metadata.date = val;
      else if (key === 'red') metadata.redAgent = val;
      else if (key === 'blue') metadata.blueAgent = val;
      else if (key === 'result') metadata.winner = val;
      else if (key === 'termination') metadata.terminationReason = val;
      else if (key === 'finalscore') {
        const scMatch = val.match(/red\s*:\s*(\d+)\s*[-–/]\s*blue\s*:\s*(\d+)/i);
        if (scMatch) {
          metadata.reportedFinalScores = {
            RED: Number(scMatch[1]),
            BLUE: Number(scMatch[2]),
          };
        }
      }
      continue;
    }

    if (line === '—' || line === '...') {
      pendingSideHeader = undefined;
      continue;
    }

    // Extract optional turn prefix e.g. "12."
    let working = line;
    const turnMatch = working.match(/^(\d+)[.)]\s*(.*)$/);
    if (turnMatch) {
      currentTurn = Number(turnMatch[1]);
      working = turnMatch[2].trim();
      pendingSideHeader = undefined;
    }
    if (!working || working === '—' || working === '...') {
      pendingSideHeader = undefined;
      continue;
    }

    // Check standalone side header line (e.g. from browser DOM copy of MoveHistory: "Đỏ", "Xanh:", "XANH—")
    const standaloneSideMatch = working.match(
      /^(?:Bên\s+)?(Đỏ|Xanh|Red|Blue|Do)\s*:?\s*(—|\.\.\.)?$/i
    );
    if (
      standaloneSideMatch &&
      (standaloneSideMatch[1].toLowerCase() !== 'do' || /Bên\s+|:$/i.test(working))
    ) {
      if (standaloneSideMatch[2]) {
        pendingSideHeader = undefined;
        continue;
      }
      const s = normalizeSide(standaloneSideMatch[1]);
      if (s) {
        pendingSideHeader = s;
        lastExplicitSide = s;
        continue;
      }
    }

    // Split same-line multiple side clauses e.g. "Đỏ: ...   Xanh: ...", tab-separated "Đỏ\t...", or fused DOM copy ("ĐỎD ...", "]Xanh:", "}Xanh:", "★TXanh:", "—Xanh:")
    const candidateSideRegex =
      /((?:Bên\s+(?:Đỏ|Do|Xanh|Red|Blue)|Đỏ|Xanh|Red|Blue|Do(?=\s*:))(?:\s*:|\s+(?=(?:\*\*|\\star|TL|[⋆★*A-Za-z]|CONFIRM_DEPLOYMENT|END_TURN|CMD:|Hoàn|Kết|—|\.\.\.))|(?=(?:\*\*|\*[^*\s]+\*|[⋆★*]|\\star|(?:TL|[STKBHFLCDA])\s*[\[(]\s*\d|CONFIRM_DEPLOYMENT|END_TURN|CMD:|—|\.\.\.))))/gi;
    const isInsideBraces = (pos: number): boolean => {
      let depth = 0;
      for (let k = 0; k < pos; k++) {
        if (working[k] === '{') depth += 1;
        else if (working[k] === '}') depth = Math.max(0, depth - 1);
      }
      return depth > 0;
    };
    const matches: { index: number; end: number; side: Side }[] = [];
    let m: RegExpExecArray | null;
    while ((m = candidateSideRegex.exec(working)) !== null) {
      const innerToken = m[1];
      const matchStart = m.index;
      if (isInsideBraces(matchStart)) continue;
      if (matchStart > 0) {
        const prevChar = working[matchStart - 1];
        const hasColon = /:\s*$/.test(innerToken);
        const validBoundary =
          /[\s\])}*★⋆>#?!—.0-9]/.test(prevChar) ||
          (hasColon && !/^Do\s*:/i.test(innerToken) && /^[A-Z]$/.test(prevChar));
        if (!validBoundary) continue;
      }
      const rawSideWord = innerToken
        .replace(/^Bên\s+/i, '')
        .replace(/:\s*$/, '')
        .trim();
      const s = normalizeSide(rawSideWord);
      if (s) {
        matches.push({ index: matchStart, end: m.index + m[0].length, side: s });
      }
    }

    if (matches.length > 0) {
      pendingSideHeader = undefined;
      for (let i = 0; i < matches.length; i++) {
        const cur = matches[i];
        const nextStart = i + 1 < matches.length ? matches[i + 1].index : working.length;
        const body = working.slice(cur.end, nextStart).trim();
        lastExplicitSide = cur.side;
        if (!body || body === '...' || body === '—') continue;
        const subSegments = splitOutsideBrackets(body);
        for (const sub of subSegments) {
          const parsed = parseNotationLineSegment(sub, cur.side, currentTurn);
          if (parsed) {
            steps.push(parsed);
          } else {
            warnings.push(`Dòng ${lineIdx + 1}: không hiểu cú pháp "${sub}"`);
          }
        }
      }
    } else {
      const subSegments = splitOutsideBrackets(working);
      for (let subIdx = 0; subIdx < subSegments.length; subIdx++) {
        const sub = subSegments[subIdx];
        const headerSide = subIdx === 0 ? pendingSideHeader : undefined;
        if (subIdx === 0) pendingSideHeader = undefined;
        const parsed = parseNotationLineSegment(sub, headerSide, currentTurn);
        if (parsed) {
          if (!parsed.side && lastExplicitSide) {
            if (
              parsed.kind === 'END_TURN' ||
              sub.startsWith(';') ||
              sub.startsWith('+') ||
              (!turnMatch &&
                /stack=|index=|carry=|DEPLOY|STACK_MOVE|BOARD|PICKUP|END_TURN|CONFIRM_DEPLOYMENT/i.test(
                  sub
                ))
            ) {
              parsed.side = lastExplicitSide;
            } else if (!turnMatch && hasLeadingIndent) {
              parsed.tentativeSide = lastExplicitSide;
            }
          }
          steps.push(parsed);
        } else {
          warnings.push(`Dòng ${lineIdx + 1}: bỏ qua dòng không khớp ký pháp ("${sub}")`);
        }
      }
    }
  }

  return {
    metadata,
    steps,
    warnings,
    format: hasCtnHeader ? 'COTULENH_NOTATION' : 'ACTION_LOG_TEXT',
  };
}

function buildNotationForStep(
  actor: PieceState,
  actionType: ActionType | 'END_TURN',
  fromPos: Position,
  toPos: Position,
  target: PieceState | null
): string {
  if (actionType === 'END_TURN') return 'CONFIRM_DEPLOYMENT';
  const actorSym = PIECE_NOTATION_SYMBOL[actor.type] || 'B';
  const fromNot = formatCoordinateNotation(fromPos);
  const toNot = formatCoordinateNotation(toPos);
  if (actionType === 'MOVE') {
    return `${actorSym} ${fromNot} _ ${toNot}`;
  }
  const targetSym = target ? PIECE_NOTATION_SYMBOL[target.type] || 'B' : '?';
  if (actionType === 'CAPTURE_STAND') {
    return `${actorSym} ${fromNot} _@_ ${targetSym} ${toNot}`;
  }
  if (actionType === 'BOARD') {
    return `${actorSym} ${fromNot} ^ ${targetSym} ${toNot}`;
  }
  return `${actorSym} ${fromNot} @ ${targetSym} ${toNot}`;
}

function samePos(a?: Position | null, b?: Position | null): boolean {
  return Boolean(a && b && a.x === b.x && a.y === b.y);
}

function resolveActorMatches(
  step: ParsedStep,
  pieces: PieceState[],
  candidateSide: Side
): PieceState[] {
  if (step.pieceId) {
    const exact = pieces.find(
      (p) => p.is_alive && p.side === candidateSide && p.piece_id === step.pieceId
    );
    if (exact) return [exact];
  }

  return pieces.filter((p) => {
    if (!p.is_alive) return false;
    if (p.side !== candidateSide) return false;
    if (step.pieceType && p.type !== step.pieceType) return false;
    if (step.fromPos) {
      const origin = p.carried_by_id ? getRootCarrier(p, pieces).position : p.position;
      if (origin.x !== step.fromPos.x || origin.y !== step.fromPos.y) return false;
    }
    return true;
  });
}

function resolveActorPiece(
  step: ParsedStep,
  pieces: PieceState[],
  sideToMove: Side,
  currentCompound: ActiveCompoundState | null = null
): PieceState | null {
  if (step.pieceId) {
    const exact = pieces.find((p) => p.is_alive && p.piece_id === step.pieceId);
    if (exact) return exact;
  }

  const candidateSide = step.side || sideToMove;
  const matches = resolveActorMatches(step, pieces, candidateSide);
  if (matches.length === 0) return null;
  if (matches.length === 1) return matches[0];

  if (currentCompound) {
    const unmoved = matches.filter(
      (p) =>
        currentCompound.memberIds.includes(p.piece_id) &&
        !currentCompound.movedPieceIds.includes(p.piece_id)
    );
    if (unmoved.length === 1) return unmoved[0];
    if (unmoved.length > 1) {
      return unmoved.find((p) => !p.carried_by_id) || unmoved[0];
    }
  }

  // Prefer non-carried root piece first unless only carried piece matched by type
  return matches.find((p) => !p.carried_by_id) || matches[0];
}

function resolveStepActingSide(
  step: ParsedStep,
  pieces: PieceState[],
  sideToMove: Side,
  currentCompound: ActiveCompoundState | null
): Side {
  if (step.side) return step.side;
  if (step.kind === 'END_TURN') return sideToMove;

  const altSide: Side = sideToMove === 'RED' ? 'BLUE' : 'RED';
  const curMatches = resolveActorMatches(step, pieces, sideToMove);
  const altMatches = resolveActorMatches(step, pieces, altSide);

  if (curMatches.length > 0 && altMatches.length === 0) return sideToMove;
  if (altMatches.length > 0 && curMatches.length === 0) return altSide;

  if (currentCompound && step.fromPos && samePos(step.fromPos, currentCompound.originPos)) {
    const hasCompoundMatch = curMatches.some(
      (m) =>
        currentCompound.memberIds.includes(m.piece_id) &&
        !currentCompound.movedPieceIds.includes(m.piece_id)
    );
    if (hasCompoundMatch) return sideToMove;
  }

  return step.tentativeSide || sideToMove;
}

function resolveTargetPiece(
  step: ParsedStep,
  actor: PieceState,
  pieces: PieceState[]
): PieceState | null {
  if (step.targetPieceId) {
    const exact = pieces.find((p) => p.is_alive && p.piece_id === step.targetPieceId);
    if (exact) return exact;
  }
  if (!step.toPos) return null;

  const expectedSide: Side =
    step.actionType === 'BOARD' ? actor.side : actor.side === 'RED' ? 'BLUE' : 'RED';

  const sameSquareRoots = pieces.filter((p) => {
    if (!p.is_alive || p.piece_id === actor.piece_id) return false;
    if (p.carried_by_id) return false;
    return p.position.x === step.toPos!.x && p.position.y === step.toPos!.y;
  });

  if (step.targetPieceType) {
    const rootPreferred = sameSquareRoots.find(
      (p) => p.type === step.targetPieceType && p.side === expectedSide
    );
    if (rootPreferred) return rootPreferred;

    const rootAnySide = sameSquareRoots.find((p) => p.type === step.targetPieceType);
    if (rootAnySide) return rootAnySide;

    const carriedFallback = pieces.find((p) => {
      if (!p.is_alive || p.piece_id === actor.piece_id) return false;
      const pos = p.carried_by_id ? getRootCarrier(p, pieces).position : p.position;
      return (
        p.type === step.targetPieceType &&
        pos.x === step.toPos!.x &&
        pos.y === step.toPos!.y
      );
    });
    if (carriedFallback) return carriedFallback;
  }

  return (
    sameSquareRoots.find((p) => p.side === expectedSide) || sameSquareRoots[0] || null
  );
}

function inferCarryCargoForStep(
  step: ParsedStep,
  stepIndex: number,
  steps: ParsedStep[],
  actor: PieceState,
  actingSide: Side,
  fromPos: Position,
  toPos: Position,
  finalActionType: ActionType,
  pieces: PieceState[]
): boolean {
  if (step.carryCargo !== undefined) {
    return step.carryCargo;
  }
  if (finalActionType === 'CAPTURE_STAND') {
    return false;
  }
  if (finalActionType === 'BOARD') {
    return true;
  }
  if (actor.type === 'HEADQUARTERS') {
    return false;
  }

  const descendantIds = getAllCarriedPieceIds(actor.piece_id, pieces);
  if (descendantIds.length === 0) {
    return true;
  }
  if (fromPos.x === toPos.x && fromPos.y === toPos.y) {
    return true;
  }

  // Only a root (uncarried) carrier followed immediately by END_TURN (CONFIRM_DEPLOYMENT) proves solo split
  const immediateNext = stepIndex + 1 < steps.length ? steps[stepIndex + 1] : null;
  if (
    actor.carried_by_id == null &&
    immediateNext &&
    immediateNext.kind === 'END_TURN' &&
    (!immediateNext.side || immediateNext.side === actingSide)
  ) {
    return false;
  }

  const childTypes = new Set<PieceType>();
  for (const id of descendantIds) {
    const child = pieces.find((p) => p.is_alive && p.piece_id === id);
    if (child) childTypes.add(child.type);
  }

  let originBlocked = false;
  let actorTrackedPos: Position | null = { ...toPos };

  for (let j = stepIndex + 1; j < steps.length; j++) {
    const s = steps[j];
    if (s.kind === 'END_TURN') continue;

    if (s.pieceId && descendantIds.includes(s.pieceId)) {
      if (!originBlocked && samePos(s.fromPos, fromPos)) return false;
      if (actorTrackedPos && samePos(s.fromPos, actorTrackedPos)) return true;
      break;
    }
    if (s.targetPieceId && descendantIds.includes(s.targetPieceId)) {
      if (!originBlocked && samePos(s.toPos, fromPos)) return false;
      if (actorTrackedPos && samePos(s.toPos, actorTrackedPos)) return true;
    }

    const sFriendly = !s.side || s.side === actingSide;
    const sEnemy = !s.side || s.side !== actingSide;

    // A carried descendant acts from fromPos (split) or actorTrackedPos (carried)
    if (sFriendly && s.pieceType && childTypes.has(s.pieceType)) {
      if (!originBlocked && samePos(s.fromPos, fromPos)) return false;
      if (actorTrackedPos && samePos(s.fromPos, actorTrackedPos)) return true;
    }

    // Another friendly unit boards the left-behind cargo at fromPos
    if (
      sFriendly &&
      s.actionType === 'BOARD' &&
      !originBlocked &&
      samePos(s.toPos, fromPos) &&
      (!s.targetPieceType || childTypes.has(s.targetPieceType))
    ) {
      return false;
    }

    // Enemy captures left-behind cargo at fromPos
    if (
      sEnemy &&
      !originBlocked &&
      samePos(s.toPos, fromPos) &&
      s.targetPieceType &&
      childTypes.has(s.targetPieceType)
    ) {
      return false;
    }

    // Follow actor across subsequent turns in case cargo deploys on a later turn
    if (
      actorTrackedPos &&
      sFriendly &&
      (!s.pieceId || s.pieceId === actor.piece_id) &&
      (!s.pieceType || s.pieceType === actor.type) &&
      samePos(s.fromPos, actorTrackedPos) &&
      s.actionType !== 'CAPTURE_STAND' &&
      s.toPos
    ) {
      actorTrackedPos = { ...s.toPos };
    }

    if (!originBlocked && s.toPos && samePos(s.toPos, fromPos) && s.actionType !== 'CAPTURE_STAND') {
      originBlocked = true;
    }
  }

  return true;
}

/**
 * Serialize active match MoveRecord[] cleanly without losing carry_cargo=false splits
 * or compound turn grouping when importing into Game Analysis Record.
 */
export function formatMoveRecordsForRecordInput(moves: MoveRecord[]): string {
  if (!moves || moves.length === 0) return '';
  const lines: string[] = [];
  let roundNum = 1;
  let lastSide: Side | null = null;

  for (const mv of moves) {
    if (lastSide === 'BLUE' && mv.side === 'RED') {
      roundNum += 1;
    }
    const baseNote = (
      mv.notation ||
      (mv.action?.action_type === 'END_TURN' ? 'CONFIRM_DEPLOYMENT' : '')
    ).trim();
    const needsCarryZero =
      (mv.action?.action_type === 'MOVE' || mv.action?.action_type === 'CAPTURE_REPLACE') &&
      mv.action?.carry_cargo === false &&
      !/\{[^}]*carry(?:_cargo)?\s*=/i.test(baseNote);
    const fullNote = needsCarryZero ? `${baseNote} {carry=0}` : baseNote;
    const sideLabel = mv.side === 'RED' ? 'Đỏ' : 'Xanh';

    const isSameSideContinuation = lastSide === mv.side;
    if (isSameSideContinuation) {
      lines.push(`   ${sideLabel}: ${fullNote}`);
    } else if (mv.side === 'RED' || lastSide === null) {
      lines.push(`${roundNum}. ${sideLabel}:  ${fullNote}`);
    } else {
      lines.push(`   ${sideLabel}: ${fullNote}`);
    }

    lastSide = mv.side;
  }
  return lines.join('\n');
}

export function formatFullMatchNotation(
  moves: MoveRecord[],
  meta: {
    winner: Side | 'DRAW';
    reason: string;
    finalScores: { RED: number; BLUE: number };
    durationFormatted: string;
    date?: string;
  }
): string {
  const today = meta.date || new Date().toISOString().split('T')[0];
  const resStr =
    meta.winner === 'RED' ? 'RED_WIN' : meta.winner === 'BLUE' ? 'BLUE_WIN' : 'DRAW';
  const moveBody = formatMoveRecordsForRecordInput(moves);

  return [
    `[Format "COTULENH-NOTATION"]`,
    `[Version "1.1"]`,
    `[Date "${today}"]`,
    `[Mode "TOTAL_FORCE"]`,
    `[Red "Commander Red"]`,
    `[Blue "Commander Blue"]`,
    `[Result "${resStr}"]`,
    `[Termination "${meta.reason}"]`,
    `[FinalScore "Red: ${meta.finalScores.RED} - Blue: ${meta.finalScores.BLUE}"]`,
    `[Duration "${meta.durationFormatted}"]`,
    ``,
    ...(moveBody ? [moveBody] : []),
  ].join('\n');
}

export function parseAndReplayRecord(rawInput: string): AnalysisResult {
  const emptyMeta: ParsedMatchMetadata = { format: 'ACTION_LOG_TEXT' };
  let cleaned = (rawInput || '').trim();
  if (!cleaned) {
    return {
      success: false,
      error: 'Vui lòng dán nội dung biên bản hoặc JSON log trước khi phân tích.',
      warnings: [],
      metadata: emptyMeta,
      frames: [],
      normalizedNotationLines: [],
    };
  }

  // Strip surrounding Markdown code fences if pasted from docs/chat
  if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```[a-zA-Z0-9_-]*\s*\r?\n?/, '').replace(/\r?\n?```\s*$/, '').trim();
  }

  let metadata: ParsedMatchMetadata = { format: 'ACTION_LOG_TEXT' };
  let steps: ParsedStep[] = [];
  const warnings: string[] = [];

  // 1. Try JSON / JSONL
  let parsedAsJson = false;
  if (cleaned.startsWith('{') || cleaned.startsWith('[')) {
    try {
      const data = JSON.parse(cleaned);
      parsedAsJson = true;
      if (Array.isArray(data)) {
        metadata = { format: 'AI_JSON_RECORD' };
        for (const item of data) {
          if (item && typeof item === 'object') {
            const st = parseJsonMoveItem(item as Record<string, unknown>);
            if (st) steps.push(st);
          }
        }
      } else if (data && typeof data === 'object') {
        const obj = data as Record<string, unknown>;
        const rawWinner =
          typeof obj.winner === 'string'
            ? obj.winner.toUpperCase()
            : typeof obj.result === 'string'
            ? obj.result.toUpperCase()
            : null;
        const reportedScoresObj =
          obj.final_scores && typeof obj.final_scores === 'object'
            ? (obj.final_scores as Record<string, unknown>)
            : null;
        metadata = {
          format: 'AI_JSON_RECORD',
          gameId: typeof obj.game_id === 'string' ? obj.game_id : undefined,
          redAgent:
            typeof obj.agent_red === 'string'
              ? obj.agent_red
              : typeof obj.red_player === 'string'
              ? obj.red_player
              : undefined,
          blueAgent:
            typeof obj.agent_blue === 'string'
              ? obj.agent_blue
              : typeof obj.blue_player === 'string'
              ? obj.blue_player
              : undefined,
          redConfigId: typeof obj.red_config_id === 'string' ? obj.red_config_id : undefined,
          blueConfigId: typeof obj.blue_config_id === 'string' ? obj.blue_config_id : undefined,
          winner: rawWinner,
          resultStatus:
            typeof obj.result_status === 'string' ? obj.result_status : undefined,
          terminationReason:
            typeof obj.termination_reason === 'string'
              ? obj.termination_reason
              : undefined,
          seed: typeof obj.seed === 'number' ? obj.seed : null,
          turnCount: typeof obj.turn_count === 'number' ? obj.turn_count : null,
          durationSec: typeof obj.duration_sec === 'number' ? obj.duration_sec : null,
          reportedFinalScores: reportedScoresObj
            ? {
                RED: Number(reportedScoresObj.RED ?? reportedScoresObj.red ?? 0),
                BLUE: Number(reportedScoresObj.BLUE ?? reportedScoresObj.blue ?? 0),
              }
            : null,
        };

        let rawMovesList: unknown[] = [];
        if (Array.isArray(obj.moves)) {
          rawMovesList = obj.moves;
        } else if (Array.isArray(obj.events)) {
          rawMovesList = obj.events;
        } else if (Array.isArray(obj.turns)) {
          for (const t of obj.turns) {
            if (t && typeof t === 'object') {
              const turnObj = t as Record<string, unknown>;
              const turnSide = turnObj.side ?? turnObj.player;
              const turnId = turnObj.turn_id ?? turnObj.turn_number;
              const actionsArr = Array.isArray(turnObj.actions) ? turnObj.actions : [];
              for (const act of actionsArr) {
                if (act && typeof act === 'object') {
                  rawMovesList.push({
                    side: turnSide,
                    player: turnSide,
                    turn_id: turnId,
                    turn_number: turnId,
                    ...(act as Record<string, unknown>),
                  });
                }
              }
            }
          }
        } else if (Array.isArray(obj.actions)) {
          rawMovesList = obj.actions;
        }

        for (const item of rawMovesList) {
          if (item && typeof item === 'object') {
            const st = parseJsonMoveItem(item as Record<string, unknown>);
            if (st) steps.push(st);
          }
        }
      }
    } catch {
      // Try line-by-line JSONL
      const lines = cleaned.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
      const jsonItems: Record<string, unknown>[] = [];
      let allJson = lines.length > 0;
      for (const l of lines) {
        if (!l.startsWith('{')) {
          allJson = false;
          break;
        }
        try {
          jsonItems.push(JSON.parse(l) as Record<string, unknown>);
        } catch {
          allJson = false;
          break;
        }
      }
      if (allJson && jsonItems.length > 0) {
        parsedAsJson = true;
        if (Array.isArray(jsonItems[0].moves)) {
          const obj = jsonItems[0];
          if (jsonItems.length > 1) {
            warnings.push(
              `Phát hiện ${jsonItems.length} ván trong JSONL; đang phát lại ván đầu tiên (${obj.game_id || '#1'}).`
            );
          }
          metadata = {
            format: 'AI_JSONL',
            gameId: typeof obj.game_id === 'string' ? obj.game_id : undefined,
            redAgent: typeof obj.agent_red === 'string' ? obj.agent_red : undefined,
            blueAgent: typeof obj.agent_blue === 'string' ? obj.agent_blue : undefined,
            winner: typeof obj.winner === 'string' ? obj.winner.toUpperCase() : null,
            terminationReason:
              typeof obj.termination_reason === 'string'
                ? obj.termination_reason
                : undefined,
            seed: typeof obj.seed === 'number' ? obj.seed : null,
          };
          for (const item of obj.moves as unknown[]) {
            if (item && typeof item === 'object') {
              const st = parseJsonMoveItem(item as Record<string, unknown>);
              if (st) steps.push(st);
            }
          }
        } else {
          metadata = { format: 'AI_JSONL' };
          for (const item of jsonItems) {
            const st = parseJsonMoveItem(item);
            if (st) steps.push(st);
          }
        }
      }
    }
  }

  // 2. Try selected_action stream or COTULENH / ActionLog text
  if (!parsedAsJson) {
    const rawLines = cleaned.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    const streamSteps: ParsedStep[] = [];
    let isPureSelectedActionStream = rawLines.length > 0;
    for (const line of rawLines) {
      const strippedPrefix = line.replace(/^(?:\d+[.)]\s*)?(?:(?:Bên\s+)?(?:Đỏ|Do|Xanh|Red|Blue)\s*:?\s*)?/i, '').trim();
      const tokenMatch = strippedPrefix.match(
        /((?:MOVE|DEPLOY|STACK_MOVE|CAPTURE|CAPTURE_REPLACE|CAPTURE_STAND|BOMB|BOMBARD|BOARD|PICKUP):(?:\([^)]*\)|\S)+|CMD:(?:END_TURN|CONFIRM_DEPLOYMENT))/i
      );
      if (tokenMatch && tokenMatch[1].length >= strippedPrefix.length * 0.45) {
        const cleanToken = tokenMatch[1].replace(/[,;]+$/, '');
        const prefixSideMatch = line.match(/\b(Đỏ|Xanh|Red|Blue)\b/i);
        const sideHint = prefixSideMatch ? normalizeSide(prefixSideMatch[1]) : undefined;
        const parsed = parseSelectedActionString(cleanToken, sideHint);
        if (parsed) {
          streamSteps.push(parsed);
          continue;
        }
      }
      isPureSelectedActionStream = false;
      break;
    }

    if (isPureSelectedActionStream && streamSteps.length > 0) {
      metadata = { format: 'SELECTED_ACTION_STREAM' };
      steps = streamSteps;
    } else {
      const textParsed = splitNotationText(cleaned);
      metadata = {
        format: textParsed.format,
        ...textParsed.metadata,
      };
      steps = textParsed.steps;
      warnings.push(...textParsed.warnings);
    }
  }

  if (steps.length === 0) {
    return {
      success: false,
      error:
        'Không nhận diện được nước đi hợp lệ nào. Hãy kiểm tra lại định dạng biên bản hoặc JSON log.',
      warnings,
      metadata,
      frames: [],
      normalizedNotationLines: [],
    };
  }

  // 3. Reconstruct Frame-by-Frame Game State
  let pieces = getInitialPieces();
  let scores = { RED: 0, BLUE: 0 };
  let capturedPieces: PieceState[] = [];
  let sideToMove: Side = 'RED';
  let activeCompound = null as ActiveCompoundState | null;
  let moveCounter = 0;
  let roundCounter = 1;
  let lastTurnOwner: Side | null = null;

  const frames: AnalysisFrame[] = [
    {
      stepIndex: 0,
      turnNumber: 1,
      sideToMove: 'RED',
      pieces: clonePieces(pieces),
      scores: { ...scores },
      capturedPieces: [],
      lastMove: null,
      activeCompound: null,
      telemetry: null,
      compoundEventTag: null,
      carriedCount: 0,
      focusPieceId: null,
    },
  ];
  const normalizedNotationLines: string[] = [];

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    const nextStep = i + 1 < steps.length ? steps[i + 1] : null;
    const actingSide: Side = resolveStepActingSide(step, pieces, sideToMove, activeCompound);

    if (activeCompound && actingSide !== sideToMove) {
      activeCompound = null;
    }
    const currentCompound: ActiveCompoundState | null = activeCompound;

    if (lastTurnOwner === 'BLUE' && actingSide === 'RED') {
      roundCounter += 1;
    }
    lastTurnOwner = actingSide;
    const turnDisplay = step.turnNumber ?? roundCounter;

    if (step.kind === 'END_TURN') {
      const nextSide: Side = actingSide === 'RED' ? 'BLUE' : 'RED';
      const fallbackActorId =
        currentCompound?.memberIds.find((id) =>
          pieces.some((p) => p.is_alive && p.piece_id === id)
        ) ||
        pieces.find((p) => p.is_alive && p.side === actingSide)?.piece_id ||
        'COMPOUND';
      const endAction: LegalAction = {
        action_id: `replay_end_${i}`,
        action_type: 'END_TURN',
        piece_id: fallbackActorId,
        from_pos: currentCompound?.originPos || { x: 0, y: 0 },
        to_pos: currentCompound?.originPos || { x: 0, y: 0 },
        target_piece_id: null,
        notation: step.notationHint || 'CONFIRM_DEPLOYMENT',
        description: 'Hoàn tất lượt tổ hợp',
      };
      const outcome = applyMockAction(endAction, pieces, true);
      scores = {
        RED: scores.RED + outcome.event.score_delta.RED,
        BLUE: scores.BLUE + outcome.event.score_delta.BLUE,
      };
      moveCounter += 1;
      const moveRec: MoveRecord = {
        move_number: moveCounter,
        side: actingSide,
        action: endAction,
        notation: outcome.event.notation || 'CONFIRM_DEPLOYMENT',
        captured_piece_type: null,
        timestamp: i,
      };
      activeCompound = null;
      sideToMove = nextSide;
      normalizedNotationLines.push(
        `${turnDisplay}. ${actingSide === 'RED' ? 'Đỏ' : 'Xanh'}: ${moveRec.notation}`
      );
      frames.push({
        stepIndex: frames.length,
        turnNumber: turnDisplay,
        sideToMove,
        pieces: clonePieces(pieces),
        scores: { ...scores },
        capturedPieces: clonePieces(capturedPieces),
        lastMove: moveRec,
        activeCompound: null,
        telemetry: step.telemetry || null,
        compoundEventTag: 'END_TURN',
        carriedCount: 0,
        focusPieceId: null,
      });
      continue;
    }

    const actor = resolveActorPiece(step, pieces, actingSide, currentCompound);
    if (!actor) {
      warnings.push(
        `Bước ${i + 1}: Không tìm thấy quân (${step.pieceId || step.pieceType || '?'}) tại [${step.fromPos?.y ?? '?'} ; ${step.fromPos?.x ?? '?'}] bên ${actingSide}. Dừng phát lại tại đây.`
      );
      break;
    }

    const originPos: Position = currentCompound
      ? { ...currentCompound.originPos }
      : { ...getRootCarrier(actor, pieces).position };
    const fromPos: Position = step.fromPos || originPos;
    const resolvedTarget = resolveTargetPiece(step, actor, pieces);
    const toPos: Position =
      step.toPos || (resolvedTarget ? { ...resolvedTarget.position } : { ...fromPos });

    let finalActionType: ActionType = step.actionType || 'MOVE';
    // Guard: if raw capture/bomb was recorded against friendly piece to board, map appropriately
    if (
      finalActionType === 'BOARD' &&
      resolvedTarget &&
      resolvedTarget.side !== actor.side
    ) {
      finalActionType = 'CAPTURE_REPLACE';
    }
    // Check AA survival heuristic or standard capture replacement
    if (
      finalActionType === 'MOVE' &&
      resolvedTarget &&
      resolvedTarget.side !== actor.side &&
      actor.type === 'AIRCRAFT'
    ) {
      finalActionType = 'CAPTURE_REPLACE';
    }

    const carryCargo = inferCarryCargoForStep(
      step,
      i,
      steps,
      actor,
      actingSide,
      fromPos,
      toPos,
      finalActionType,
      pieces
    );

    const actorWasCarried = actor.carried_by_id != null;
    const oldRoot = getRootCarrier(actor, pieces);
    const actorDescBefore = getAllCarriedPieceIds(actor.piece_id, pieces);
    const isCarrierPickingUp =
      finalActionType === 'BOARD' &&
      resolvedTarget != null &&
      canBoardCarrier(resolvedTarget, actor, pieces);

    // Track compound state for stay-in-stack check (mirrors packages/commander_game_engine/engine.py)
    let memberIds: string[] = [];
    if (currentCompound) {
      memberIds = currentCompound.memberIds;
    } else if (finalActionType !== 'BOARD') {
      if (actorWasCarried && oldRoot.type !== 'HEADQUARTERS') {
        memberIds = [oldRoot.piece_id, ...getAllCarriedPieceIds(oldRoot.piece_id, pieces)];
      } else if (
        !actorWasCarried &&
        actor.type !== 'HEADQUARTERS' &&
        actorDescBefore.length > 0 &&
        (finalActionType === 'CAPTURE_STAND' || carryCargo === false)
      ) {
        memberIds = [actor.piece_id, ...actorDescBefore];
      }
    }

    const previouslyMoved: string[] = currentCompound ? currentCompound.movedPieceIds : [];
    const newMoved: string[] = previouslyMoved.includes(actor.piece_id)
      ? [...previouslyMoved]
      : [...previouslyMoved, actor.piece_id];
    const movedAway =
      finalActionType !== 'CAPTURE_STAND' &&
      (toPos.x !== originPos.x || toPos.y !== originPos.y);
    if (movedAway && carryCargo !== false) {
      for (const tcId of actorDescBefore) {
        if (!newMoved.includes(tcId)) newMoved.push(tcId);
      }
    }

    const builtNotation =
      step.notationHint ||
      buildNotationForStep(actor, finalActionType, fromPos, toPos, resolvedTarget);

    const legalAction: LegalAction = {
      action_id: `replay_act_${i}`,
      action_type: finalActionType,
      piece_id: actor.piece_id,
      from_pos: fromPos,
      to_pos: toPos,
      target_piece_id:
        finalActionType === 'MOVE'
          ? null
          : resolvedTarget
          ? resolvedTarget.piece_id
          : step.targetPieceId || null,
      notation: builtNotation,
      description: builtNotation,
      carry_cargo: carryCargo,
    };

    // Determine whether turn stays in compound after this step
    const prevAliveIds = new Set(pieces.filter((p) => p.is_alive).map((p) => p.piece_id));
    const explicitNextSameSide = Boolean(nextStep && nextStep.side === actingSide);
    const explicitNextOppositeSide = Boolean(nextStep && nextStep.side && nextStep.side !== actingSide);
    const previewOutcome = applyMockAction(legalAction, pieces, false);
    const previewRemainingAtOrigin = previewOutcome.nextPieces.filter(
      (p) =>
        p.is_alive &&
        memberIds.includes(p.piece_id) &&
        !newMoved.includes(p.piece_id) &&
        p.position.x === originPos.x &&
        p.position.y === originPos.y
    );
    const predictedCmdCaptured = Boolean(
      previewOutcome.capturedPiece && previewOutcome.capturedPiece.type === 'COMMANDER'
    );
    const nextActionCount = (currentCompound?.actionCount || 0) + 1;
    const canContinueCompound =
      !predictedCmdCaptured &&
      finalActionType !== 'BOARD' &&
      memberIds.length > 1 &&
      previewRemainingAtOrigin.length > 0 &&
      nextActionCount < 3;

    let staysInCompound = false;
    if (explicitNextOppositeSide) {
      staysInCompound = false;
    } else if (nextStep && nextStep.kind === 'END_TURN') {
      staysInCompound = canContinueCompound;
    } else if (nextStep && nextStep.kind === 'ACTION' && !nextStep.side) {
      // Unlabelled next line: stay in compound ONLY if it actually continues at originPos
      const matchesOriginMember =
        canContinueCompound &&
        nextStep.fromPos != null &&
        samePos(nextStep.fromPos, originPos) &&
        previewRemainingAtOrigin.some(
          (m) =>
            (!nextStep.pieceType || m.type === nextStep.pieceType) &&
            (!nextStep.pieceId || m.piece_id === nextStep.pieceId)
        );
      staysInCompound = matchesOriginMember;
    } else if (explicitNextSameSide) {
      staysInCompound = canContinueCompound;
    } else {
      // End of record (!nextStep) or standard compound continuation
      staysInCompound = canContinueCompound;
    }

    const { nextPieces, event, capturedPiece } = applyMockAction(
      legalAction,
      pieces,
      !staysInCompound
    );

    pieces = nextPieces;
    const newlyDead = nextPieces.filter((np) => !np.is_alive && prevAliveIds.has(np.piece_id));
    if (newlyDead.length > 0) {
      capturedPieces = [...capturedPieces, ...newlyDead];
    } else if (capturedPiece) {
      capturedPieces = [...capturedPieces, capturedPiece];
    }

    scores = {
      RED: scores.RED + event.score_delta.RED,
      BLUE: scores.BLUE + event.score_delta.BLUE,
    };

    moveCounter += 1;
    const formattedCanonical = buildNotationForStep(
      actor,
      finalActionType,
      fromPos,
      toPos,
      resolvedTarget
    );
    const displayNotation =
      step.notationHint && !step.notationHint.startsWith('MOVE:')
        ? step.notationHint
        : event.notation && !event.notation.startsWith('MOVE:')
        ? event.notation
        : formattedCanonical;

    const moveRec: MoveRecord = {
      move_number: moveCounter,
      side: actingSide,
      action: legalAction,
      notation: displayNotation,
      captured_piece_type: capturedPiece ? capturedPiece.type : null,
      timestamp: i,
    };

    if (staysInCompound && memberIds.length > 0) {
      activeCompound = {
        originPos,
        memberIds,
        movedPieceIds: newMoved,
        actionCount: nextActionCount,
      };
      sideToMove = actingSide;
    } else if (
      explicitNextSameSide &&
      !explicitNextOppositeSide &&
      nextStep?.kind !== 'END_TURN'
    ) {
      activeCompound = null;
      sideToMove = actingSide;
    } else {
      activeCompound = null;
      sideToMove = actingSide === 'RED' ? 'BLUE' : 'RED';
    }

    // Determine carried/compound UI tag and default inspector focus for this frame
    const actorAfter = pieces.find((p) => p.piece_id === actor.piece_id);
    const actorCargoAfter = actorAfter?.is_alive
      ? getAllCarriedPieceIds(actorAfter.piece_id, pieces).length
      : 0;
    const oldRootAlive = pieces.some((p) => p.is_alive && p.piece_id === oldRoot.piece_id);

    let compoundEventTag: CompoundEventTag | null = null;
    let carriedCount = 0;
    let focusPieceId: string | null = null;

    if (finalActionType === 'BOARD') {
      if (isCarrierPickingUp) {
        compoundEventTag = 'PICKUP';
        carriedCount = actorCargoAfter;
        focusPieceId = actor.piece_id;
      } else {
        compoundEventTag = 'BOARD';
        carriedCount = resolvedTarget
          ? getAllCarriedPieceIds(resolvedTarget.piece_id, pieces).length
          : 1;
        focusPieceId = resolvedTarget ? resolvedTarget.piece_id : actor.piece_id;
      }
    } else if (actorWasCarried && oldRoot.type !== 'HEADQUARTERS') {
      compoundEventTag = 'DEPLOY';
      carriedCount = oldRootAlive ? getAllCarriedPieceIds(oldRoot.piece_id, pieces).length : 0;
      focusPieceId = oldRootAlive ? oldRoot.piece_id : actor.piece_id;
    } else if (
      !actorWasCarried &&
      actor.type !== 'HEADQUARTERS' &&
      actorDescBefore.length > 0 &&
      (finalActionType === 'MOVE' || finalActionType === 'CAPTURE_REPLACE')
    ) {
      if (carryCargo === false) {
        compoundEventTag = 'SOLO_SPLIT';
        carriedCount = actorDescBefore.length;
        focusPieceId = activeCompound?.memberIds[0] || actor.piece_id;
      } else {
        compoundEventTag = 'CARRY_MOVE';
        carriedCount = actorCargoAfter || actorDescBefore.length;
        focusPieceId = actorAfter?.is_alive ? actor.piece_id : null;
      }
    } else if (finalActionType === 'CAPTURE_STAND' && actorDescBefore.length > 0) {
      compoundEventTag = 'CARRY_MOVE';
      carriedCount = actorCargoAfter || actorDescBefore.length;
      focusPieceId = actor.piece_id;
    } else if (currentCompound != null) {
      compoundEventTag = 'DEPLOY';
      carriedCount = actorCargoAfter;
      focusPieceId = currentCompound.memberIds[0] || actor.piece_id;
    }

    const needsCarryZeroSuffix =
      (finalActionType === 'MOVE' || finalActionType === 'CAPTURE_REPLACE') &&
      carryCargo === false &&
      actor.type !== 'HEADQUARTERS' &&
      actorDescBefore.length > 0 &&
      !/\{[^}]*carry(?:_cargo)?\s*=/i.test(displayNotation);

    const normalizedLineNote = needsCarryZeroSuffix
      ? `${displayNotation} {carry=0}`
      : displayNotation;

    normalizedNotationLines.push(
      `${turnDisplay}. ${actingSide === 'RED' ? 'Đỏ' : 'Xanh'}: ${normalizedLineNote}`
    );

    frames.push({
      stepIndex: frames.length,
      turnNumber: turnDisplay,
      sideToMove,
      pieces: clonePieces(pieces),
      scores: { ...scores },
      capturedPieces: clonePieces(capturedPieces),
      lastMove: moveRec,
      activeCompound: activeCompound
        ? {
            ...activeCompound,
            originPos: { ...activeCompound.originPos },
            memberIds: [...activeCompound.memberIds],
            movedPieceIds: [...activeCompound.movedPieceIds],
          }
        : null,
      telemetry: step.telemetry || null,
      compoundEventTag,
      carriedCount,
      focusPieceId,
    });
  }

  return {
    success: frames.length > 1,
    error:
      frames.length <= 1
        ? warnings[0] || 'Không thể tái tạo nước đi đầu tiên từ biên bản.'
        : undefined,
    warnings,
    metadata,
    frames,
    normalizedNotationLines,
  };
}
