import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MoveRecord, PieceState } from '../../types';
import { Language, translations } from '../../i18n';
import {
  AnalysisResult,
  CompoundEventTag,
  formatMoveRecordsForRecordInput,
  parseAndReplayRecord,
  SAMPLE_AI_VS_AI_JSON_RECORD,
  SAMPLE_NOTATION_RECORD,
} from '../../utils/recordAnalyzer';
import { Board } from '../Board/Board';
import { CompoundControlBar } from '../Board/CompoundControlBar';
import { PieceDetail } from '../PieceDetail/PieceDetail';
import { CapturedPieces } from '../CapturedPieces/CapturedPieces';
import styles from './GameAnalysisRecord.module.css';

interface GameAnalysisRecordProps {
  lang: Language;
  activeMatchMoves?: MoveRecord[];
}

export const GameAnalysisRecord: React.FC<GameAnalysisRecordProps> = ({
  lang,
  activeMatchMoves = [],
}) => {
  const t = translations[lang];
  const fileInputRef = useRef<HTMLInputElement>(null);
  const moveListRef = useRef<HTMLDivElement>(null);

  const [rawInput, setRawInput] = useState<string>('');
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(false);
  const [playSpeedMs, setPlaySpeedMs] = useState<number>(900);
  const [flipped, setFlipped] = useState<boolean>(false);
  const [inspectedPieceId, setInspectedPieceId] = useState<string | null>(null);
  const [isInputCollapsed, setIsInputCollapsed] = useState<boolean>(false);
  const [copiedNotation, setCopiedNotation] = useState<boolean>(false);

  const runAnalysis = (text: string) => {
    setIsAutoPlaying(false);
    const res = parseAndReplayRecord(text);
    setAnalysis(res);
    setCurrentStep(0);
    setInspectedPieceId(null);
    if (res.success && res.frames.length > 1) {
      // Jump to step 1 on initial load or stay at 0? Step 0 is initial setup,
      // advancing to 1 immediately shows the first move arrow nicely or stay at 0:
      // Let's keep at 0 so user sees full initial state cleanly, or navigate freely.
      setCurrentStep(0);
    }
  };

  const frames = analysis?.success ? analysis.frames : [];
  const maxStep = Math.max(0, frames.length - 1);
  const currentFrame = frames[Math.min(currentStep, maxStep)] || null;

  // Auto-play progression timer
  useEffect(() => {
    if (!isAutoPlaying || !analysis?.success || frames.length <= 1) return;
    if (currentStep >= maxStep) {
      setIsAutoPlaying(false);
      return;
    }
    const timer = setTimeout(() => {
      setCurrentStep((prev) => Math.min(maxStep, prev + 1));
    }, playSpeedMs);
    return () => clearTimeout(timer);
  }, [isAutoPlaying, currentStep, maxStep, playSpeedMs, analysis?.success, frames.length]);

  // Keyboard navigation (Left/Right/Home/End) when not typing inside textarea/input
  useEffect(() => {
    if (!analysis?.success || frames.length <= 1) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'TEXTAREA' || tag === 'INPUT' || tag === 'SELECT') return;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setIsAutoPlaying(false);
        setCurrentStep((prev) => Math.max(0, prev - 1));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setIsAutoPlaying(false);
        setCurrentStep((prev) => Math.min(maxStep, prev + 1));
      } else if (e.key === 'Home') {
        e.preventDefault();
        setIsAutoPlaying(false);
        setCurrentStep(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        setIsAutoPlaying(false);
        setCurrentStep(maxStep);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [analysis?.success, frames.length, maxStep]);

  // Scroll move list row into view cleanly
  useEffect(() => {
    if (!moveListRef.current) return;
    const activeEl = moveListRef.current.querySelector(
      `[data-step-index="${currentStep}"]`
    ) as HTMLElement | null;
    if (activeEl) {
      activeEl.scrollIntoView({ block: 'nearest' });
    }
  }, [currentStep]);

  const manualInspectedAliveId = useMemo(() => {
    if (!currentFrame || !inspectedPieceId) return null;
    return currentFrame.pieces.some((p) => p.is_alive && p.piece_id === inspectedPieceId)
      ? inspectedPieceId
      : null;
  }, [currentFrame, inspectedPieceId]);

  const effectiveInspectedPieceId =
    manualInspectedAliveId ??
    currentFrame?.focusPieceId ??
    currentFrame?.activeCompound?.memberIds[0] ??
    null;

  const inspectedPiece: PieceState | null = useMemo(() => {
    if (!currentFrame || !effectiveInspectedPieceId) return null;
    return currentFrame.pieces.find((p) => p.piece_id === effectiveInspectedPieceId) || null;
  }, [currentFrame, effectiveInspectedPieceId]);

  const handleLoadSampleNotation = () => {
    setRawInput(SAMPLE_NOTATION_RECORD);
    runAnalysis(SAMPLE_NOTATION_RECORD);
  };

  const handleLoadSampleAiJson = () => {
    setRawInput(SAMPLE_AI_VS_AI_JSON_RECORD);
    runAnalysis(SAMPLE_AI_VS_AI_JSON_RECORD);
  };

  const handleImportActiveMatch = () => {
    if (activeMatchMoves.length === 0) return;
    const text = formatMoveRecordsForRecordInput(activeMatchMoves);
    setRawInput(text);
    runAnalysis(text);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const content = typeof reader.result === 'string' ? reader.result : '';
      setRawInput(content);
      runAnalysis(content);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleCopyNormalized = () => {
    if (!analysis || analysis.normalizedNotationLines.length === 0) return;
    navigator.clipboard.writeText(analysis.normalizedNotationLines.join('\n'));
    setCopiedNotation(true);
    setTimeout(() => setCopiedNotation(false), 2000);
  };

  const formatBadgeLabel = (fmt: string) => {
    switch (fmt) {
      case 'AI_JSON_RECORD':
        return 'AI JSON (game_records)';
      case 'AI_JSONL':
        return 'JSON Lines (.jsonl)';
      case 'SELECTED_ACTION_STREAM':
        return 'Agent Action Stream';
      case 'COTULENH_NOTATION':
        return 'COTULENH-NOTATION v1';
      default:
        return lang === 'vi' ? 'Biên bản văn bản' : 'Action Log Text';
    }
  };

  const getCompoundTagLabel = (
    tag?: CompoundEventTag | null,
    carriedCount: number = 0
  ): string | null => {
    if (!tag) return null;
    switch (tag) {
      case 'BOARD':
        return t.analysis.tagBoard;
      case 'PICKUP':
        return carriedCount > 0 ? `${t.analysis.tagPickup} (${carriedCount})` : t.analysis.tagPickup;
      case 'CARRY_MOVE':
        return carriedCount > 0
          ? `${t.analysis.tagCarrying} (${carriedCount})`
          : t.analysis.tagCarrying;
      case 'SOLO_SPLIT':
        return t.analysis.tagSoloSplit;
      case 'DEPLOY':
        return t.analysis.tagDeploy;
      case 'END_TURN':
        return t.analysis.tagEndCompound;
      default:
        return null;
    }
  };

  return (
    <div className={styles.pageContainer}>
      {/* Page Header */}
      <div className={styles.pageHeader}>
        <div>
          <h2 className={styles.pageTitle}>{t.analysis.title}</h2>
          <p className={styles.pageSubtitle}>{t.analysis.subtitle}</p>
        </div>
        <div className={styles.headerActions}>
          {activeMatchMoves.length > 0 && (
            <button
              type="button"
              className="btn btn-outline-gold"
              onClick={handleImportActiveMatch}
            >
              📥 {t.analysis.useCurrentMatch} ({activeMatchMoves.length})
            </button>
          )}
          {analysis?.success && analysis.normalizedNotationLines.length > 0 && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleCopyNormalized}
            >
              {copiedNotation
                ? `✓ ${lang === 'vi' ? 'Đã sao chép' : 'Copied'}`
                : `📋 ${t.analysis.copyCurrentNotation}`}
            </button>
          )}
        </div>
      </div>

      {/* Input / Paste Record Panel */}
      <section className={`tactical-panel ${styles.inputPanel}`}>
        <div className={styles.inputHeader}>
          <div className={styles.inputTitleGroup}>
            <span className={styles.sectionHeading}>{t.analysis.inputTitle}</span>
            <span className={styles.inputHint}>{t.analysis.inputHint}</span>
          </div>
          <div className={styles.inputTools}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleLoadSampleNotation}
            >
              📄 {t.analysis.btnLoadSampleNotation}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleLoadSampleAiJson}
            >
              🤖 {t.analysis.btnLoadSampleAiJson}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => fileInputRef.current?.click()}
            >
              📂 {t.analysis.btnUploadFile}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.jsonl,.txt,.ctn,.md,.csv"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
            {analysis?.success && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsInputCollapsed((prev) => !prev)}
              >
                {isInputCollapsed
                  ? lang === 'vi'
                    ? '▼ Mở khung dán'
                    : '▼ Expand Editor'
                  : lang === 'vi'
                  ? '▲ Thu gọn'
                  : '▲ Collapse'}
              </button>
            )}
          </div>
        </div>

        {!isInputCollapsed && (
          <>
            <textarea
              className={styles.recordTextarea}
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              placeholder={t.analysis.placeholder}
              rows={6}
              spellCheck={false}
            />
            <div className={styles.inputFooter}>
              <div className={styles.feedbackArea}>
                {analysis && !analysis.success && analysis.error && (
                  <span className={styles.errorText}>⚠️ {analysis.error}</span>
                )}
                {analysis?.warnings && analysis.warnings.length > 0 && (
                  <span className={styles.warningText}>
                    ⚠️ {t.analysis.warningsTitle} ({analysis.warnings.length}):{' '}
                    {analysis.warnings[0]}
                  </span>
                )}
              </div>
              <div className={styles.actionButtons}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setRawInput('');
                    setAnalysis(null);
                    setCurrentStep(0);
                    setIsAutoPlaying(false);
                    setInspectedPieceId(null);
                  }}
                >
                  {t.analysis.btnClear}
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => runAnalysis(rawInput)}
                >
                  ▶ {t.analysis.btnAnalyze}
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Main 3-Column Replay & Analysis Workspace */}
      {!analysis?.success || !currentFrame ? (
        <div className={`tactical-panel ${styles.emptyWorkspace}`}>
          <p>{t.analysis.emptyPrompt}</p>
        </div>
      ) : (
        <div className={styles.workspaceGrid}>
          {/* Left Column: Metadata & Replayed Move List */}
          <aside className={styles.leftCol}>
            <div className={`tactical-panel ${styles.metaCard}`}>
              <h3 className={styles.cardTitle}>{t.analysis.matchMetaTitle}</h3>
              <div className={styles.metaRows}>
                <div className={styles.metaRow}>
                  <span>{t.analysis.detectedFormat}</span>
                  <strong>{formatBadgeLabel(analysis.metadata.format)}</strong>
                </div>
                {analysis.metadata.redAgent && (
                  <div className={styles.metaRow}>
                    <span>{t.analysis.redAgent}</span>
                    <strong className={styles.textRed}>
                      {analysis.metadata.redAgent}
                      {analysis.metadata.redConfigId
                        ? ` (${analysis.metadata.redConfigId})`
                        : ''}
                    </strong>
                  </div>
                )}
                {analysis.metadata.blueAgent && (
                  <div className={styles.metaRow}>
                    <span>{t.analysis.blueAgent}</span>
                    <strong className={styles.textBlue}>
                      {analysis.metadata.blueAgent}
                      {analysis.metadata.blueConfigId
                        ? ` (${analysis.metadata.blueConfigId})`
                        : ''}
                    </strong>
                  </div>
                )}
                {analysis.metadata.winner && (
                  <div className={styles.metaRow}>
                    <span>{t.analysis.winnerLabel}</span>
                    <strong>{analysis.metadata.winner}</strong>
                  </div>
                )}
                {analysis.metadata.terminationReason && (
                  <div className={styles.metaRow}>
                    <span>{t.analysis.reasonLabel}</span>
                    <strong>{analysis.metadata.terminationReason}</strong>
                  </div>
                )}
                {analysis.metadata.seed != null && (
                  <div className={styles.metaRow}>
                    <span>{t.analysis.seedLabel}</span>
                    <strong>{analysis.metadata.seed}</strong>
                  </div>
                )}
                <div className={styles.metaRow}>
                  <span>{t.analysis.totalMovesLabel}</span>
                  <strong>{maxStep}</strong>
                </div>
              </div>
            </div>

            <div className={`tactical-panel ${styles.moveListCard}`}>
              <h3 className={styles.cardTitle}>{t.analysis.moveListTitle}</h3>
              <div className={styles.moveListScroll} ref={moveListRef}>
                <button
                  type="button"
                  data-step-index={0}
                  className={`${styles.stepRow} ${
                    currentStep === 0 ? styles.stepRowActive : ''
                  }`}
                  onClick={() => {
                    setIsAutoPlaying(false);
                    setCurrentStep(0);
                  }}
                >
                  <span className={styles.stepNum}>0</span>
                  <span className={styles.stepText}>{t.analysis.initialBoardLabel}</span>
                </button>

                {frames.slice(1).map((fr) => {
                  const mv = fr.lastMove;
                  const isActive = currentStep === fr.stepIndex;
                  const isRed = mv?.side === 'RED';
                  const compoundLabel = getCompoundTagLabel(
                    fr.compoundEventTag,
                    fr.carriedCount
                  );
                  return (
                    <button
                      key={`step-${fr.stepIndex}`}
                      type="button"
                      data-step-index={fr.stepIndex}
                      className={`${styles.stepRow} ${
                        isActive ? styles.stepRowActive : ''
                      }`}
                      onClick={() => {
                        setIsAutoPlaying(false);
                        setCurrentStep(fr.stepIndex);
                      }}
                    >
                      <span className={styles.stepNum}>{fr.stepIndex}.</span>
                      <span className={isRed ? styles.sidePillRed : styles.sidePillBlue}>
                        {isRed
                          ? lang === 'vi'
                            ? 'Đỏ'
                            : 'Red'
                          : lang === 'vi'
                          ? 'Xanh'
                          : 'Blue'}
                      </span>
                      <span className={styles.stepText}>
                        {mv?.notation || '—'}
                      </span>
                      {compoundLabel && (
                        <span className={styles.stepCompoundTag}>{compoundLabel}</span>
                      )}
                      {fr.telemetry?.heuristicScore != null && (
                        <span className={styles.stepScoreTag}>
                          {fr.telemetry.heuristicScore.toFixed(1)}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </aside>

          {/* Center Column: Board + Step Controls (Đầu / Lùi / Tiến / Cuối) */}
          <section className={styles.centerCol}>
            <Board
              pieces={currentFrame.pieces}
              selectedPieceId={inspectedPieceId}
              onSelectPiece={(p) =>
                setInspectedPieceId((prev) => (prev === p.piece_id ? null : p.piece_id))
              }
              lastMove={currentFrame.lastMove}
              activeCompound={currentFrame.activeCompound}
              flipped={flipped}
              readOnly={true}
              lang={lang}
            />

            {/* Compound unit inspector outside board */}
            <CompoundControlBar
              pieces={currentFrame.pieces}
              selectedPieceId={effectiveInspectedPieceId}
              activeCompound={currentFrame.activeCompound}
              onSelectPiece={(p) => setInspectedPieceId(p.piece_id)}
              lang={lang}
              readOnly={true}
            />

            {/* Playback & Đầu / Lùi / Tiến / Cuối Controls */}
            <div className={`tactical-panel ${styles.playbackBar}`}>
              <input
                type="range"
                min={0}
                max={maxStep}
                value={currentStep}
                onChange={(e) => {
                  setIsAutoPlaying(false);
                  setCurrentStep(Number(e.target.value));
                }}
                className={styles.stepSlider}
              />

              <div className={styles.playbackButtonsRow}>
                <div className={styles.navButtonsGroup}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={currentStep <= 0}
                    onClick={() => {
                      setIsAutoPlaying(false);
                      setCurrentStep(0);
                    }}
                  >
                    ⏮ {t.game.navFirst}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={currentStep <= 0}
                    onClick={() => {
                      setIsAutoPlaying(false);
                      setCurrentStep((prev) => Math.max(0, prev - 1));
                    }}
                  >
                    ◀ {t.game.navPrev}
                  </button>
                  <span className={styles.stepCounterPill}>
                    {t.game.stepLabel} {currentStep} / {maxStep}
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={currentStep >= maxStep}
                    onClick={() => {
                      setIsAutoPlaying(false);
                      setCurrentStep((prev) => Math.min(maxStep, prev + 1));
                    }}
                  >
                    {t.game.navNext} ▶
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={currentStep >= maxStep}
                    onClick={() => {
                      setIsAutoPlaying(false);
                      setCurrentStep(maxStep);
                    }}
                  >
                    {t.game.navLast} ⏭
                  </button>
                </div>

                <div className={styles.extraControlsGroup}>
                  <button
                    type="button"
                    className={`btn ${isAutoPlaying ? 'btn-primary' : 'btn-outline-gold'}`}
                    onClick={() => {
                      if (!isAutoPlaying && currentStep >= maxStep) {
                        setCurrentStep(0);
                      }
                      setIsAutoPlaying((prev) => !prev);
                    }}
                  >
                    {isAutoPlaying ? `⏸ ${t.analysis.btnPause}` : `▶ ${t.analysis.btnAutoPlay}`}
                  </button>

                  <select
                    aria-label={t.analysis.speedLabel}
                    className={styles.speedSelect}
                    value={playSpeedMs}
                    onChange={(e) => setPlaySpeedMs(Number(e.target.value))}
                  >
                    <option value={1600}>0.5x</option>
                    <option value={900}>1x</option>
                    <option value={450}>2x</option>
                    <option value={220}>4x</option>
                  </select>

                  <button
                    type="button"
                    className={`btn btn-secondary ${flipped ? styles.flipBtnActive : ''}`}
                    onClick={() => setFlipped((prev) => !prev)}
                  >
                    🔄 {t.game.flipBoard}
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* Right Column: Scores, AI Telemetry, PieceDetail & Casualties */}
          <aside className={styles.rightCol}>
            {/* Frame Score & Turn */}
            <div className={`tactical-panel ${styles.scoreCard}`}>
              <div className={styles.scorePair}>
                <div className={styles.scoreSide}>
                  <span className={styles.textRed}>{t.game.redSide}</span>
                  <strong className={styles.scoreBig}>{currentFrame.scores.RED}</strong>
                </div>
                <span className={styles.scoreVs}>vs</span>
                <div className={styles.scoreSide}>
                  <span className={styles.textBlue}>{t.game.blueSide}</span>
                  <strong className={styles.scoreBig}>{currentFrame.scores.BLUE}</strong>
                </div>
              </div>
              <div className={styles.turnLine}>
                <span>
                  {t.game.turn}:{' '}
                  <strong
                    className={
                      currentFrame.sideToMove === 'RED' ? styles.textRed : styles.textBlue
                    }
                  >
                    {currentFrame.sideToMove === 'RED'
                      ? t.game.redSide
                      : t.game.blueSide}
                  </strong>
                </span>
                <span className="badge">
                  T{currentFrame.turnNumber}
                </span>
              </div>
              {currentFrame.activeCompound && (
                <div className={styles.compoundStatusRow}>
                  <span className={styles.compoundStatusBadge}>
                    ⚡ {t.analysis.compoundActiveBadge} ({currentFrame.activeCompound.actionCount}/3)
                  </span>
                </div>
              )}
            </div>

            {/* AI Decision Telemetry Inspector */}
            <div className={`tactical-panel ${styles.telemetryCard}`}>
              <h3 className={styles.cardTitle}>{t.analysis.telemetryTitle}</h3>
              {!currentFrame.telemetry ? (
                <p className={styles.emptyTelemetry}>{t.analysis.noTelemetry}</p>
              ) : (
                <div className={styles.telemetryBody}>
                  {currentFrame.telemetry.agentName && (
                    <div className={styles.teleRow}>
                      <span>Agent</span>
                      <strong>
                        {currentFrame.telemetry.agentName}
                        {currentFrame.telemetry.agentConfigId
                          ? ` (${currentFrame.telemetry.agentConfigId})`
                          : ''}
                      </strong>
                    </div>
                  )}
                  {currentFrame.telemetry.ruleTriggered && (
                    <div className={styles.teleRow}>
                      <span>{t.analysis.ruleTriggered}</span>
                      <strong className={styles.teleHighlight}>
                        {currentFrame.telemetry.ruleTriggered}
                      </strong>
                    </div>
                  )}
                  {currentFrame.telemetry.heuristicScore != null && (
                    <div className={styles.teleRow}>
                      <span>{t.analysis.heuristicScore}</span>
                      <strong className={styles.teleHighlight}>
                        {currentFrame.telemetry.heuristicScore.toFixed(2)}
                      </strong>
                    </div>
                  )}
                  {currentFrame.telemetry.decisionTimeMs != null && (
                    <div className={styles.teleRow}>
                      <span>{t.analysis.decisionTime}</span>
                      <strong>{currentFrame.telemetry.decisionTimeMs.toFixed(2)} ms</strong>
                    </div>
                  )}
                  {currentFrame.telemetry.nodesVisited != null && (
                    <div className={styles.teleRow}>
                      <span>{t.analysis.nodesVisited}</span>
                      <strong>{currentFrame.telemetry.nodesVisited}</strong>
                    </div>
                  )}
                  {currentFrame.telemetry.simulations != null && (
                    <div className={styles.teleRow}>
                      <span>{t.analysis.simulations}</span>
                      <strong>{currentFrame.telemetry.simulations}</strong>
                    </div>
                  )}
                  {currentFrame.telemetry.selectedAction && (
                    <div className={styles.teleRawBox}>
                      <span className={styles.teleRawLabel}>
                        {t.analysis.selectedActionRaw}:
                      </span>
                      <code className={styles.teleRawCode}>
                        {currentFrame.telemetry.selectedAction}
                      </code>
                    </div>
                  )}
                  {currentFrame.telemetry.heuristicComponents &&
                    Object.keys(currentFrame.telemetry.heuristicComponents).length > 0 && (
                      <div className={styles.teleBreakdown}>
                        <span className={styles.teleRawLabel}>
                          {t.analysis.heuristicBreakdown}:
                        </span>
                        <div className={styles.componentsGrid}>
                          {Object.entries(currentFrame.telemetry.heuristicComponents).map(
                            ([k, v]) => (
                              <div key={k} className={styles.componentRow}>
                                <span>{k}</span>
                                <strong>{Number(v).toFixed(2)}</strong>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}
                </div>
              )}
            </div>

            <PieceDetail
              piece={inspectedPiece}
              allPieces={currentFrame.pieces}
              onSelectPiece={(p) => setInspectedPieceId(p.piece_id)}
              movedPieceIds={currentFrame.activeCompound?.movedPieceIds || []}
              lang={lang}
              readOnly={true}
            />

            <CapturedPieces capturedPieces={currentFrame.capturedPieces} lang={lang} />
          </aside>
        </div>
      )}
    </div>
  );
};

