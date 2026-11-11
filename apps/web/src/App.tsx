import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Header } from './components/Header/Header';
import { Home } from './components/Home/Home';
import { Board } from './components/Board/Board';
import { CompoundControlBar } from './components/Board/CompoundControlBar';
import { PieceDetail } from './components/PieceDetail/PieceDetail';
import { MoveHistory } from './components/MoveHistory/MoveHistory';
import { CapturedPieces } from './components/CapturedPieces/CapturedPieces';
import { GameAnalysisRecord } from './components/GameAnalysisRecord/GameAnalysisRecord';
import { GameOverModal } from './components/GameOverModal/GameOverModal';
import { ConfirmModal } from './components/ConfirmModal/ConfirmModal';
import {
  PieceState,
  Side,
  LegalAction,
  MoveRecord,
  MatchSnapshot,
  GameStatus,
  GameResult,
  GameMode,
  ActiveCompoundState,
  GameStateDTO,
  ActionType,
  TerminationReason,
} from './types';
import { getInitialPieces } from './utils/initialBoard';
import {
  getMockLegalActions,
  applyMockAction,
  getAllCarriedPieceIds,
  selectSmartAiAction,
  getRootCarrier,
  delayedSolitaryHqCommanderId,
  evaluateTurnHandoffOutcome,
} from './services/mockGameService';
import { apiClient, ApiError } from './services/apiClient';
import { Language, translations } from './i18n';
import styles from './App.module.css';

function normalizePieces(raw: PieceState[]): PieceState[] {
  const posFixed = raw.map((p) => {
    if (p.is_alive && p.carried_by_id) {
      const root = getRootCarrier(p, raw);
      return { ...p, position: { ...root.position } };
    }
    return p;
  });
  return posFixed.map((p) => ({
    ...p,
    carrying_piece_ids: posFixed
      .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
      .map((other) => other.piece_id),
  }));
}

function extractCompoundState(
  gs: GameStateDTO,
  normalizedPieces: PieceState[]
): ActiveCompoundState | null {
  if (gs.turn_phase !== 'STACK_ACTIVE') return null;
  const originPos = gs.compound_origin ? { ...gs.compound_origin } : { x: 0, y: 0 };
  const memberIds =
    gs.compound_member_ids && gs.compound_member_ids.length > 0
      ? [...gs.compound_member_ids]
      : normalizedPieces
          .filter(
            (p) =>
              p.is_alive &&
              p.side === gs.side_to_move &&
              p.position.x === originPos.x &&
              p.position.y === originPos.y
          )
          .map((p) => p.piece_id);
  const movedPieceIds = gs.compound_moved_piece_ids ? [...gs.compound_moved_piece_ids] : [];
  return {
    originPos,
    memberIds,
    movedPieceIds,
    actionCount: movedPieceIds.length,
  };
}

function clonePiecesSnapshot(list: PieceState[]): PieceState[] {
  return list.map((p) => ({
    ...p,
    position: { ...p.position },
    carrying_piece_ids: [...(p.carrying_piece_ids || [])],
  }));
}

function cloneCompoundSnapshot(
  compound: ActiveCompoundState | null
): ActiveCompoundState | null {
  if (!compound) return null;
  return {
    originPos: { ...compound.originPos },
    memberIds: [...compound.memberIds],
    movedPieceIds: [...compound.movedPieceIds],
    actionCount: compound.actionCount,
  };
}

function buildInitialSnapshot(initialPieces: PieceState[]): MatchSnapshot {
  return {
    snapshotIndex: 0,
    pieces: clonePiecesSnapshot(initialPieces),
    scores: { RED: 0, BLUE: 0 },
    capturedPieces: [],
    sideToMove: 'RED',
    lastMove: null,
    activeCompound: null,
    movesCount: 0,
  };
}

function buildGameResultFromDTO(
  gs: GameStateDTO,
  nextMoves: MoveRecord[],
  durationSeconds: number,
  fallbackScores: { RED: number; BLUE: number },
  fallbackWinnerSide: Side
): GameResult {
  const rawWinner = gs.result?.winner;
  const winnerValue: Side | 'DRAW' =
    rawWinner === 'RED' || rawWinner === 'BLUE' || rawWinner === 'DRAW'
      ? rawWinner
      : fallbackWinnerSide;
  const reasonValue: TerminationReason =
    gs.result?.reason || (winnerValue === 'DRAW' ? 'STALEMATE' : 'CHECKMATE');
  return {
    winner: winnerValue,
    reason: reasonValue,
    final_scores: gs.result?.final_scores || gs.scores || fallbackScores,
    total_turns: Math.max(1, Math.ceil(nextMoves.length / 2)),
    total_moves: nextMoves.length,
    duration_seconds: durationSeconds,
    captured_commander_side:
      reasonValue === 'COMMANDER_CAPTURED' && winnerValue !== 'DRAW'
        ? winnerValue === 'BLUE'
          ? 'RED'
          : 'BLUE'
        : null,
  };
}

export const App: React.FC = () => {
  // Language Preference with LocalStorage persistence
  const [lang, setLang] = useState<Language>(() => {
    const saved = localStorage.getItem('commander_chess_lang');
    return saved === 'en' || saved === 'vi' ? saved : 'vi';
  });

  // Default to 'home' as per CR-003 requirements
  const [activeTab, setActiveTab] = useState<string>('home');
  const [gameMode, setGameMode] = useState<GameMode>('HUMAN_VS_AI');
  const [isAiThinking, setIsAiThinking] = useState<boolean>(false);
  const [pieces, setPieces] = useState<PieceState[]>(() => getInitialPieces());
  const [selectedPieceId, setSelectedPieceId] = useState<string | null>(null);
  const [sideToMove, setSideToMove] = useState<Side>('RED');
  const [scores, setScores] = useState<{ RED: number; BLUE: number }>({ RED: 0, BLUE: 0 });
  const [moves, setMoves] = useState<MoveRecord[]>([]);
  const [capturedPieces, setCapturedPieces] = useState<PieceState[]>([]);
  const [status, setStatus] = useState<GameStatus>('IN_PROGRESS');
  const [gameResult, setGameResult] = useState<GameResult | null>(null);
  const [isGameOverModalOpen, setIsGameOverModalOpen] = useState<boolean>(false);
  const [confirmModalType, setConfirmModalType] = useState<'NEW_GAME' | 'RESIGN' | 'DRAW' | null>(null);
  const [matchSeconds, setMatchSeconds] = useState<number>(0);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [gameSessionId, setGameSessionId] = useState<string | null>(null);
  const [stateVersion, setStateVersion] = useState<number>(1);
  const [matchSnapshots, setMatchSnapshots] = useState<MatchSnapshot[]>(() => [
    buildInitialSnapshot(getInitialPieces()),
  ]);
  const [reviewIndex, setReviewIndex] = useState<number | null>(null);
  const [boardFlipped, setBoardFlipped] = useState<boolean>(false);

  const stateVersionRef = useRef<number>(1);
  const piecesRef = useRef<PieceState[]>(pieces);
  piecesRef.current = pieces;
  const scoresRef = useRef<{ RED: number; BLUE: number }>(scores);
  scoresRef.current = scores;
  const movesRef = useRef<MoveRecord[]>(moves);
  movesRef.current = moves;
  const capturedPiecesRef = useRef<PieceState[]>(capturedPieces);
  capturedPiecesRef.current = capturedPieces;
  const matchSnapshotsRef = useRef<MatchSnapshot[]>(matchSnapshots);
  matchSnapshotsRef.current = matchSnapshots;

  const syncStateVersion = (newVersion: number) => {
    stateVersionRef.current = newVersion;
    setStateVersion(newVersion);
  };

  const appendMatchSnapshot = (snapData: Omit<MatchSnapshot, 'snapshotIndex'>) => {
    const nextList: MatchSnapshot[] = [
      ...matchSnapshotsRef.current,
      {
        snapshotIndex: matchSnapshotsRef.current.length,
        pieces: clonePiecesSnapshot(snapData.pieces),
        scores: { ...snapData.scores },
        capturedPieces: clonePiecesSnapshot(snapData.capturedPieces),
        sideToMove: snapData.sideToMove,
        lastMove: snapData.lastMove,
        activeCompound: cloneCompoundSnapshot(snapData.activeCompound),
        movesCount: snapData.movesCount,
      },
    ];
    matchSnapshotsRef.current = nextList;
    setMatchSnapshots(nextList);
    setReviewIndex(null);
  };

  const [activeCompound, setActiveCompound] = useState<ActiveCompoundState | null>(null);
  const [carryCargoWithMovement, setCarryCargoWithMovement] = useState<boolean>(true);

  const maxSnapshotIndex = Math.max(0, matchSnapshots.length - 1);
  const effectiveSnapshotIndex =
    reviewIndex === null ? maxSnapshotIndex : Math.min(Math.max(0, reviewIndex), maxSnapshotIndex);
  const isReviewingPast = reviewIndex !== null && reviewIndex < maxSnapshotIndex;
  const displayedSnapshot =
    matchSnapshots[effectiveSnapshotIndex] || matchSnapshots[maxSnapshotIndex];
  const displayedPieces = isReviewingPast ? displayedSnapshot.pieces : pieces;
  const displayedScores = isReviewingPast ? displayedSnapshot.scores : scores;
  const displayedCapturedPieces = isReviewingPast
    ? displayedSnapshot.capturedPieces
    : capturedPieces;
  const displayedLastMove = isReviewingPast
    ? displayedSnapshot.lastMove
    : moves.length > 0
    ? moves[moves.length - 1]
    : null;
  const displayedActiveCompound = isReviewingPast
    ? displayedSnapshot.activeCompound
    : activeCompound;
  const displayedSideToMove = isReviewingPast ? displayedSnapshot.sideToMove : sideToMove;

  const handleNavigateSnapshot = (targetIdx: number | null) => {
    const returningLive = targetIdx === null || targetIdx >= maxSnapshotIndex;
    if (returningLive) {
      if (isReviewingPast) {
        setSelectedPieceId(null);
      }
      setReviewIndex(null);
    } else {
      setReviewIndex(Math.max(0, targetIdx));
    }
    setCarryCargoWithMovement(true);
  };

  const t = translations[lang];

  useEffect(() => {
    localStorage.setItem('commander_chess_lang', lang);
  }, [lang]);

  // Probe FastAPI Backend and establish active game session
  useEffect(() => {
    let isMounted = true;
    const probe = async () => {
      try {
        const res = await apiClient.checkHealth();
        if (res.status === 'ok' && isMounted) {
          setBackendOnline(true);
          const session = await apiClient.createGame({
            mode: 'HUMAN_VS_AI',
            player_side: 'RED',
            blue_agent_id: 'RandomAgent',
          });
          if (isMounted) {
            setGameSessionId(session.game_id);
            syncStateVersion(session.state_version);
            if (session.pieces && session.pieces.length > 0) {
              const initNorm = normalizePieces(session.pieces);
              setPieces(initNorm);
              if (movesRef.current.length === 0) {
                const initSnaps = [buildInitialSnapshot(initNorm)];
                matchSnapshotsRef.current = initSnaps;
                setMatchSnapshots(initSnaps);
              }
            }
          }
        }
      } catch {
        if (isMounted) {
          setBackendOnline(false);
        }
      }
    };
    probe();
    return () => {
      isMounted = false;
    };
  }, []);

  // Combat Match Timer - runs while game is IN_PROGRESS on the board tab
  useEffect(() => {
    if (status !== 'IN_PROGRESS' || activeTab !== 'play') return;
    const interval = setInterval(() => {
      setMatchSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [status, activeTab]);

  const formattedTime = useMemo(() => {
    const mins = Math.floor(matchSeconds / 60);
    const secs = matchSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, [matchSeconds]);

  const selectedPiece = displayedPieces.find((p) => p.piece_id === selectedPieceId) || null;

  // Keyboard navigation for in-game move review (Đầu / Lùi / Tiến / Cuối)
  useEffect(() => {
    if (activeTab !== 'play' || confirmModalType !== null || isGameOverModalOpen) return;
    if (maxSnapshotIndex <= 0) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'TEXTAREA' || tag === 'INPUT' || tag === 'SELECT') return;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handleNavigateSnapshot(Math.max(0, effectiveSnapshotIndex - 1));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNavigateSnapshot(effectiveSnapshotIndex + 1);
      } else if (e.key === 'Home') {
        e.preventDefault();
        handleNavigateSnapshot(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        handleNavigateSnapshot(null);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [
    activeTab,
    confirmModalType,
    isGameOverModalOpen,
    maxSnapshotIndex,
    effectiveSnapshotIndex,
  ]);

  // Calculate legal actions for currently selected piece of active side
  const legalActions = useMemo(() => {
    if (status === 'GAME_OVER' || isAiThinking || isReviewingPast) return [];
    if (!selectedPiece || selectedPiece.side !== sideToMove) return [];
    // Quy tắc phong Anh hùng trễ: nếu phe chỉ còn 1 Sở chỉ huy + Tư lệnh đang núp bên trong, bắt buộc Tư lệnh thoát ra trước
    const trapCmdId = delayedSolitaryHqCommanderId(pieces, sideToMove);
    if (trapCmdId !== null && selectedPiece.piece_id !== trapCmdId) {
      return [];
    }
    // Nếu đang trong lượt tác chiến của tổ hợp và quân này đã đi rồi -> không còn nước đi
    if (activeCompound && activeCompound.movedPieceIds.includes(selectedPiece.piece_id)) {
      return [];
    }
    return getMockLegalActions(selectedPiece, pieces, carryCargoWithMovement);
  }, [
    status,
    isAiThinking,
    isReviewingPast,
    selectedPiece,
    sideToMove,
    pieces,
    activeCompound,
    carryCargoWithMovement,
  ]);

  const handleSelectPiece = (piece: PieceState) => {
    setCarryCargoWithMovement(true);
    if (isReviewingPast) {
      setSelectedPieceId((prev) => (prev === piece.piece_id ? null : piece.piece_id));
      return;
    }
    if (status === 'GAME_OVER' || isAiThinking) return;
    // Trong chế độ đấu với AI, người chơi không thể chọn quân của AI (Xanh)
    if (gameMode === 'HUMAN_VS_AI' && piece.side === 'BLUE') {
      return;
    }

    // QUY TẮC 3: Khi đang trong lượt tác chiến tổ hợp (STACK_ACTIVE), người chơi không thể điều khiển quân ở ngoài tổ hợp đó!
    if (activeCompound) {
      if (!activeCompound.memberIds.includes(piece.piece_id)) {
        return;
      }
      // Không thể chọn quân đã hoàn thành nước đi trong lượt này
      if (activeCompound.movedPieceIds.includes(piece.piece_id)) {
        return;
      }
    }

    // Ở sở chỉ huy thường (chưa phong Anh hùng), sở chỉ huy không thể di chuyển nên nếu có Tư lệnh trong đó,
    // click vào sẽ tự động chọn Tư lệnh để di chuyển ra ngoài!
    if (piece.type === 'HEADQUARTERS' && !piece.is_hero) {
      const carriedCommander = pieces.find(
        (p) => p.is_alive && p.carried_by_id === piece.piece_id && p.type === 'COMMANDER'
      );
      if (carriedCommander) {
        if (activeCompound && activeCompound.movedPieceIds.includes(carriedCommander.piece_id)) {
          return;
        }
        if (selectedPieceId === carriedCommander.piece_id) {
          setSelectedPieceId(null);
        } else {
          setSelectedPieceId(carriedCommander.piece_id);
        }
        return;
      }
    }

    if (selectedPieceId === piece.piece_id) {
      setSelectedPieceId(null);
    } else {
      setSelectedPieceId(piece.piece_id);
    }
  };

  const handleConfirmCompound = async () => {
    if (isReviewingPast) return;
    const currentSide = sideToMove;
    const nextSideFallback: Side = currentSide === 'RED' ? 'BLUE' : 'RED';
    const compoundSnapshot = activeCompound;
    const currentPieces = piecesRef.current;

    setSelectedPieceId(null);
    setActiveCompound(null);
    setCarryCargoWithMovement(true);

    // Đồng bộ kết thúc lượt tổ hợp sang FastAPI backend (nếu online)
    if (backendOnline && gameSessionId) {
      try {
        const gs = await apiClient.endTurn(gameSessionId, stateVersionRef.current);
        syncStateVersion(gs.state_version);
        const nextNormalized =
          gs.pieces && gs.pieces.length > 0 ? normalizePieces(gs.pieces) : currentPieces;
        setPieces(nextNormalized);
        const nextScores = gs.scores
          ? { RED: gs.scores.RED, BLUE: gs.scores.BLUE }
          : { ...scoresRef.current };
        if (gs.scores) {
          setScores(nextScores);
        }
        const notation = gs.last_event?.notation || 'CONFIRM_DEPLOYMENT';
        const confirmAction: LegalAction = {
          action_id: `confirm_${Date.now()}`,
          action_type: 'END_TURN',
          piece_id: 'COMPOUND',
          from_pos: compoundSnapshot?.originPos || { x: 0, y: 0 },
          to_pos: compoundSnapshot?.originPos || { x: 0, y: 0 },
          target_piece_id: null,
          notation,
          description:
            lang === 'vi'
              ? 'Đã xác nhận hoàn tất lượt tác chiến của tổ hợp.'
              : 'Compound deployment turn completed.',
        };
        const confirmRecord: MoveRecord = {
          move_number: movesRef.current.length + 1,
          side: currentSide,
          action: confirmAction,
          notation,
          captured_piece_type: null,
          timestamp: Date.now(),
        };
        const nextMoves: MoveRecord[] = [...movesRef.current, confirmRecord];
        setMoves(nextMoves);

        const nextCompound = extractCompoundState(gs, nextNormalized);
        appendMatchSnapshot({
          pieces: nextNormalized,
          scores: nextScores,
          capturedPieces: capturedPiecesRef.current,
          sideToMove: gs.side_to_move,
          lastMove: confirmRecord,
          activeCompound: nextCompound,
          movesCount: nextMoves.length,
        });

        if (gs.status === 'GAME_OVER') {
          setStatus('GAME_OVER');
          setGameResult(
            buildGameResultFromDTO(gs, nextMoves, matchSeconds, nextScores, currentSide)
          );
          setIsGameOverModalOpen(true);
          return;
        }

        setActiveCompound(nextCompound);
        setSideToMove(gs.side_to_move);
        return;
      } catch (err) {
        console.warn('Backend endTurn failed:', err);
        if (err instanceof ApiError) {
          try {
            const fresh = await apiClient.getGame(gameSessionId);
            syncStateVersion(fresh.state_version);
            const freshNormalized = normalizePieces(fresh.pieces);
            setPieces(freshNormalized);
            setScores({ RED: fresh.scores.RED, BLUE: fresh.scores.BLUE });
            setActiveCompound(extractCompoundState(fresh, freshNormalized));
            setSideToMove(fresh.side_to_move);
            if (fresh.status === 'GAME_OVER') {
              setStatus('GAME_OVER');
              setGameResult(buildGameResultFromDTO(fresh, movesRef.current, matchSeconds, scoresRef.current, currentSide));
              setIsGameOverModalOpen(true);
            }
            return;
          } catch {
            // Fall through to local handling if getGame also fails
          }
        } else {
          setBackendOnline(false);
        }
      }
    }

    const endTurnActorId =
      compoundSnapshot?.memberIds.find((id) =>
        currentPieces.some((p) => p.is_alive && p.piece_id === id)
      ) ||
      currentPieces.find((p) => p.is_alive && p.side === currentSide)?.piece_id ||
      'COMPOUND';
    const endTurnAction: LegalAction = {
      action_id: `confirm_${Date.now()}`,
      action_type: 'END_TURN',
      piece_id: endTurnActorId,
      from_pos: compoundSnapshot?.originPos || { x: 0, y: 0 },
      to_pos: compoundSnapshot?.originPos || { x: 0, y: 0 },
      target_piece_id: null,
      notation: 'CONFIRM_DEPLOYMENT',
      description:
        lang === 'vi'
          ? 'Đã xác nhận hoàn tất lượt tác chiến của tổ hợp.'
          : 'Compound deployment turn completed.',
    };
    const { event } = applyMockAction(endTurnAction, currentPieces, true);
    const finalScores = {
      RED: scoresRef.current.RED + event.score_delta.RED,
      BLUE: scoresRef.current.BLUE + event.score_delta.BLUE,
    };
    if (event.score_delta.RED > 0 || event.score_delta.BLUE > 0) {
      setScores(finalScores);
    }
    const confirmRecord: MoveRecord = {
      move_number: movesRef.current.length + 1,
      side: currentSide,
      action: endTurnAction,
      notation: event.notation || 'CONFIRM_DEPLOYMENT',
      captured_piece_type: null,
      timestamp: Date.now(),
    };
    const nextMoves: MoveRecord[] = [...movesRef.current, confirmRecord];
    setMoves(nextMoves);

    appendMatchSnapshot({
      pieces: currentPieces,
      scores: finalScores,
      capturedPieces: capturedPiecesRef.current,
      sideToMove: nextSideFallback,
      lastMove: confirmRecord,
      activeCompound: null,
      movesCount: nextMoves.length,
    });

    if (event.details?.is_checkmate || event.details?.is_stalemate) {
      const isStale = Boolean(event.details?.is_stalemate);
      setStatus('GAME_OVER');
      setGameResult({
        winner: isStale ? 'DRAW' : currentSide,
        reason: isStale ? 'STALEMATE' : 'CHECKMATE',
        final_scores: finalScores,
        total_turns: Math.ceil(nextMoves.length / 2),
        total_moves: nextMoves.length,
        duration_seconds: matchSeconds,
        captured_commander_side: null,
      });
      setIsGameOverModalOpen(true);
      return;
    }

    setSideToMove(nextSideFallback);
  };

  const triggerAiStep = async () => {
    if (status === 'GAME_OVER' || isAiThinking || isReviewingPast) return;
    setIsAiThinking(true);
    const actingSide = sideToMove;

    try {
      if (backendOnline && gameSessionId) {
        const prevPieces = piecesRef.current;
        const aiRes = await apiClient.aiStep(gameSessionId);
        syncStateVersion(aiRes.state_version);

        // PHÒNG THỦ TUYỆT ĐỐI: Kiểm tra quân thực hiện nước đi của AI
        if (aiRes.event.actor_id && aiRes.event.actor_id !== 'COMPOUND') {
          const actorPiece = prevPieces.find((p) => p.piece_id === aiRes.event.actor_id);
          if (actorPiece && actorPiece.side !== actingSide) {
            console.error('LỖI AN TOÀN: Backend AI trả về quân không thuộc lượt hiện tại! Từ chối thực thi nước đi này.');
            return;
          }
        }

        const nextNormalized =
          aiRes.game_state.pieces && aiRes.game_state.pieces.length > 0
            ? normalizePieces(aiRes.game_state.pieces)
            : prevPieces;
        const prevDeadIds = new Set(prevPieces.filter((p) => !p.is_alive).map((p) => p.piece_id));
        const newlyDead = nextNormalized.filter((p) => !p.is_alive && !prevDeadIds.has(p.piece_id));
        const nextCaptured =
          newlyDead.length > 0
            ? [...capturedPiecesRef.current, ...newlyDead]
            : capturedPiecesRef.current;
        if (newlyDead.length > 0) {
          setCapturedPieces(nextCaptured);
        }
        setPieces(nextNormalized);

        const nextScores = aiRes.game_state.scores
          ? {
              RED: aiRes.game_state.scores.RED,
              BLUE: aiRes.game_state.scores.BLUE,
            }
          : { ...scoresRef.current };
        if (aiRes.game_state.scores) {
          setScores(nextScores);
        }

        const targetPiece = aiRes.event.target_id
          ? prevPieces.find((p) => p.piece_id === aiRes.event.target_id) || null
          : null;
        const actorBefore = prevPieces.find((p) => p.piece_id === aiRes.event.actor_id);
        const fromPos = aiRes.event.details?.from_pos
          ? { ...aiRes.event.details.from_pos }
          : actorBefore
          ? { ...actorBefore.position }
          : { x: 0, y: 0 };
        const toPos = aiRes.event.details?.to_pos
          ? { ...aiRes.event.details.to_pos }
          : (() => {
              const actorAfter = nextNormalized.find((p) => p.piece_id === aiRes.event.actor_id);
              return actorAfter ? { ...actorAfter.position } : fromPos;
            })();
        const rawActionType = aiRes.event.details?.action_type as ActionType | undefined;
        const resolvedActionType: ActionType =
          rawActionType ||
          (aiRes.event.actor_id === 'COMPOUND'
            ? 'END_TURN'
            : aiRes.event.event_type === 'PIECE_CAPTURED'
            ? 'CAPTURE_REPLACE'
            : 'MOVE');

        const newRecord: MoveRecord = {
          move_number: movesRef.current.length + 1,
          side: actingSide,
          action: {
            action_id: `ai_${Date.now()}`,
            action_type: resolvedActionType,
            piece_id: aiRes.event.actor_id || '',
            from_pos: fromPos,
            to_pos: toPos,
            target_piece_id: aiRes.event.target_id || null,
            carry_cargo:
              typeof aiRes.event.details?.carry_cargo === 'boolean'
                ? aiRes.event.details.carry_cargo
                : resolvedActionType !== 'CAPTURE_STAND',
            notation: aiRes.event.notation,
            description: 'Nước đi của Random Agent',
          },
          notation: aiRes.event.notation,
          captured_piece_type:
            targetPiece && !nextNormalized.some((p) => p.is_alive && p.piece_id === targetPiece.piece_id)
              ? targetPiece.type
              : null,
          timestamp: Date.now(),
        };
        const nextMoves = [...movesRef.current, newRecord];
        setMoves(nextMoves);

        const nextCompound =
          aiRes.game_state.status === 'GAME_OVER'
            ? null
            : extractCompoundState(aiRes.game_state, nextNormalized);

        appendMatchSnapshot({
          pieces: nextNormalized,
          scores: nextScores,
          capturedPieces: nextCaptured,
          sideToMove: aiRes.game_state.side_to_move,
          lastMove: newRecord,
          activeCompound: nextCompound,
          movesCount: nextMoves.length,
        });

        if (aiRes.game_state.status === 'GAME_OVER') {
          setStatus('GAME_OVER');
          setGameResult(
            buildGameResultFromDTO(
              aiRes.game_state,
              nextMoves,
              matchSeconds,
              nextScores,
              actingSide
            )
          );
          setIsGameOverModalOpen(true);
          setSelectedPieceId(null);
          setActiveCompound(null);
          return;
        }

        setSelectedPieceId(null);
        setActiveCompound(nextCompound);
        setSideToMove(aiRes.game_state.side_to_move);
      } else {
        // Fallback ngoại tuyến (Mock engine) - Tác tử AI thông minh bao gồm cả tổ hợp cõng quân & END_TURN
        const smartAction = selectSmartAiAction(piecesRef.current, actingSide, activeCompound);
        if (smartAction) {
          if (smartAction.action_type === 'END_TURN') {
            await handleConfirmCompound();
          } else {
            await handleExecuteAction(smartAction, true);
          }
        } else if (!activeCompound) {
          const outcome = evaluateTurnHandoffOutcome(piecesRef.current, actingSide);
          if (outcome.isCheckmate || outcome.isStalemate) {
            const opponent: Side = actingSide === 'RED' ? 'BLUE' : 'RED';
            const finalScores = outcome.isCheckmate
              ? { ...scoresRef.current, [opponent]: scoresRef.current[opponent] + 50 }
              : { ...scoresRef.current };
            if (outcome.isCheckmate) setScores(finalScores);
            setStatus('GAME_OVER');
            setGameResult({
              winner: outcome.isCheckmate ? opponent : 'DRAW',
              reason: outcome.isCheckmate ? 'CHECKMATE' : 'STALEMATE',
              final_scores: finalScores,
              total_turns: Math.max(1, Math.ceil(movesRef.current.length / 2)),
              total_moves: movesRef.current.length,
              duration_seconds: matchSeconds,
              captured_commander_side: null,
            });
            setIsGameOverModalOpen(true);
          }
        }
      }
    } catch (err) {
      console.error('Lỗi khi thực thi nước đi AI:', err);
    } finally {
      setIsAiThinking(false);
    }
  };

  // Tự động kích hoạt nước đi của AI khi đến lượt phe Xanh trong chế độ HUMAN_VS_AI
  useEffect(() => {
    if (status !== 'IN_PROGRESS' || activeTab !== 'play' || isReviewingPast) return;
    if (gameMode === 'HUMAN_VS_AI' && sideToMove === 'BLUE' && !isAiThinking) {
      const timer = setTimeout(() => {
        triggerAiStep();
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [sideToMove, gameMode, status, activeTab, isAiThinking, activeCompound, isReviewingPast]);

  const handleExecuteAction = async (action: LegalAction, isAiAction: boolean = false) => {
    if (status === 'GAME_OVER' || isReviewingPast || (!isAiAction && isAiThinking)) return;

    const currentPieces = piecesRef.current;
    const currentSide = sideToMove;
    const actorBefore = currentPieces.find((p) => p.piece_id === action.piece_id);
    const effectiveCarryCargo =
      action.carry_cargo !== undefined ? action.carry_cargo : carryCargoWithMovement;
    const actionWithCarry: LegalAction = {
      ...action,
      carry_cargo: effectiveCarryCargo,
    };

    const originPos = activeCompound
      ? activeCompound.originPos
      : actorBefore
      ? { ...getRootCarrier(actorBefore, currentPieces).position }
      : { ...action.from_pos };

    // Xác định tổ hợp quân gốc nếu nước đi thuộc lượt tác chiến tổ hợp
    let memberIds: string[] = [];
    if (activeCompound) {
      memberIds = activeCompound.memberIds;
    } else if (actorBefore && action.action_type !== 'BOARD') {
      const actorWasCarried = actorBefore.carried_by_id != null;
      const oldRoot = getRootCarrier(actorBefore, currentPieces);
      const actorDescendants = getAllCarriedPieceIds(actorBefore.piece_id, currentPieces);
      if (actorWasCarried && oldRoot.type !== 'HEADQUARTERS') {
        memberIds = [oldRoot.piece_id, ...getAllCarriedPieceIds(oldRoot.piece_id, currentPieces)];
      } else if (
        !actorWasCarried &&
        actorBefore.type !== 'HEADQUARTERS' &&
        actorDescendants.length > 0 &&
        (action.action_type === 'CAPTURE_STAND' || effectiveCarryCargo === false)
      ) {
        memberIds = [actorBefore.piece_id, ...actorDescendants];
      }
    }

    const previouslyMoved = activeCompound ? activeCompound.movedPieceIds : [];
    const newMoved = previouslyMoved.includes(action.piece_id)
      ? [...previouslyMoved]
      : [...previouslyMoved, action.piece_id];
    const movedAway =
      action.action_type !== 'CAPTURE_STAND' &&
      (action.to_pos.x !== originPos.x || action.to_pos.y !== originPos.y);
    if (movedAway && effectiveCarryCargo !== false) {
      const travelingCargo = getAllCarriedPieceIds(action.piece_id, currentPieces);
      for (const tcId of travelingCargo) {
        if (!newMoved.includes(tcId)) {
          newMoved.push(tcId);
        }
      }
    }

    // Dự đoán nhanh lượt tổ hợp còn tiếp tục hay không để truyền cờ is_compound_action chính xác cho backend
    const previewOutcome = applyMockAction(actionWithCarry, currentPieces, false);
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
    const predictedStayInStack =
      !predictedCmdCaptured &&
      action.action_type !== 'BOARD' &&
      action.action_type !== 'END_TURN' &&
      memberIds.length > 1 &&
      previewRemainingAtOrigin.length > 0 &&
      newMoved.length < Math.min(3, memberIds.length);

    // 1. Khi kết nối FastAPI backend online: sử dụng trạng thái trả về từ backend làm chuẩn duy nhất
    if (backendOnline && gameSessionId) {
      try {
        const res = await apiClient.executeAction(gameSessionId, {
          action_type: action.action_type,
          piece_id: action.piece_id,
          to_pos: action.to_pos,
          target_piece_id: action.target_piece_id,
          state_version: stateVersionRef.current,
          is_compound_action: predictedStayInStack,
          carry_cargo: effectiveCarryCargo,
        });
        syncStateVersion(res.state_version);
        const gs = res.game_state;
        const nextNormalized =
          gs.pieces && gs.pieces.length > 0 ? normalizePieces(gs.pieces) : previewOutcome.nextPieces;
        const prevDeadIds = new Set(currentPieces.filter((p) => !p.is_alive).map((p) => p.piece_id));
        const newlyDead = nextNormalized.filter((p) => !p.is_alive && !prevDeadIds.has(p.piece_id));
        const nextCaptured =
          newlyDead.length > 0
            ? [...capturedPiecesRef.current, ...newlyDead]
            : capturedPiecesRef.current;
        if (newlyDead.length > 0) {
          setCapturedPieces(nextCaptured);
        }
        setPieces(nextNormalized);

        const nextScores = gs.scores
          ? { RED: gs.scores.RED, BLUE: gs.scores.BLUE }
          : { ...scoresRef.current };
        if (gs.scores) {
          setScores(nextScores);
        }

        const capPiece = action.target_piece_id
          ? currentPieces.find((p) => p.piece_id === action.target_piece_id) || null
          : null;
        const newRecord: MoveRecord = {
          move_number: movesRef.current.length + 1,
          side: currentSide,
          action: actionWithCarry,
          notation: res.event.notation || action.notation,
          captured_piece_type:
            capPiece && !nextNormalized.some((p) => p.is_alive && p.piece_id === capPiece.piece_id)
              ? capPiece.type
              : null,
          timestamp: Date.now(),
        };
        const nextMoves = [...movesRef.current, newRecord];
        setMoves(nextMoves);
        setCarryCargoWithMovement(true);
        setSelectedPieceId(null);

        const nextCompound =
          gs.status === 'GAME_OVER' ? null : extractCompoundState(gs, nextNormalized);

        appendMatchSnapshot({
          pieces: nextNormalized,
          scores: nextScores,
          capturedPieces: nextCaptured,
          sideToMove: gs.side_to_move,
          lastMove: newRecord,
          activeCompound: nextCompound,
          movesCount: nextMoves.length,
        });

        if (gs.status === 'GAME_OVER') {
          setStatus('GAME_OVER');
          setGameResult(
            buildGameResultFromDTO(gs, nextMoves, matchSeconds, nextScores, currentSide)
          );
          setIsGameOverModalOpen(true);
          setActiveCompound(null);
          return;
        }

        setActiveCompound(nextCompound);
        setSideToMove(gs.side_to_move);
        return;
      } catch (err) {
        console.warn('Backend action synchronization failed:', err);
        if (err instanceof ApiError) {
          try {
            const fresh = await apiClient.getGame(gameSessionId);
            syncStateVersion(fresh.state_version);
            const freshNormalized = normalizePieces(fresh.pieces);
            setPieces(freshNormalized);
            setScores({ RED: fresh.scores.RED, BLUE: fresh.scores.BLUE });
            setActiveCompound(extractCompoundState(fresh, freshNormalized));
            setSideToMove(fresh.side_to_move);
            if (fresh.status === 'GAME_OVER') {
              setStatus('GAME_OVER');
              setGameResult(
                buildGameResultFromDTO(
                  fresh,
                  movesRef.current,
                  matchSeconds,
                  { RED: fresh.scores.RED, BLUE: fresh.scores.BLUE },
                  currentSide
                )
              );
              setIsGameOverModalOpen(true);
            }
            setCarryCargoWithMovement(true);
            setSelectedPieceId(null);
            return;
          } catch {
            // Fall through if unable to reach server
          }
        } else {
          setBackendOnline(false);
        }
      }
    }

    // 2. Luồng ngoại tuyến (Mock game service)
    const { nextPieces, event, capturedPiece } = applyMockAction(
      actionWithCarry,
      currentPieces,
      !predictedStayInStack
    );
    setPieces(nextPieces);

    const newlyDead = nextPieces.filter(
      (np) => !np.is_alive && currentPieces.find((p) => p.piece_id === np.piece_id && p.is_alive)
    );
    const nextCaptured =
      newlyDead.length > 0
        ? [...capturedPiecesRef.current, ...newlyDead]
        : capturedPiece
        ? [...capturedPiecesRef.current, capturedPiece]
        : capturedPiecesRef.current;
    if (newlyDead.length > 0 || capturedPiece) {
      setCapturedPieces(nextCaptured);
    }

    const finalRedScore = scoresRef.current.RED + event.score_delta.RED;
    const finalBlueScore = scoresRef.current.BLUE + event.score_delta.BLUE;
    const finalScores = { RED: finalRedScore, BLUE: finalBlueScore };
    if (event.score_delta.RED > 0 || event.score_delta.BLUE > 0) {
      setScores(finalScores);
    }

    const newRecord: MoveRecord = {
      move_number: movesRef.current.length + 1,
      side: currentSide,
      action: actionWithCarry,
      notation: event.notation || action.notation,
      captured_piece_type: capturedPiece ? capturedPiece.type : null,
      timestamp: Date.now(),
    };
    const nextMoves = [...movesRef.current, newRecord];
    setMoves(nextMoves);
    setCarryCargoWithMovement(true);

    const isGameEnding =
      Boolean(capturedPiece && capturedPiece.type === 'COMMANDER') ||
      Boolean(event.details?.is_checkmate || event.details?.is_stalemate);

    const nextCompoundState: ActiveCompoundState | null =
      !isGameEnding && predictedStayInStack
        ? {
            originPos,
            memberIds,
            movedPieceIds: newMoved,
            actionCount: (activeCompound?.actionCount || 0) + 1,
          }
        : null;

    const nextSide: Side = isGameEnding
      ? currentSide
      : predictedStayInStack
      ? currentSide
      : currentSide === 'RED'
      ? 'BLUE'
      : 'RED';

    appendMatchSnapshot({
      pieces: nextPieces,
      scores: finalScores,
      capturedPieces: nextCaptured,
      sideToMove: nextSide,
      lastMove: newRecord,
      activeCompound: nextCompoundState,
      movesCount: nextMoves.length,
    });

    // KẾT THÚC TRẬN ĐẤU: Bắt được Tư lệnh đối phương (phòng thủ)
    if (capturedPiece && capturedPiece.type === 'COMMANDER') {
      setStatus('GAME_OVER');
      setGameResult({
        winner: currentSide,
        reason: 'COMMANDER_CAPTURED',
        final_scores: finalScores,
        total_turns: Math.ceil(nextMoves.length / 2),
        total_moves: nextMoves.length,
        duration_seconds: matchSeconds,
        captured_commander_side: capturedPiece.side,
      });
      setIsGameOverModalOpen(true);
      setSelectedPieceId(null);
      setActiveCompound(null);
      return;
    }

    // KẾT THÚC TRẬN ĐẤU: Chiếu hết (CHECKMATE) hoặc Hòa cờ bí (STALEMATE - DEC-020)
    if (event.details?.is_checkmate || event.details?.is_stalemate) {
      const isStale = Boolean(event.details?.is_stalemate);
      setStatus('GAME_OVER');
      setGameResult({
        winner: isStale ? 'DRAW' : currentSide,
        reason: isStale ? 'STALEMATE' : 'CHECKMATE',
        final_scores: finalScores,
        total_turns: Math.ceil(nextMoves.length / 2),
        total_moves: nextMoves.length,
        duration_seconds: matchSeconds,
        captured_commander_side: null,
      });
      setIsGameOverModalOpen(true);
      setSelectedPieceId(null);
      setActiveCompound(null);
      return;
    }

    if (predictedStayInStack && nextCompoundState) {
      setActiveCompound(nextCompoundState);
      setSelectedPieceId(null);
    } else {
      setActiveCompound(null);
      setSelectedPieceId(null);
      setSideToMove(nextSide);
    }
  };

  const handleRequestNewGame = () => {
    if (moves.length === 0 || status === 'GAME_OVER') {
      handleResetBoard();
    } else {
      setConfirmModalType('NEW_GAME');
    }
  };

  const handleResetBoard = async (newMode?: GameMode) => {
    const modeToUse = newMode || gameMode;
    if (newMode) setGameMode(newMode);
    const freshInitial = getInitialPieces();
    const initSnaps = [buildInitialSnapshot(freshInitial)];
    matchSnapshotsRef.current = initSnaps;
    setMatchSnapshots(initSnaps);
    setReviewIndex(null);
    setPieces(freshInitial);
    setSelectedPieceId(null);
    setActiveCompound(null);
    setCarryCargoWithMovement(true);
    setSideToMove('RED');
    setScores({ RED: 0, BLUE: 0 });
    setMoves([]);
    setCapturedPieces([]);
    setStatus('IN_PROGRESS');
    setGameResult(null);
    setIsGameOverModalOpen(false);
    setConfirmModalType(null);
    setMatchSeconds(0);
    syncStateVersion(1);
    setIsAiThinking(false);

    if (backendOnline) {
      try {
        const session = await apiClient.createGame({
          mode: modeToUse,
          player_side: 'RED',
          blue_agent_id: modeToUse === 'HUMAN_VS_AI' ? 'RandomAgent' : null,
        });
        setGameSessionId(session.game_id);
        syncStateVersion(session.state_version);
        if (session.pieces && session.pieces.length > 0) {
          const initNorm = normalizePieces(session.pieces);
          const backendSnaps = [buildInitialSnapshot(initNorm)];
          matchSnapshotsRef.current = backendSnaps;
          setMatchSnapshots(backendSnaps);
          setReviewIndex(null);
          setPieces(initNorm);
        }
      } catch (err) {
        console.warn('Backend new game creation failed:', err);
      }
    }
  };

  const handleRequestResign = () => {
    if (status === 'GAME_OVER' || isReviewingPast) return;
    setConfirmModalType('RESIGN');
  };

  const handleConfirmResign = async () => {
    const winner: Side = sideToMove === 'RED' ? 'BLUE' : 'RED';
    if (backendOnline && gameSessionId) {
      try {
        await apiClient.resignGame(gameSessionId, sideToMove);
      } catch (err) {
        console.warn('Backend resign failed:', err);
      }
    }

    const result: GameResult = {
      winner,
      reason: 'RESIGNATION',
      final_scores: scores,
      total_turns: Math.max(1, Math.ceil(moves.length / 2)),
      total_moves: moves.length,
      duration_seconds: matchSeconds,
      captured_commander_side: null,
    };
    setReviewIndex(null);
    setStatus('GAME_OVER');
    setGameResult(result);
    setConfirmModalType(null);
    setIsGameOverModalOpen(true);
  };

  const handleRequestDraw = () => {
    if (status === 'GAME_OVER' || isReviewingPast) return;
    setConfirmModalType('DRAW');
  };

  const handleConfirmDraw = async () => {
    if (backendOnline && gameSessionId) {
      try {
        await apiClient.drawGame(gameSessionId, sideToMove);
      } catch (err) {
        console.warn('Backend draw failed:', err);
      }
    }

    const result: GameResult = {
      winner: 'DRAW',
      reason: 'MUTUAL_DRAW',
      final_scores: scores,
      total_turns: Math.max(1, Math.ceil(moves.length / 2)),
      total_moves: moves.length,
      duration_seconds: matchSeconds,
      captured_commander_side: null,
    };
    setReviewIndex(null);
    setStatus('GAME_OVER');
    setGameResult(result);
    setConfirmModalType(null);
    setIsGameOverModalOpen(true);
  };

  const handleNavigate = (tab: string, mode?: GameMode) => {
    if (mode) {
      handleResetBoard(mode);
    }
    setActiveTab(tab);
  };

  return (
    <>
      <Header
        currentLang={lang}
        onLanguageChange={setLang}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <main className={styles.main}>
        {/* TAB 1: HOME PAGE (CR-003) */}
        {activeTab === 'home' && (
          <Home lang={lang} onNavigate={handleNavigate} />
        )}

        {/* TAB 2: PLAY TACTICAL BOARD (CR-001, CR-004) */}
        {activeTab === 'play' && (
          <div className={styles.gameLayout}>
            {/* Left Operational Info Panel (Optimized to free vertical space for board) */}
            <aside className={styles.leftPanel}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: '100%', justifyContent: 'flex-start' }}
                onClick={() => setActiveTab('home')}
                title={t.game.backToHome}
              >
                ← {t.game.backToHome}
              </button>

              {/* Mode Info Card */}
              <div className={`tactical-panel ${styles.modePanel}`}>
                <div className={styles.modePanelHeader}>
                  <span className={styles.modePanelLabel}>
                    {lang === 'vi' ? 'Chế độ' : 'Mode'}
                  </span>
                  <span className="badge">Total Force</span>
                </div>
                <div className={styles.modePanelTitle}>
                  {lang === 'vi' ? 'Tổng lực' : 'Total Force'}
                </div>

                {/* Mode Selector Pill Buttons */}
                <div className={styles.modeSelectorGroup}>
                  <button
                    type="button"
                    className={`${styles.modePill} ${gameMode === 'HUMAN_VS_AI' ? styles.modePillActive : ''}`}
                    onClick={() => {
                      if (gameMode !== 'HUMAN_VS_AI') handleResetBoard('HUMAN_VS_AI');
                    }}
                    disabled={isAiThinking}
                    title={t.game.modeHumanVsAi}
                  >
                    🤖 {t.game.modeHumanVsAi}
                  </button>
                  <button
                    type="button"
                    className={`${styles.modePill} ${gameMode === 'HUMAN_VS_HUMAN' ? styles.modePillActive : ''}`}
                    onClick={() => {
                      if (gameMode !== 'HUMAN_VS_HUMAN') handleResetBoard('HUMAN_VS_HUMAN');
                    }}
                    disabled={isAiThinking}
                    title={t.game.modeHumanVsHuman}
                  >
                    ⚔️ {t.game.modeHumanVsHuman}
                  </button>
                </div>

                <div className={styles.modePanelSpecs}>
                  <div className={styles.modePanelRow}>
                    <span>{lang === 'vi' ? 'Quy mô' : 'Grid'}</span>
                    <strong>11 × 12</strong>
                  </div>
                  <div className={styles.modePanelRow}>
                    <span>{lang === 'vi' ? 'Giao điểm' : 'Points'}</span>
                    <strong>132 pts</strong>
                  </div>
                  <div className={styles.modePanelRow}>
                    <span>{lang === 'vi' ? 'Quân lực' : 'Pieces'}</span>
                    <strong>38 ({lang === 'vi' ? '19/phe' : '19/side'})</strong>
                  </div>
                </div>
              </div>

              {/* Action Log / Move History Panel */}
              <MoveHistory
                moves={moves}
                lang={lang}
                activeSnapshotIndex={effectiveSnapshotIndex}
                totalSnapshots={matchSnapshots.length}
                onNavigateSnapshot={handleNavigateSnapshot}
              />

              {/* Rules Guide Quick Link */}
              <button
                type="button"
                className="btn btn-outline-gold"
                style={{ width: '100%', fontSize: '0.8rem', padding: '0.45rem 0.65rem' }}
                onClick={() => setActiveTab('rules')}
              >
                📖 {lang === 'vi' ? 'Cẩm nang luật' : 'Rules Guide'}
              </button>
            </aside>

            {/* Main Tactical Board Area - Full Vertical Space without top bar */}
            <section className={styles.boardSection}>
              {isReviewingPast && (
                <div className={styles.reviewBanner}>
                  <span>⏪ {t.game.reviewingHistoryBanner}</span>
                  <button
                    type="button"
                    className={styles.reopenBtn}
                    onClick={() => handleNavigateSnapshot(null)}
                  >
                    {t.game.returnToLiveBtn} ⏭
                  </button>
                </div>
              )}

              <Board
                pieces={displayedPieces}
                selectedPieceId={selectedPieceId}
                onSelectPiece={handleSelectPiece}
                legalActions={legalActions}
                onExecuteAction={handleExecuteAction}
                lastMove={displayedLastMove}
                activeCompound={displayedActiveCompound}
                flipped={boardFlipped}
                readOnly={isReviewingPast}
                lang={lang}
              />

              <CompoundControlBar
                pieces={displayedPieces}
                selectedPieceId={selectedPieceId}
                activeCompound={displayedActiveCompound}
                carryCargo={carryCargoWithMovement}
                onToggleCarryCargo={setCarryCargoWithMovement}
                onSelectPiece={handleSelectPiece}
                onConfirmCompound={handleConfirmCompound}
                lang={lang}
                readOnly={isReviewingPast || status === 'GAME_OVER' || isAiThinking}
              />

              <div className={`tactical-panel ${styles.reviewControlBar}`}>
                <button
                  type="button"
                  className={styles.reviewNavBtn}
                  disabled={effectiveSnapshotIndex <= 0}
                  onClick={() => handleNavigateSnapshot(0)}
                  title="Home"
                >
                  ⏮ {t.game.navFirst}
                </button>
                <button
                  type="button"
                  className={styles.reviewNavBtn}
                  disabled={effectiveSnapshotIndex <= 0}
                  onClick={() => handleNavigateSnapshot(effectiveSnapshotIndex - 1)}
                  title="ArrowLeft"
                >
                  ◀ {t.game.navPrev}
                </button>
                <span className={styles.reviewStepBadge}>
                  {t.game.stepLabel} {effectiveSnapshotIndex} / {maxSnapshotIndex}
                </span>
                <button
                  type="button"
                  className={styles.reviewNavBtn}
                  disabled={effectiveSnapshotIndex >= maxSnapshotIndex}
                  onClick={() => handleNavigateSnapshot(effectiveSnapshotIndex + 1)}
                  title="ArrowRight"
                >
                  {t.game.navNext} ▶
                </button>
                <button
                  type="button"
                  className={styles.reviewNavBtn}
                  disabled={effectiveSnapshotIndex >= maxSnapshotIndex}
                  onClick={() => handleNavigateSnapshot(null)}
                  title="End"
                >
                  {t.game.navLast} ⏭
                </button>
                <button
                  type="button"
                  className={`${styles.reviewNavBtn} ${
                    boardFlipped ? styles.reviewFlipBtnActive : ''
                  }`}
                  onClick={() => setBoardFlipped((prev) => !prev)}
                  title={t.game.flipBoard}
                >
                  🔄 {t.game.flipBoard}
                </button>
              </div>
            </section>

            {/* Right Sidebar Control & Info Panel */}
            <aside className={styles.sidebar}>
              {/* Match Status Card */}
              <div className={`tactical-panel ${styles.statusCard}`}>
                <div className={styles.statusHeader}>
                  <span className={styles.statusTitle}>{t.game.status}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <div
                      className={backendOnline ? styles.backendBadgeOnline : styles.backendBadgeOffline}
                      title={backendOnline ? `${t.game.backendOnline} (v${stateVersion})` : t.game.backendOffline}
                    >
                      <span>{backendOnline ? '🟢' : '🟡'}</span>
                      <span>{backendOnline ? 'FastAPI' : 'Local'}</span>
                    </div>
                    <div className={styles.timerDisplay} title={t.game.timer}>
                      <span>⏱️</span>
                      <span>{formattedTime}</span>
                    </div>
                    <span
                      className="badge"
                      style={
                        status === 'GAME_OVER'
                          ? { color: 'var(--gold-primary)', borderColor: 'var(--gold-primary)' }
                          : {}
                      }
                    >
                      {status === 'GAME_OVER' ? t.game.gameOver : t.game.activeSession}
                    </span>
                  </div>
                </div>

                {/* Game Over Banner with Reopen modal button */}
                {status === 'GAME_OVER' && (
                  <div className={styles.gameOverBanner}>
                    <span className={styles.gameOverText}>
                      {gameResult?.winner === 'RED'
                        ? `★ ${t.game.redSide} thắng`
                        : gameResult?.winner === 'BLUE'
                        ? `★ ${t.game.blueSide} thắng`
                        : `🤝 ${t.game.drawMatch}`}
                    </span>
                    <button
                      type="button"
                      className={styles.reopenBtn}
                      onClick={() => setIsGameOverModalOpen(true)}
                    >
                      {t.game.btnReopenModal}
                    </button>
                  </div>
                )}

                {/* Turn Indicator - Neutral dark background with solid faction pip */}
                <div className={styles.turnIndicator}>
                  <div
                    className={`${styles.turnDot} ${
                      displayedSideToMove === 'BLUE' ? styles.turnDotBlue : ''
                    }`}
                  />
                  <span className={styles.turnText}>
                    {t.game.turn}:{' '}
                    <strong
                      className={
                        displayedSideToMove === 'RED'
                          ? styles.turnSideRed
                          : styles.turnSideBlue
                      }
                    >
                      {displayedSideToMove === 'RED'
                        ? t.game.redSide
                        : gameMode === 'HUMAN_VS_AI'
                        ? t.game.aiBotName
                        : t.game.blueSide}
                    </strong>
                  </span>
                </div>

                {/* AI Thinking Indicator Banner */}
                {isAiThinking && (
                  <div className={styles.aiThinkingBanner}>
                    <span className={styles.aiThinkingSpinner}>⚙️</span>
                    <span>{t.game.aiThinking}</span>
                  </div>
                )}

                {/* Score Overview - Clean typography, no nested tinted pills */}
                <div className={styles.scoreRow}>
                  <div className={styles.scoreTeam}>
                    <span className={styles.teamLabelRed}>{t.game.redSide}</span>
                    <span className={styles.scoreValue}>
                      {displayedScores.RED}
                    </span>
                  </div>
                  <div className={styles.scoreDivider}>vs</div>
                  <div className={styles.scoreTeam}>
                    <span className={styles.teamLabelBlue}>{t.game.blueSide}</span>
                    <span className={styles.scoreValue}>
                      {displayedScores.BLUE}
                    </span>
                  </div>
                </div>

                {/* Primary Controls */}
                <div className={styles.controls}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                    onClick={handleRequestNewGame}
                    disabled={isAiThinking}
                  >
                    🔄 {t.game.newGame}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={triggerAiStep}
                    disabled={status === 'GAME_OVER' || isAiThinking || isReviewingPast}
                    title={t.game.aiMoveBtn}
                  >
                    {t.game.aiMoveBtn}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setActiveCompound(null);
                      setSelectedPieceId(null);
                      setSideToMove(sideToMove === 'RED' ? 'BLUE' : 'RED');
                    }}
                    disabled={status === 'GAME_OVER' || isAiThinking || isReviewingPast}
                    title="Chuyển lượt thử nghiệm"
                  >
                    {t.game.swapTurn}
                  </button>
                </div>

                {/* Tactical Action Controls (Resign & Draw) */}
                <div className={styles.controlsSecondary}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleRequestResign}
                    disabled={status === 'GAME_OVER' || isReviewingPast}
                    title={t.game.resign}
                  >
                    🏳️ {t.game.resign}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleRequestDraw}
                    disabled={status === 'GAME_OVER' || isReviewingPast}
                    title={t.game.drawOffer}
                  >
                    🤝 {t.game.drawOffer}
                  </button>
                </div>
              </div>

              {/* Tactical Piece Detail Panel */}
              <PieceDetail
                piece={selectedPiece}
                allPieces={displayedPieces}
                onSelectPiece={handleSelectPiece}
                lang={lang}
                movedPieceIds={displayedActiveCompound?.movedPieceIds}
                readOnly={isReviewingPast || status === 'GAME_OVER' || isAiThinking}
              />

              {/* Captured Pieces Tracker */}
              <CapturedPieces capturedPieces={displayedCapturedPieces} lang={lang} />
            </aside>
          </div>
        )}

        {/* TAB 3: RULES & TACTICS GUIDE */}
        {activeTab === 'rules' && (
          <div className={styles.rulesContainer}>
            <div className={styles.rulesHeader}>
              <div>
                <h2 className={styles.rulesTitle}>
                  {lang === 'vi' ? 'Cẩm Nang Luật Chơi Cờ Tư Lệnh' : 'Commander Chess Rules & Tactics'}
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '0.25rem' }}>
                  {lang === 'vi'
                    ? 'Chuẩn hóa theo đặc tả luật chính thức docs/GAME_RULES.md — Chiến tranh Tổng lực'
                    : 'Standardized according to official specs docs/GAME_RULES.md — Total Force Warfare'}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setActiveTab('play')}
              >
                {t.home.btnPlayNow} →
              </button>
            </div>

            <div className={styles.rulesGrid}>
              {/* Card 1: Địa hình & Bàn cờ */}
              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>◈</span>
                  {lang === 'vi' ? '1. Địa hình & Bàn cờ Chiến thuật' : '1. Strategic Terrain & Board'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Bàn cờ gồm 11 đường dọc (X: 0..10) và 12 đường ngang (Y: 0..11), tổng cộng 132 giao điểm. Gốc [0 ; 0] ở góc dưới bên trái.'
                      : 'Board features 11 vertical (X: 0..10) and 12 horizontal lines (Y: 0..11), 132 intersections. Origin [0 ; 0] at bottom-left.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Biển sâu (cột X: 0, 1): Chỉ Hải quân và Máy bay hoạt động. Quân bộ khi tấn công tàu trên biển thì bắn tại chỗ (_@_), tuyệt đối không xuống biển.'
                      : 'Deep sea (columns X: 0, 1): Reserved for Navy and Aircraft. Land units attacking ships at sea attack in-place (_@_) without entering water.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Sông chia đôi hai chiến tuyến (Y: 5..6). Chỉ Bộ binh bơi qua được, hoặc qua 2 Ngầm đá [5;5]-[6;5] và [5;7]-[6;7], hoặc nhờ Công binh chở qua.'
                      : 'River bisects frontlines (Y: 5..6). Only Infantry can swim across, or pass through 2 underwater stone bridges, or transported by Engineers.'}
                  </li>
                </ul>
              </div>

              {/* Card 2: Quy tắc Tối thượng — An toàn Tư lệnh, Chiếu hết & Hòa cờ bí */}
              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle} style={{ color: 'var(--crimson-primary)' }}>
                  <span>⚠️</span>
                  {lang === 'vi' ? '2. An toàn Tư lệnh, Chiếu hết & Hòa cờ bí' : '2. Commander Safety, Checkmate & Stalemate'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Mọi nước đi khiến Tư lệnh bị uy hiếp (đối mặt trực tiếp không quân cản, tự bước vào ô bị ăn, hoặc để quân đang ngồi trên phương tiện địch triển khai ăn được) đều bị cấm tuyệt đối.'
                      : 'Every move leaving your Commander threatened (direct facing, moving into attack, pinned blocker leaving, or enemy carried deployment attack) is strictly illegal.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Che chở & Cấm đối mặt khi cõng (DEC-021): Chỉ Sở chỉ huy thường che chở Tư lệnh đã trú bên trong khỏi chiếu & đối mặt. Tư lệnh KHÔNG được lên phương tiện nằm trên đường nhìn Tư lệnh địch, và phương tiện cơ động (Xe tăng, Máy bay, Tàu chiến) đang cõng Tư lệnh KHÔNG được dừng lại trên đường nhìn thẳng thông thoáng đối mặt Tư lệnh địch.'
                      : 'Shelter & Transport Facing Ban (DEC-021): Only regular HQ shelters an already-sheltered Commander from check & facing. Commander cannot board a carrier standing on enemy Commander line of sight, and mobile carriers carrying Commander (Tank, Aircraft, Navy) cannot stop on enemy Commander unobstructed facing line.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Chiếu hết để thắng (+50đ): Bên đang bị chiếu mà còn 0 nước đi hợp lệ sẽ thua ngay lập tức.'
                      : 'Checkmate to Win (+50 pts): When in check with 0 legal moves, that side loses immediately.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Hòa cờ bí (Stalemate): Khi đến lượt một bên có 0 nước đi hợp lệ nhưng Tư lệnh KHÔNG bị chiếu → ván đấu xử HÒA ngay lập tức.'
                      : 'Stalemate Draw: If the active side has 0 legal moves while NOT in check, the match immediately ends in a DRAW.'}
                  </li>
                </ul>
              </div>

              {/* Card 3: Vành đai lửa Phòng không */}
              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>🔥</span>
                  {lang === 'vi' ? '3. Vành đai lửa Phòng không' : '3. Air Defense Umbrellas'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Cao xạ (F): Vùng cấm bay 1 đoạn ngang/dọc (4 ô kề). Tên lửa (L): Vùng cấm bay 1–2 đoạn thẳng + 1 đoạn chéo. Hải quân (H): 1 đoạn thẳng.'
                      : 'Anti-Air (F): 1 orthogonal step. Missile (L): 1–2 orthogonal + 1 diagonal steps. Navy (H): 1 orthogonal step.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Bắn hạ khi bay qua: Máy bay thường bay qua bất kỳ ô nào thuộc vành đai lửa của địch sẽ bị bắn hạ ngay lập tức.'
                      : 'Shot down on transit: Standard Aircraft flying through any enemy AA intersection is shot down immediately.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Quy tắc 1 đổi 1: Máy bay tấn công mục tiêu trong vùng phòng không sẽ tiêu diệt được mục tiêu nhưng bản thân máy bay cũng bị bắn rơi cùng lúc.'
                      : 'Mutual destruction (1-for-1): Aircraft attacking a target inside AA envelope destroys the target but is shot down simultaneously.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Radar trên bàn cờ: Khi click chọn quân Máy bay trên bàn cờ, toàn bộ vành đai lửa đối phương (🔥) sẽ hiển thị sáng rõ.'
                      : 'Tactical board radar: Clicking an Aircraft highlights the entire enemy air defense envelope (🔥) on the board.'}
                  </li>
                </ul>
              </div>

              {/* Card 4: Hành quân thần tốc & Cõng quân */}
              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>🚛</span>
                  {lang === 'vi' ? '4. Hành quân Thần tốc & Cõng quân' : '4. Mechanized Transport & Stacking'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Xe tăng (T): Chở tối đa 2 quân bộ (Bộ binh, Dân quân, Tư lệnh). Tàu chiến (H): Chở 1 máy bay HOẶC 1 xe tăng HOẶC 2 quân bộ.'
                      : 'Tank (T): Carries up to 2 infantry units (Infantry, Militia, Commander). Navy (H): Carries 1 aircraft OR 1 tank OR 2 infantry units.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Công binh (C): Đứng ở bờ sông (Y=5 bên Đỏ, Y=6 bên Xanh) để chở 1 vũ khí nặng (Pháo, Cao xạ, Tên lửa) vượt sông sâu.'
                      : 'Engineer (C): Stationed at riverbank (Y=5 for Red, Y=6 for Blue) to carry 1 heavy weapon (Artillery, Anti-Air, Missile) across deep river.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Lên phương tiện (^): Tốn 1 lượt tác chiến. Triển khai tách quân bằng nước đi hoặc nước ăn hợp lệ của chính quân đó.'
                      : 'Boarding (^): Costs 1 turn. Deployment from transport executes as a valid move or attack of that carried piece.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Phương tiện bị tiêu diệt: Toàn bộ quân đang ngồi bên trong bị chết theo và cộng dồn điểm cho đối phương.'
                      : 'Transport destruction: All passengers inside are destroyed along with the transport, granting cumulative score.'}
                  </li>
                </ul>
              </div>

              {/* Card 5: Phong Anh hùng & Huy hiệu Sao Vàng */}
              <div className={styles.rulesCard} style={{ gridColumn: 'span 2' }}>
                <h3 className={styles.rulesCardTitle}>
                  <span style={{ color: 'var(--gold-primary)' }}>★</span>
                  {lang === 'vi' ? '5. Phong Anh hùng & Huy hiệu Sao Vàng Góc Quân' : '5. Hero Promotion & Golden Star Badge'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Điều kiện phong: Phong Anh hùng khi quân đi nước chiếu Tư lệnh địch; khi phe chỉ còn đúng 1 quân chiến đấu (không tính Tư lệnh & Sở chỉ huy); hoặc khi chỉ còn Tư lệnh + duy nhất 1 Sở chỉ huy.'
                      : 'Promotion conditions: Promoted on checking the enemy Commander; when only 1 combat piece remains (excluding Commander & HQ); or when only Commander + 1 solitary HQ remain.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Phong trễ Sở chỉ huy duy nhất: Nếu còn 2 Sở chỉ huy thì CHƯA phong. Khi còn đúng 1 Sở chỉ huy + Tư lệnh đang núp bên trong, Sở chỉ huy CHƯA phong ngay mà buộc Tư lệnh di chuyển rời Sở chỉ huy trước (nước đi duy nhất), ngay khi Tư lệnh bước ra thì Sở chỉ huy lập tức phong Anh hùng!'
                      : 'Delayed Solitary-HQ Promotion: 2 HQs are never promoted. If only 1 HQ + Commander sheltered inside remain, HQ stays unpromoted until Commander exits (its only legal move), promoting the sole HQ to Hero the instant Commander steps out.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Quyền năng vượt trội: Tăng 1 đoạn tầm đi và ăn; được bổ sung các đường chéo; Máy bay Anh hùng miễn nhiễm phòng không; mọi quân (kể cả Bộ binh, Dân quân, Tăng, Pháo, Công binh, Tư lệnh...) đều có thể tấn công Máy bay!'
                      : 'Heroic traits: +1 step move/capture range; gains diagonals; Hero Aircraft ignores AA; and EVERY piece type can attack Aircraft!'}
                  </li>
                </ul>
              </div>
            </div>

            {/* Tactical Reference Table: 11 Piece Classes */}
            <h3 className={styles.rulesSectionTitle}>
              <span>⚔</span>
              {lang === 'vi' ? 'Bảng Tra Cứu Tác Chiến 11 Chủng Loại Quân Cờ' : 'Tactical Reference Matrix — 11 Piece Classes'}
            </h3>

            <div className={styles.rulesTableWrapper}>
              <table className={styles.rulesTable}>
                <thead>
                  <tr>
                    <th>{lang === 'vi' ? 'Quân cờ & Ký hiệu' : 'Piece & Notation'}</th>
                    <th>{lang === 'vi' ? 'Tầm di chuyển' : 'Movement Range'}</th>
                    <th>{lang === 'vi' ? 'Tầm ăn quân' : 'Capture Range'}</th>
                    <th>{lang === 'vi' ? 'Mục tiêu tấn công' : 'Valid Targets'}</th>
                    <th>{lang === 'vi' ? 'Tương tác Sông & Biển' : 'River & Sea Rules'}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>⋆</span>
                      {lang === 'vi' ? 'Tư lệnh (⋆)' : 'Commander (⋆)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc không hạn chế (bị cản)' : 'Orthogonal unlimited (blocked)'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (thế chỗ @ hoặc _@_)' : 'Orthogonal 1 step (@ or _@_)'}</td>
                    <td>{lang === 'vi' ? 'Mọi quân địch (kể cả Máy bay) và tàu ven bờ (cấm tự sát).' : 'All enemy pieces (incl. Aircraft) & coastal ships (no self-check).'}</td>
                    <td>{lang === 'vi' ? 'Tự qua sông sâu được. Cấm lên phương tiện hay dừng xe/tàu/máy bay cõng trên đường nhìn Tư lệnh địch.' : 'Crosses deep river. Cannot board or halt inside mobile carrier on enemy Commander LOS.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--text-secondary)' }}>S</span>
                      {lang === 'vi' ? 'Sở chỉ huy (S)' : 'Headquarters (S)'}
                    </td>
                    <td>{lang === 'vi' ? 'Cố định (Anh hùng: 8 hướng 1–2 đoạn)' : 'Stationary (Hero: 8-dir 1–2 steps)'}</td>
                    <td>{lang === 'vi' ? 'Thường: không ăn. Anh hùng: 8 hướng 1–2 đoạn' : 'Regular: none. Hero: 8-dir 1–2 steps'}</td>
                    <td>{lang === 'vi' ? 'Thường che chắn Tư lệnh. Anh hùng chiến đấu như Bộ binh Anh hùng.' : 'Regular shelters Commander. Hero fights like Hero Infantry.'}</td>
                    <td>{lang === 'vi' ? 'Chỉ Sở chỉ huy duy nhất mới phong Anh hùng (phong trễ nếu Tư lệnh đang núp).' : 'Only sole HQ promotes to Hero (delayed while Commander is inside).'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--crimson-primary)' }}>B</span>
                      {lang === 'vi' ? 'Bộ binh (B)' : 'Infantry (B)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn' : 'Orthogonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (thế chỗ @)' : 'Orthogonal 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Mọi quân mặt đất, Máy bay và tàu ven bờ.' : 'Ground units, Aircraft, and coastal ships.'}</td>
                    <td>{lang === 'vi' ? 'Bơi qua sông sâu được. Lên xe tăng, tàu chiến.' : 'Swims across deep river. Boards tanks, warships.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--crimson-primary)' }}>D</span>
                      {lang === 'vi' ? 'Dân quân (D)' : 'Militia (D)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng (ngang/dọc/chéo) 1 đoạn' : 'All 8 directions, 1 step'}</td>
                    <td>{lang === 'vi' ? '8 hướng 1 đoạn (thế chỗ @)' : 'All 8 directions, 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Mọi quân mặt đất, Máy bay và tàu ven bờ.' : 'Ground units, Aircraft, and coastal ships.'}</td>
                    <td>{lang === 'vi' ? 'Qua sông sâu được. Không ra biển sâu.' : 'Crosses deep river. Cannot enter deep sea.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>T</span>
                      {lang === 'vi' ? 'Xe tăng (T)' : 'Tank (T)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2 đoạn (bị cản ở đoạn 1)' : 'Orthogonal 1–2 steps (blocked)'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2 đoạn (thế chỗ @)' : 'Orthogonal 1–2 steps (@)'}</td>
                    <td>{lang === 'vi' ? 'Quân đất, Máy bay. Bắn tàu biển tại chỗ (_@_).' : 'Ground units, Aircraft. Fires at sea ships in-place (_@_).'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu (trừ ngầm đá). Cõng tối đa 2 bộ binh.' : 'No deep river alone (except fords). Transports up to 2 infantry.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--text-secondary)' }}>C</span>
                      {lang === 'vi' ? 'Công binh (C)' : 'Engineer (C)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn' : 'Orthogonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (thế chỗ @)' : 'Orthogonal 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Mọi quân mặt đất, Máy bay và tàu ven bờ.' : 'Ground units, Aircraft, and coastal ships.'}</td>
                    <td>{lang === 'vi' ? 'Bơi qua sông sâu. Đứng ở bờ cõng vũ khí nặng qua sông.' : 'Swims river. Bridges/carries heavy weapons across.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>A</span>
                      {lang === 'vi' ? 'Pháo binh (A)' : 'Artillery (A)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng 1–3 đoạn (bị cản)' : 'All 8 directions 1–3 steps (blocked)'}</td>
                    <td>{lang === 'vi' ? '8 hướng 1–3 đoạn (BẮN XUYÊN MỌI QUÂN CẢN)' : 'All 8 directions (PIERCES ALL OBSTACLES)'}</td>
                    <td>{lang === 'vi' ? 'Mọi quân đất, Máy bay. Bắn tàu biển tại chỗ (_@_).' : 'Ground units, Aircraft. Fires at ships in-place (_@_).'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu (qua ngầm hoặc Công binh chở).' : 'No deep river alone (needs Engineer or stone ford).'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--team-blue)' }}>F</span>
                      {lang === 'vi' ? 'Cao xạ (F)' : 'Anti-Air (F)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn' : 'Orthogonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (bắn máy bay & bộ binh)' : 'Orthogonal 1 step (hits aircraft & infantry)'}</td>
                    <td>{lang === 'vi' ? 'Bắn hạ máy bay và mọi quân bộ. Tạo vành đai lửa 1 đoạn.' : 'Shoots aircraft and land units. Projects 1-step AA.'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu (qua ngầm hoặc Công binh chở).' : 'No deep river alone (except fords or Engineer).'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--team-blue)' }}>L</span>
                      {lang === 'vi' ? 'Tên lửa (L)' : 'Missile (L)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2, chéo 1 đoạn (KHÔNG xuyên cản)' : 'Orthogonal 1–2, diag 1 (blocked on move)'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2, chéo 1 đoạn (ĐƯỢC ĂN XUYÊN CẢN)' : 'Orthogonal 1–2, diag 1 (PIERCES OBSTACLES)'}</td>
                    <td>{lang === 'vi' ? 'Bắn máy bay, tàu chiến, quân đất. Vành đai lửa 2 thẳng + 1 chéo.' : 'Hits aircraft, ships, ground. Projects wide AA umbrella.'}</td>
                    <td>{lang === 'vi' ? 'Di chuyển không xuyên cản, không tự vượt sông sâu (trừ ngầm đá).' : 'Cannot move through blockers; crosses river only via stone fords.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>K</span>
                      {lang === 'vi' ? 'Máy bay (K)' : 'Aircraft (K)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng 1–4 đoạn (BAY XUYÊN MỌI QUÂN)' : 'All 8 directions 1–4 steps (FLIES OVER ALL)'}</td>
                    <td>{lang === 'vi' ? '8 hướng 1–4 đoạn (thế chỗ @ hoặc ném bom _@_)' : 'All 8 directions (@ or bombing _@_)'}</td>
                    <td>{lang === 'vi' ? 'Đánh máy bay (bắt buộc thế chỗ). Đánh đất/biển (ném bom/oanh tạc).' : 'Dogfights aircraft (@). Ground/naval bomb or strike.'}</td>
                    <td>{lang === 'vi' ? 'Bay qua sông, biển, qua đầu quân ta/địch. Bị bắn hạ trong vành đai phòng không.' : 'Flies over river, sea & all pieces. Intercepted by AA umbrellas.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--team-blue)' }}>H</span>
                      {lang === 'vi' ? 'Hải quân (H)' : 'Navy (H)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng 1–4 đoạn (vượt qua quân ta trên bờ biển/bờ sông)' : 'All 8 directions 1–4 steps (passes friendly shore units)'}</td>
                    <td>{lang === 'vi' ? 'Diệt hạm 4 đoạn, pháo hạm 3 đoạn, cao xạ 1 đoạn (AH: +1)' : 'Ships 4, naval gun into land 3, AA 1 (Hero: +1)'}</td>
                    <td>{lang === 'vi' ? 'Tàu địch, Máy bay (1đ), và bắn Pháo hạm vào đất liền qua vật cản trong 3đ (AH: 4đ).' : 'Enemy ships, Aircraft (1), and bombards inland over obstacles within 3 steps (Hero: 4).'}</td>
                    <td>{lang === 'vi' ? 'Chỉ đi trên Biển (X: 0..2) và Sông (Y: 5..6). Không cắt góc đất liền, tránh 2 ngầm đá.' : 'Operates in Sea (X: 0..2) & River (Y: 5..6), avoiding land corners & stone fords.'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: GAME ANALYSIS RECORD */}
        {activeTab === 'replays' && (
          <GameAnalysisRecord lang={lang} activeMatchMoves={moves} />
        )}

        {/* TAB 5: UNDER DEVELOPMENT MODULES (aiVsAi, stats) */}
        {activeTab !== 'home' &&
          activeTab !== 'play' &&
          activeTab !== 'rules' &&
          activeTab !== 'replays' && (
          <div className={styles.devPanel}>
            <div className={styles.devBadge}>⚙</div>
            <h2 className={styles.devTitle}>
              {lang === 'vi' ? 'Chức Năng Đang Phát Triển' : 'Module In Development'}
            </h2>
            <p className={styles.devDesc}>
              {lang === 'vi'
                ? `Chức năng "${t.nav[activeTab as keyof typeof t.nav] || activeTab}" được lên lịch triển khai trong các Task tiếp theo (Task 1.2+) theo lộ trình phát triển của dự án.`
                : `The "${t.nav[activeTab as keyof typeof t.nav] || activeTab}" module is scheduled for implementation in Task 1.2+ according to the project roadmap.`}
            </p>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setActiveTab('play')}
              >
                {t.home.btnPlayNow}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setActiveTab('home')}
              >
                {t.game.backToHome}
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModalType !== null}
        title={
          confirmModalType === 'NEW_GAME'
            ? t.game.confirmNewGameTitle
            : confirmModalType === 'RESIGN'
            ? t.game.confirmResignTitle
            : t.game.confirmDrawTitle
        }
        description={
          confirmModalType === 'NEW_GAME'
            ? t.game.confirmNewGameDesc
            : confirmModalType === 'RESIGN'
            ? t.game.confirmResignDesc
            : t.game.confirmDrawDesc
        }
        confirmLabel={
          confirmModalType === 'RESIGN'
            ? t.game.resign
            : confirmModalType === 'DRAW'
            ? t.game.drawOffer
            : t.game.newGame
        }
        isDanger={confirmModalType === 'RESIGN' || confirmModalType === 'NEW_GAME'}
        onConfirm={() => {
          if (confirmModalType === 'NEW_GAME') {
            handleResetBoard();
          } else if (confirmModalType === 'RESIGN') {
            handleConfirmResign();
          } else if (confirmModalType === 'DRAW') {
            handleConfirmDraw();
          }
        }}
        onCancel={() => setConfirmModalType(null)}
        lang={lang}
      />

      {/* Game Over Victory / Summary Modal */}
      <GameOverModal
        isOpen={isGameOverModalOpen}
        result={gameResult}
        moves={moves}
        lang={lang}
        onNewGame={handleResetBoard}
        onClose={() => setIsGameOverModalOpen(false)}
      />

      <footer className={styles.footer}>
        <p>
          Commander Chess AI Platform — Saigon University (2026) | Advanced Artificial Intelligence
        </p>
      </footer>
    </>
  );
};

