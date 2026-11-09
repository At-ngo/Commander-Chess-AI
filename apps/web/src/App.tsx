import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Header } from './components/Header/Header';
import { Home } from './components/Home/Home';
import { Board } from './components/Board/Board';
import { PieceDetail } from './components/PieceDetail/PieceDetail';
import { MoveHistory } from './components/MoveHistory/MoveHistory';
import { CapturedPieces } from './components/CapturedPieces/CapturedPieces';
import { GameOverModal } from './components/GameOverModal/GameOverModal';
import { ConfirmModal } from './components/ConfirmModal/ConfirmModal';
import { PieceState, Side, LegalAction, MoveRecord, GameStatus, GameResult, GameMode, ActiveCompoundState } from './types';
import { getInitialPieces } from './utils/initialBoard';
import { getMockLegalActions, applyMockAction, getAllCarriedPieceIds, selectSmartAiAction } from './services/mockGameService';
import { apiClient } from './services/apiClient';
import { Language, translations } from './i18n';
import styles from './App.module.css';

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
  const stateVersionRef = useRef<number>(1);
  const piecesRef = useRef<PieceState[]>(pieces);
  piecesRef.current = pieces;

  const syncStateVersion = (newVersion: number) => {
    stateVersionRef.current = newVersion;
    setStateVersion(newVersion);
  };

  const [activeCompound, setActiveCompound] = useState<ActiveCompoundState | null>(null);
  const [carryCargoWithMovement, setCarryCargoWithMovement] = useState<boolean>(true);

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

  const selectedPiece = pieces.find((p) => p.piece_id === selectedPieceId) || null;

  // Calculate legal actions for currently selected piece of active side
  const legalActions = useMemo(() => {
    if (status === 'GAME_OVER' || isAiThinking) return [];
    if (!selectedPiece || selectedPiece.side !== sideToMove) return [];
    // Nếu đang trong lượt tác chiến của tổ hợp và quân này đã đi rồi -> không còn nước đi
    if (activeCompound && activeCompound.movedPieceIds.includes(selectedPiece.piece_id)) {
      return [];
    }
    return getMockLegalActions(selectedPiece, pieces, carryCargoWithMovement);
  }, [status, isAiThinking, selectedPiece, sideToMove, pieces, activeCompound, carryCargoWithMovement]);

  const handleSelectPiece = (piece: PieceState) => {
    setCarryCargoWithMovement(true);
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

    // Ở sở chỉ huy, sở chỉ huy không thể di chuyển nên nếu có Tư lệnh trong đó,
    // click vào sẽ tự động chọn Tư lệnh để di chuyển ra ngoài!
    if (piece.type === 'HEADQUARTERS') {
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
    setSelectedPieceId(null);
    setActiveCompound(null);
    setCarryCargoWithMovement(true);

    const confirmAction: LegalAction = {
      action_id: `confirm_${Date.now()}`,
      action_type: 'MOVE',
      piece_id: 'COMPOUND',
      from_pos: { x: 0, y: 0 },
      to_pos: { x: 0, y: 0 },
      target_piece_id: null,
      notation: 'CONFIRM_DEPLOYMENT',
      description:
        lang === 'vi'
          ? 'Đã xác nhận hoàn tất lượt tác chiến của tổ hợp.'
          : 'Compound deployment turn completed.',
    };
    setMoves((prev) => [
      ...prev,
      {
        move_number: prev.length + 1,
        side: sideToMove,
        action: confirmAction,
        notation: 'CONFIRM_DEPLOYMENT',
        captured_piece_type: null,
        timestamp: Date.now(),
      },
    ]);

    // Đồng bộ kết thúc lượt tổ hợp sang FastAPI backend (nếu online)
    if (backendOnline && gameSessionId) {
      try {
        const res = await apiClient.endTurn(gameSessionId, stateVersionRef.current);
        syncStateVersion(res.state_version);
      } catch (err) {
        console.warn('Backend endTurn failed:', err);
      }
    }

    // Kết thúc lượt tổ hợp: chuyển lượt ngay lập tức sang phe đối diện!
    setSideToMove((prev) => (prev === 'RED' ? 'BLUE' : 'RED'));
  };

  const triggerAiStep = async () => {
    if (status === 'GAME_OVER' || isAiThinking) return;
    setIsAiThinking(true);

    try {
      if (backendOnline && gameSessionId) {
        const aiRes = await apiClient.aiStep(gameSessionId);
        syncStateVersion(aiRes.state_version);

        // PHÒNG THỦ TUYỆT ĐỐI: Kiểm tra quân thực hiện nước đi của AI (chỉ chấp nhận quân BLUE)
        if (aiRes.event.actor_id) {
          const actorPiece = piecesRef.current.find((p) => p.piece_id === aiRes.event.actor_id);
          if (actorPiece && actorPiece.side === 'RED') {
            console.error('LỖI AN TOÀN: Backend AI trả về quân của người chơi (RED)! Từ chối thực thi nước đi này.');
            return;
          }
        }

        let deadPiece: PieceState | null = null;
        if (aiRes.event.target_id) {
          deadPiece = piecesRef.current.find((p) => p.piece_id === aiRes.event.target_id) || null;
          if (deadPiece) {
            setCapturedPieces((prev) => [...prev, deadPiece!]);
          }
        }

        if (aiRes.game_state.scores) {
          setScores({
            RED: aiRes.game_state.scores.RED,
            BLUE: aiRes.game_state.scores.BLUE,
          });
        }

        if (aiRes.game_state.pieces) {
          const reconciledPieces = aiRes.game_state.pieces.map((rp) => {
            const localPiece = piecesRef.current.find((lp) => lp.piece_id === rp.piece_id);
            if (!localPiece) return rp;
            if (!localPiece.is_alive) {
              return { ...rp, is_alive: false };
            }
            if (aiRes.event.target_id === rp.piece_id) {
              return { ...rp, is_alive: false };
            }
            // Bảo vệ quân của người chơi (RED) tuyệt đối không bị đè toạ độ cũ từ AI response
            if (localPiece.side === 'RED') {
              return {
                ...rp,
                position: { ...localPiece.position },
                carried_by_id: localPiece.carried_by_id,
                is_hero: localPiece.is_hero || rp.is_hero,
              };
            }
            return {
              ...rp,
              is_hero: localPiece.is_hero || rp.is_hero,
            };
          });
          const newlyDeadAi = reconciledPieces.filter(
            (np) => !np.is_alive && piecesRef.current.find((p) => p.piece_id === np.piece_id && p.is_alive)
          );
          if (newlyDeadAi.length > 0) {
            setCapturedPieces((prev) => [...prev, ...newlyDeadAi]);
          }
          // Bảo đảm tính nhất quán 2 chiều tuyệt đối giữa carried_by_id và carrying_piece_ids
          const consistentPieces = reconciledPieces.map((p) => ({
            ...p,
            carrying_piece_ids: reconciledPieces
              .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
              .map((other) => other.piece_id),
          }));
          setPieces(consistentPieces);
        }

        const actorBefore = piecesRef.current.find((p) => p.piece_id === aiRes.event.actor_id);
        const fromPos = actorBefore
          ? { ...actorBefore.position }
          : (aiRes.event.details?.from_pos || { x: 0, y: 0 });
        const toPos = aiRes.event.details?.to_pos
          ? { ...aiRes.event.details.to_pos }
          : (() => {
              const actorAfter = aiRes.game_state?.pieces?.find((p) => p.piece_id === aiRes.event.actor_id);
              return actorAfter ? { ...actorAfter.position } : fromPos;
            })();

        const newRecord: MoveRecord = {
          move_number: moves.length + 1,
          side: sideToMove,
          action: {
            action_id: `ai_${Date.now()}`,
            action_type: aiRes.event.event_type === 'PIECE_CAPTURED' ? 'CAPTURE_REPLACE' : 'MOVE',
            piece_id: aiRes.event.actor_id || '',
            from_pos: fromPos,
            to_pos: toPos,
            notation: aiRes.event.notation,
            description: 'Nước đi của Random Agent',
          },
          notation: aiRes.event.notation,
          captured_piece_type: deadPiece ? deadPiece.type : null,
          timestamp: Date.now(),
        };
        const nextMoves = [...moves, newRecord];
        setMoves(nextMoves);

        if (aiRes.game_state.status === 'GAME_OVER') {
          const winnerSide: Side = (aiRes.game_state.result?.winner as Side) || (aiRes.game_state.side_to_move === 'RED' ? 'BLUE' : 'RED');
          const finalResult: GameResult = {
            winner: winnerSide,
            reason: aiRes.game_state.result?.reason || 'COMMANDER_CAPTURED',
            final_scores: aiRes.game_state.scores || scores,
            total_turns: Math.ceil(nextMoves.length / 2),
            total_moves: nextMoves.length,
            duration_seconds: matchSeconds,
            captured_commander_side: winnerSide === 'BLUE' ? 'RED' : 'BLUE',
          };
          setStatus('GAME_OVER');
          setGameResult(finalResult);
          setIsGameOverModalOpen(true);
          setSelectedPieceId(null);
          return;
        }

        setSelectedPieceId(null);
        setSideToMove('RED');
      } else {
        // Fallback ngoại tuyến (Mock engine) - Tác tử AI thông minh không hiến Tư lệnh & ưu tiên hóa giải chiếu (DEC-019)
        const smartAction = selectSmartAiAction(piecesRef.current, sideToMove);
        if (smartAction) {
          await handleExecuteAction(smartAction, true);
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
    if (status !== 'IN_PROGRESS' || activeTab !== 'play') return;
    if (gameMode === 'HUMAN_VS_AI' && sideToMove === 'BLUE' && !isAiThinking) {
      const timer = setTimeout(() => {
        triggerAiStep();
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [sideToMove, gameMode, status, activeTab, isAiThinking]);

  const handleExecuteAction = async (action: LegalAction, isAiAction: boolean = false) => {
    if (status === 'GAME_OVER' || (!isAiAction && isAiThinking)) return;

    // 1. Authoritative local move application (retains full piece attributes & stability)
    const { nextPieces, event, capturedPiece } = applyMockAction(action, pieces);
    setPieces(nextPieces);

    // Thu thập toàn bộ tổn thất (quân bị ăn, máy bay bị bắn hạ trong phòng không, quân chở theo)
    const newlyDead = nextPieces.filter(
      (np) => !np.is_alive && pieces.find((p) => p.piece_id === np.piece_id && p.is_alive)
    );
    if (newlyDead.length > 0) {
      setCapturedPieces((prev) => [...prev, ...newlyDead]);
    } else if (capturedPiece) {
      setCapturedPieces((prev) => [...prev, capturedPiece]);
    }

    const finalRedScore = scores.RED + event.score_delta.RED;
    const finalBlueScore = scores.BLUE + event.score_delta.BLUE;

    if (event.score_delta.RED > 0 || event.score_delta.BLUE > 0) {
      setScores({
        RED: finalRedScore,
        BLUE: finalBlueScore,
      });
    }

    const newRecord: MoveRecord = {
      move_number: moves.length + 1,
      side: sideToMove,
      action,
      notation: event.notation || action.notation,
      captured_piece_type: capturedPiece ? capturedPiece.type : null,
      timestamp: Date.now(),
    };
    const nextMoves = [...moves, newRecord];
    setMoves(nextMoves);

    // KẾT THÚC TRẬN ĐẤU: Bắt được Tư lệnh đối phương!
    if (capturedPiece && capturedPiece.type === 'COMMANDER') {
      const winner: Side = sideToMove;
      const result: GameResult = {
        winner,
        reason: 'COMMANDER_CAPTURED',
        final_scores: { RED: finalRedScore, BLUE: finalBlueScore },
        total_turns: Math.ceil(nextMoves.length / 2),
        total_moves: nextMoves.length,
        duration_seconds: matchSeconds,
        captured_commander_side: capturedPiece.side,
      };
      setStatus('GAME_OVER');
      setGameResult(result);
      setIsGameOverModalOpen(true);
      setSelectedPieceId(null);
      setActiveCompound(null);

      if (backendOnline && gameSessionId) {
        apiClient.executeAction(gameSessionId, {
          action_type: action.action_type,
          piece_id: action.piece_id,
          to_pos: action.to_pos,
          target_piece_id: action.target_piece_id,
          state_version: stateVersionRef.current,
          is_compound_action: false,
        }).then((res) => syncStateVersion(res.state_version)).catch(console.warn);
      }
      return;
    }

    // KẾT THÚC TRẬN ĐẤU: Chiếu hết Tư lệnh đối phương! (DEC-019 & CHECKMATE)
    if (event.details?.is_checkmate) {
      const winner: Side = sideToMove;
      const result: GameResult = {
        winner,
        reason: 'CHECKMATE',
        final_scores: { RED: finalRedScore, BLUE: finalBlueScore },
        total_turns: Math.ceil(nextMoves.length / 2),
        total_moves: nextMoves.length,
        duration_seconds: matchSeconds,
        captured_commander_side: winner === 'RED' ? 'BLUE' : 'RED',
      };
      setStatus('GAME_OVER');
      setGameResult(result);
      setIsGameOverModalOpen(true);
      setSelectedPieceId(null);
      setActiveCompound(null);

      if (backendOnline && gameSessionId) {
        apiClient.executeAction(gameSessionId, {
          action_type: action.action_type,
          piece_id: action.piece_id,
          to_pos: action.to_pos,
          target_piece_id: action.target_piece_id,
          state_version: stateVersionRef.current,
          is_compound_action: false,
        }).then((res) => syncStateVersion(res.state_version)).catch(console.warn);
      }
      return;
    }

    // =========================================================================
    // QUY TẮC TỔ HỢP CÕNG QUÂN (Compound Action Mechanics - Rule 1, 2, 3, 4, 5)
    // =========================================================================
    if (isAiAction) {
      setActiveCompound(null);
      setSelectedPieceId(null);
      setSideToMove('RED');

      if (backendOnline && gameSessionId) {
        apiClient.executeAction(gameSessionId, {
          action_type: action.action_type,
          piece_id: action.piece_id,
          to_pos: action.to_pos,
          target_piece_id: action.target_piece_id,
          state_version: stateVersionRef.current,
          is_compound_action: false,
        }).then((res) => syncStateVersion(res.state_version)).catch(console.warn);
      }
      return;
    }

    const actorBefore = pieces.find((p) => p.piece_id === action.piece_id);
    const originPos = activeCompound
      ? activeCompound.originPos
      : actorBefore
      ? { ...actorBefore.position }
      : { ...action.from_pos };

    // Xác định xem hành động này có thuộc về một tổ hợp quân hay không
    let memberIds: string[] = [];
    if (activeCompound) {
      memberIds = activeCompound.memberIds;
    } else {
      const carriedBy = actorBefore?.carried_by_id;
      const rootCarrier = carriedBy
        ? pieces.find((p) => p.piece_id === carriedBy) || actorBefore
        : actorBefore;
      const passengers = pieces.filter(
        (p) =>
          p.is_alive &&
          p.side === sideToMove &&
          (p.carried_by_id === rootCarrier?.piece_id || p.carried_by_id === actorBefore?.piece_id)
      );
      if (rootCarrier && passengers.length > 0) {
        memberIds = [rootCarrier.piece_id, ...passengers.map((p) => p.piece_id)];
      }
    }

    const isCompoundAction = memberIds.length > 1;

    // Xử lý chuỗi hành động trong lượt tổ hợp (STACK_ACTIVE):
    const previouslyMoved = activeCompound ? activeCompound.movedPieceIds : [];
    const newMoved = [...previouslyMoved, action.piece_id];

    // QUY TẮC 4: Nếu quân di chuyển ra khỏi vị trí xuất phát, kể cả có mang quân theo
    // thì quân được mang cũng được tính là đã hoàn thành nước đi và không được đi tiếp!
    const movedAway =
      action.action_type !== 'CAPTURE_STAND' &&
      (action.to_pos.x !== originPos.x || action.to_pos.y !== originPos.y);

    if (movedAway && action.carry_cargo !== false) {
      const travelingCargo = getAllCarriedPieceIds(action.piece_id, pieces);
      for (const tcId of travelingCargo) {
        if (!newMoved.includes(tcId)) {
          newMoved.push(tcId);
        }
      }
    }

    setCarryCargoWithMovement(true);

    // Kiểm tra xem còn quân nào trong tổ hợp còn ở vị trí xuất phát và chưa hành động không
    const remainingAtOrigin = nextPieces.filter(
      (p) =>
        p.is_alive &&
        memberIds.includes(p.piece_id) &&
        !newMoved.includes(p.piece_id) &&
        p.position.x === originPos.x &&
        p.position.y === originPos.y
    );

    // Xác định chính xác xem lượt tổ hợp này đã kết thúc hay còn tiếp tục nước đi kế tiếp
    const isCompoundStillActive =
      isCompoundAction &&
      remainingAtOrigin.length > 0 &&
      newMoved.length < memberIds.length;

    // 2. Đồng bộ hành động sang FastAPI backend session với cờ is_compound_action chính xác
    if (backendOnline && gameSessionId) {
      try {
        const res = await apiClient.executeAction(gameSessionId, {
          action_type: action.action_type,
          piece_id: action.piece_id,
          to_pos: action.to_pos,
          target_piece_id: action.target_piece_id,
          state_version: stateVersionRef.current,
          is_compound_action: isCompoundStillActive,
        });
        syncStateVersion(res.state_version);
        if (res.game_state && res.game_state.pieces) {
          // Bảo đảm các quân đã bị tiêu diệt cục bộ không bị phản hồi từ backend đè trạng thái
          // Và quân người chơi vừa di chuyển giữ nguyên toạ độ đích đến đã chọn
          const reconciledPieces = res.game_state.pieces.map((rp) => {
            const localPiece = nextPieces.find((lp) => lp.piece_id === rp.piece_id);
            if (!localPiece) return rp;
            if (!localPiece.is_alive) {
              return { ...rp, is_alive: false };
            }
            if (localPiece.piece_id === action.piece_id || localPiece.side === actorBefore?.side) {
              return {
                ...rp,
                position: { ...localPiece.position },
                carried_by_id: localPiece.carried_by_id,
                is_hero: localPiece.is_hero || rp.is_hero,
              };
            }
            return {
              ...rp,
              is_hero: localPiece.is_hero || rp.is_hero,
            };
          });
          // Bảo đảm tính nhất quán 2 chiều tuyệt đối giữa carried_by_id và carrying_piece_ids
          const consistentPieces = reconciledPieces.map((p) => ({
            ...p,
            carrying_piece_ids: reconciledPieces
              .filter((other) => other.is_alive && other.carried_by_id === p.piece_id)
              .map((other) => other.piece_id),
          }));
          setPieces(consistentPieces);
        }
      } catch (err) {
        console.warn('Backend action synchronization failed:', err);
        // Refresh state_version từ backend để tránh lỗi lệch phiên bản ở các nước tiếp theo
        try {
          const fresh = await apiClient.getGame(gameSessionId);
          syncStateVersion(fresh.state_version);
        } catch (syncErr) {
          console.warn('Failed to resync state version:', syncErr);
        }
      }
    }

    if (isCompoundStillActive) {
      // Vẫn còn quân ở vị trí xuất phát chưa hành động: Tiếp tục duy trì lượt tổ hợp (STACK_ACTIVE)
      setActiveCompound({
        originPos,
        memberIds,
        movedPieceIds: newMoved,
        actionCount: (activeCompound?.actionCount || 0) + 1,
      });
      setSelectedPieceId(null);
      // Giữ nguyên sideToMove để người chơi tiếp tục chọn quân còn lại hoặc bấm "Hoàn tất lượt tổ hợp"!
    } else {
      // Nước đi đơn lẻ hoặc toàn bộ các quân trong tổ hợp đã hoàn tất nước đi: Kết thúc lượt, đổi phe!
      setActiveCompound(null);
      setSelectedPieceId(null);
      setSideToMove((prev) => (prev === 'RED' ? 'BLUE' : 'RED'));
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
    setPieces(getInitialPieces());
    setSelectedPieceId(null);
    setActiveCompound(null);
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
      } catch (err) {
        console.warn('Backend new game creation failed:', err);
      }
    }
  };

  const handleRequestResign = () => {
    if (status === 'GAME_OVER') return;
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
    setStatus('GAME_OVER');
    setGameResult(result);
    setConfirmModalType(null);
    setIsGameOverModalOpen(true);
  };

  const handleRequestDraw = () => {
    if (status === 'GAME_OVER') return;
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
              <MoveHistory moves={moves} lang={lang} />

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
              <Board
                pieces={pieces}
                selectedPieceId={selectedPieceId}
                onSelectPiece={handleSelectPiece}
                legalActions={legalActions}
                onExecuteAction={handleExecuteAction}
                onConfirmCompound={handleConfirmCompound}
                lastMove={moves.length > 0 ? moves[moves.length - 1] : null}
                activeCompound={activeCompound}
                carryCargo={carryCargoWithMovement}
                onToggleCarryCargo={setCarryCargoWithMovement}
              />
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
                      sideToMove === 'BLUE' ? styles.turnDotBlue : ''
                    }`}
                  />
                  <span className={styles.turnText}>
                    {t.game.turn}:{' '}
                    <strong
                      className={
                        sideToMove === 'RED'
                          ? styles.turnSideRed
                          : styles.turnSideBlue
                      }
                    >
                      {sideToMove === 'RED'
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
                      {scores.RED}
                    </span>
                  </div>
                  <div className={styles.scoreDivider}>vs</div>
                  <div className={styles.scoreTeam}>
                    <span className={styles.teamLabelBlue}>{t.game.blueSide}</span>
                    <span className={styles.scoreValue}>
                      {scores.BLUE}
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
                    disabled={status === 'GAME_OVER' || isAiThinking}
                    title={t.game.aiMoveBtn}
                  >
                    {t.game.aiMoveBtn}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setSideToMove(sideToMove === 'RED' ? 'BLUE' : 'RED')}
                    disabled={status === 'GAME_OVER' || isAiThinking}
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
                    disabled={status === 'GAME_OVER'}
                    title={t.game.resign}
                  >
                    🏳️ {t.game.resign}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleRequestDraw}
                    disabled={status === 'GAME_OVER'}
                    title={t.game.drawOffer}
                  >
                    🤝 {t.game.drawOffer}
                  </button>
                </div>
              </div>

              {/* Tactical Piece Detail Panel */}
              <PieceDetail
                piece={selectedPiece}
                allPieces={pieces}
                onSelectPiece={handleSelectPiece}
                lang={lang}
              />

              {/* Captured Pieces Tracker */}
              <CapturedPieces capturedPieces={capturedPieces} lang={lang} />
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

              {/* Card 2: Quy tắc Tối thượng — Cấm Tư lệnh Đối mặt nhau */}
              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle} style={{ color: 'var(--crimson-primary)' }}>
                  <span>⚠️</span>
                  {lang === 'vi' ? '2. Cấm Tư lệnh Đối mặt (Lộ mặt Tướng)' : '2. Opposing Commanders Prohibition'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Hai Tư lệnh không bao giờ được cùng nằm trên một đường thẳng (cùng hàng ngang hoặc cùng cột dọc) mà ở giữa không có bất kỳ quân cờ nào che chắn.'
                      : 'The two Commanders must NEVER face each other on the same orthogonal line (row or column) without any piece blocking between them.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Nước đi tự sát bị cấm: Tư lệnh không được tự di chuyển vào đường thẳng trống đang có Tư lệnh địch.'
                      : 'Suicide moves prohibited: Commander cannot step into an unobstructed line facing enemy Commander.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Ghim quân cản: Quân cờ đang là vật cản duy nhất giữa 2 Tư lệnh bị "ghim" tại chỗ, tuyệt đối không được di chuyển rời khỏi đường thẳng đó.'
                      : 'Pinned piece: A single piece standing between two Commanders is pinned and cannot move off that line.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Sở chỉ huy che chở: Tư lệnh trú trong Sở chỉ huy được che chở an toàn khỏi quy tắc đối mặt.'
                      : 'HQ shelter: Commander inside a Headquarters is shielded from the opposing commanders rule.'}
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
                      ? 'Điều kiện phong: Tự động phong Anh hùng khi một quân đi nước chiếu Tư lệnh địch, hoặc khi phe chỉ còn đúng 1 quân khác ngoài Tư lệnh.'
                      : 'Promotion conditions: Automatically promoted when checking the enemy Commander, or when only 1 non-Commander piece remains.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Dấu hiệu nhận biết: Quân được phong Anh hùng có thêm một ngôi sao vàng nhỏ (★) nằm ở góc trên quân cờ trên bàn cờ.'
                      : 'Visual badge: Heroic pieces proudly display a golden star badge (★) at the top-right corner of their piece icon.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Quyền năng vượt trội: Tăng 1 đoạn tầm đi và ăn; được bổ sung các đường chéo; Máy bay Anh hùng trở thành máy bay tàng hình miễn nhiễm phòng không!'
                      : 'Heroic traits: +1 step to movement and attack range; gains diagonal movements; Heroic Aircraft becomes stealth and ignores air defense!'}
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
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (thế chỗ @)' : 'Orthogonal 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Quân mặt đất, tàu ven bờ. KHÔNG đánh máy bay.' : 'Ground units, coastal ships. NO aircraft.'}</td>
                    <td>{lang === 'vi' ? 'Tự qua sông sâu được. Không ra biển sâu.' : 'Crosses deep river. Cannot enter deep sea.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--text-secondary)' }}>S</span>
                      {lang === 'vi' ? 'Sở chỉ huy (S)' : 'Headquarters (S)'}
                    </td>
                    <td>{lang === 'vi' ? 'Cố định, không di chuyển' : 'Stationary, no move'}</td>
                    <td>{lang === 'vi' ? 'Không ăn quân' : 'No attack'}</td>
                    <td>{lang === 'vi' ? 'Công trình phòng thủ che chắn Tư lệnh.' : 'Defensive structure shielding Commander.'}</td>
                    <td>{lang === 'vi' ? 'Cố định trên đất liền. Bị phá Tư lệnh lộ diện.' : 'Land base. When destroyed, Commander revealed.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--crimson-primary)' }}>B</span>
                      {lang === 'vi' ? 'Bộ binh (B)' : 'Infantry (B)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn' : 'Orthogonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (thế chỗ @)' : 'Orthogonal 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Quân mặt đất, tàu ven bờ. KHÔNG đánh máy bay.' : 'Ground units, coastal ships. NO aircraft.'}</td>
                    <td>{lang === 'vi' ? 'Bơi qua sông sâu được. Lên xe tăng, tàu chiến.' : 'Swims across deep river. Boards tanks, warships.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--crimson-primary)' }}>D</span>
                      {lang === 'vi' ? 'Dân quân (D)' : 'Militia (D)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng (ngang/dọc/chéo) 1 đoạn' : 'All 8 directions, 1 step'}</td>
                    <td>{lang === 'vi' ? '8 hướng 1 đoạn (thế chỗ @)' : 'All 8 directions, 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Quân mặt đất, tàu ven bờ. KHÔNG đánh máy bay.' : 'Ground units, coastal ships. NO aircraft.'}</td>
                    <td>{lang === 'vi' ? 'Qua sông sâu được. Không ra biển sâu.' : 'Crosses deep river. Cannot enter deep sea.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>T</span>
                      {lang === 'vi' ? 'Xe tăng (T)' : 'Tank (T)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2 đoạn (bị cản ở đoạn 1)' : 'Orthogonal 1–2 steps (blocked)'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2 đoạn (thế chỗ @)' : 'Orthogonal 1–2 steps (@)'}</td>
                    <td>{lang === 'vi' ? 'Quân đất. Bắn tàu biển tại chỗ (_@_). Không đánh máy bay.' : 'Ground units. Fires at sea ships in-place (_@_).'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu. Cõng tối đa 2 bộ binh.' : 'No deep river alone. Transports up to 2 infantry.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--text-secondary)' }}>C</span>
                      {lang === 'vi' ? 'Công binh (C)' : 'Engineer (C)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn' : 'Orthogonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (thế chỗ @)' : 'Orthogonal 1 step (@)'}</td>
                    <td>{lang === 'vi' ? 'Quân mặt đất. KHÔNG đánh máy bay.' : 'Ground units. NO aircraft.'}</td>
                    <td>{lang === 'vi' ? 'Bơi qua sông sâu. Đứng ở bờ cõng vũ khí nặng qua sông.' : 'Swims river. Bridges/carries heavy weapons across.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>A</span>
                      {lang === 'vi' ? 'Pháo binh (A)' : 'Artillery (A)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng 1–3 đoạn (bị cản)' : 'All 8 directions 1–3 steps (blocked)'}</td>
                    <td>{lang === 'vi' ? '8 hướng 1–3 đoạn (BẮN XUYÊN MỌI QUÂN CẢN)' : 'All 8 directions (PIERCES ALL OBSTACLES)'}</td>
                    <td>{lang === 'vi' ? 'Mọi quân đất. Bắn tàu biển tại chỗ (_@_). Không đánh máy bay.' : 'Ground units. Fires at ships in-place (_@_).'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu (qua ngầm hoặc Công binh chở).' : 'No deep river alone (needs Engineer or stone ford).'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--team-blue)' }}>F</span>
                      {lang === 'vi' ? 'Cao xạ (F)' : 'Anti-Air (F)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn' : 'Orthogonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1 đoạn (bắn máy bay & bộ binh)' : 'Orthogonal 1 step (hits aircraft & infantry)'}</td>
                    <td>{lang === 'vi' ? 'Bắn hạ máy bay và quân bộ. Tạo vành đai lửa 1 đoạn.' : 'Shoots aircraft and infantry. Projects 1-step AA.'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu. Không ra biển sâu.' : 'No deep river alone. Cannot enter deep sea.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--team-blue)' }}>L</span>
                      {lang === 'vi' ? 'Tên lửa (L)' : 'Missile (L)'}
                    </td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2 đoạn, chéo 1 đoạn' : 'Orthogonal 1–2, diagonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Ngang/dọc 1–2 đoạn, chéo 1 đoạn' : 'Orthogonal 1–2, diagonal 1 step'}</td>
                    <td>{lang === 'vi' ? 'Bắn máy bay, tàu chiến, quân đất. Vành đai lửa 2 thẳng + 1 chéo.' : 'Hits aircraft, ships, ground. Projects wide AA umbrella.'}</td>
                    <td>{lang === 'vi' ? 'Không tự qua sông sâu. Không ra biển sâu.' : 'No deep river alone. Cannot enter deep sea.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--gold-primary)' }}>K</span>
                      {lang === 'vi' ? 'Máy bay (K)' : 'Aircraft (K)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng 1–4 đoạn (BAY XUYÊN MỌI QUÂN)' : 'All 8 directions 1–4 steps (FLIES OVER ALL)'}</td>
                    <td>{lang === 'vi' ? '8 hướng 1–4 đoạn (thế chỗ @ hoặc ném bom _@_)' : 'All 8 directions (@ or bombing _@_)'}</td>
                    <td>{lang === 'vi' ? 'Đánh máy bay (bắt buộc thế chỗ). Đánh đất/biển (ném bom/oanh tạc).' : 'Dogfights aircraft (@). Ground/naval bomb or strike.'}</td>
                    <td>{lang === 'vi' ? 'Bay qua sông, biển. Bị tiêu diệt bởi vành đai lửa phòng không.' : 'Flies over river & sea. Intercepted by AA umbrellas.'}</td>
                  </tr>
                  <tr>
                    <td className={styles.rulesPieceName}>
                      <span style={{ color: 'var(--team-blue)' }}>H</span>
                      {lang === 'vi' ? 'Hải quân (H)' : 'Navy (H)'}
                    </td>
                    <td>{lang === 'vi' ? '8 hướng 1–4 đoạn (trên sông/biển)' : 'All 8 directions 1–4 steps (sea & river)'}</td>
                    <td>{lang === 'vi' ? 'Diệt hạm 4 đoạn, pháo hạm 3 đoạn, cao xạ hạm 1 đoạn' : 'Missiles 4 steps, naval guns 3, AA gun 1'}</td>
                    <td>{lang === 'vi' ? 'Tàu chiến địch, quân trên đất/bờ, máy bay. Cõng máy bay/xe tăng.' : 'Enemy warships, coastal units, aircraft. Transports.'}</td>
                    <td>{lang === 'vi' ? 'Chỉ đi trên Biển (X: 0..2) và Sông (Y: 5..6). Không lên cạn.' : 'Operates only in Sea (X: 0..2) and River (Y: 5..6).'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: UNDER DEVELOPMENT MODULES (aiVsAi, replays, stats) */}
        {activeTab !== 'home' && activeTab !== 'play' && activeTab !== 'rules' && (
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

