import React, { useState, useEffect, useMemo } from 'react';
import { Header } from './components/Header/Header';
import { Home } from './components/Home/Home';
import { Board } from './components/Board/Board';
import { PieceDetail } from './components/PieceDetail/PieceDetail';
import { MoveHistory } from './components/MoveHistory/MoveHistory';
import { CapturedPieces } from './components/CapturedPieces/CapturedPieces';
import { PieceState, Side, LegalAction, MoveRecord } from './types';
import { getInitialPieces } from './utils/initialBoard';
import { getMockLegalActions, applyMockAction } from './services/mockGameService';
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
  const [pieces, setPieces] = useState<PieceState[]>(() => getInitialPieces());
  const [selectedPieceId, setSelectedPieceId] = useState<string | null>(null);
  const [sideToMove, setSideToMove] = useState<Side>('RED');
  const [scores, setScores] = useState<{ RED: number; BLUE: number }>({ RED: 0, BLUE: 0 });
  const [moves, setMoves] = useState<MoveRecord[]>([]);
  const [capturedPieces, setCapturedPieces] = useState<PieceState[]>([]);

  const t = translations[lang];

  useEffect(() => {
    localStorage.setItem('commander_chess_lang', lang);
  }, [lang]);

  const selectedPiece = pieces.find((p) => p.piece_id === selectedPieceId) || null;

  // Calculate legal actions for currently selected piece of active side
  const legalActions = useMemo(() => {
    if (!selectedPiece || selectedPiece.side !== sideToMove) return [];
    return getMockLegalActions(selectedPiece, pieces);
  }, [selectedPiece, sideToMove, pieces]);

  const handleSelectPiece = (piece: PieceState) => {
    if (selectedPieceId === piece.piece_id) {
      setSelectedPieceId(null);
    } else {
      setSelectedPieceId(piece.piece_id);
    }
  };

  const handleExecuteAction = (action: LegalAction) => {
    const { nextPieces, event, capturedPiece } = applyMockAction(action, pieces);
    setPieces(nextPieces);

    if (capturedPiece) {
      setCapturedPieces((prev) => [...prev, capturedPiece]);
    }

    if (event.score_delta.RED > 0 || event.score_delta.BLUE > 0) {
      setScores((prev) => ({
        RED: prev.RED + event.score_delta.RED,
        BLUE: prev.BLUE + event.score_delta.BLUE,
      }));
    }

    const newRecord: MoveRecord = {
      move_number: moves.length + 1,
      side: sideToMove,
      action,
      notation: action.notation,
      captured_piece_type: capturedPiece ? capturedPiece.type : null,
      timestamp: Date.now(),
    };
    setMoves((prev) => [...prev, newRecord]);

    setSelectedPieceId(null);
    setSideToMove((prev) => (prev === 'RED' ? 'BLUE' : 'RED'));
  };

  const handleResetBoard = () => {
    setPieces(getInitialPieces());
    setSelectedPieceId(null);
    setSideToMove('RED');
    setScores({ RED: 0, BLUE: 0 });
    setMoves([]);
    setCapturedPieces([]);
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
          <Home lang={lang} onNavigate={setActiveTab} />
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
              />
            </section>

            {/* Right Sidebar Control & Info Panel */}
            <aside className={styles.sidebar}>
              {/* Match Status Card */}
              <div className={`tactical-panel ${styles.statusCard}`}>
                <div className={styles.statusHeader}>
                  <span className={styles.statusTitle}>{t.game.status}</span>
                  <span className="badge">Active Session</span>
                </div>

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
                      {sideToMove === 'RED' ? t.game.redSide : t.game.blueSide}
                    </strong>
                  </span>
                </div>

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

                {/* Controls */}
                <div className={styles.controls}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                    onClick={handleResetBoard}
                  >
                    {t.game.newGame}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setSideToMove(sideToMove === 'RED' ? 'BLUE' : 'RED')}
                    title="Chuyển lượt thử nghiệm"
                  >
                    {t.game.swapTurn}
                  </button>
                </div>
              </div>

              {/* Tactical Piece Detail Panel */}
              <PieceDetail piece={selectedPiece} lang={lang} />

              {/* Captured Pieces Tracker */}
              <CapturedPieces capturedPieces={capturedPieces} lang={lang} />
            </aside>
          </div>
        )}

        {/* TAB 3: RULES & TACTICS GUIDE */}
        {activeTab === 'rules' && (
          <div className={styles.rulesContainer}>
            <div className={styles.rulesHeader}>
              <h2 className={styles.rulesTitle}>
                {lang === 'vi' ? 'Cẩm Nang Luật Chơi Cờ Tư Lệnh' : 'Commander Chess Rules & Tactics'}
              </h2>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setActiveTab('play')}
              >
                {t.home.btnPlayNow} →
              </button>
            </div>

            <div className={styles.rulesGrid}>
              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>◈</span>
                  {lang === 'vi' ? '1. Địa hình & Bàn cờ' : '1. Terrain & Board'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Bàn cờ gồm 11 đường dọc (X: 0..10) và 12 đường ngang (Y: 0..11), tổng cộng 132 giao điểm.'
                      : 'Board features 11 vertical (X: 0..10) and 12 horizontal lines (Y: 0..11), 132 intersections.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Dải biển nằm ở hai cột ngoài cùng bên trái (X: 0, 1) dành riêng cho Hải quân và Không quân di chuyển.'
                      : 'Sea zone spans columns X: 0, 1 reserved for Navy ships and Aircraft.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Sông chia đôi bàn cờ giữa hàng Y: 5 và Y: 6. Chỉ bộ binh bơi hoặc công binh bắc cầu mới vượt được sông.'
                      : 'River bisects rows Y: 5 and Y: 6. Only swimming infantry or combat engineer bridges cross.'}
                  </li>
                </ul>
              </div>

              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>◈</span>
                  {lang === 'vi' ? '2. Lực lượng Tổng Lực' : '2. Total Force Order of Battle'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Mỗi bên sở hữu 19 quân gồm 11 chủng loại: Tư lệnh, Xe tăng, Pháo binh, Tên lửa, Cao xạ, Không quân, Hải quân, Dân quân, Bộ binh, Công binh, Sở chỉ huy.'
                      : 'Each side fields 19 pieces across 11 piece classes: Commander, Tank, Artillery, Missile, Anti-Air, Aircraft, Navy, Militia, Infantry, Engineer, Headquarters.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Mục tiêu tối thượng của ván cờ là bảo vệ Tư lệnh phe mình và bắt/tiêu diệt Tư lệnh đối phương.'
                      : 'Primary objective is securing your Commander while neutralizing the enemy Commander.'}
                  </li>
                </ul>
              </div>

              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>◈</span>
                  {lang === 'vi' ? '3. Hành quân & Cõng quân' : '3. Mechanized Transport & Stacking'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Xe tăng có thể chở tối đa 2 bộ binh di chuyển tốc độ cao trên đất liền.'
                      : 'Tanks can transport up to 2 infantry units across land at mechanized speed.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Tàu chiến có thể chở tối đa 1 máy bay hoặc bộ binh trên tuyến hải trình.'
                      : 'Navy warships can carry up to 1 aircraft or infantry unit along sea lanes.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Hành động phối hợp (lên xe, di chuyển, xuống xe) được thực hiện trọn vẹn trong một lượt tác chiến.'
                      : 'Coordinated stacking actions (mount, move, dismount) execute smoothly within one turn.'}
                  </li>
                </ul>
              </div>

              <div className={styles.rulesCard}>
                <h3 className={styles.rulesCardTitle}>
                  <span>◈</span>
                  {lang === 'vi' ? '4. Vành đai lửa Phòng không' : '4. Anti-Air Fire Umbrella'}
                </h3>
                <ul className={styles.rulesList}>
                  <li>
                    {lang === 'vi'
                      ? 'Cao xạ (tầm 2) và Tên lửa (tầm 3) tự động tạo vùng cấm bay bảo vệ lực lượng mặt đất.'
                      : 'Anti-Air (range 2) and Missiles (range 3) project passive air defense umbrellas.'}
                  </li>
                  <li>
                    {lang === 'vi'
                      ? 'Máy bay bay qua hoặc tấn công trong tầm phòng không sẽ bị tiêu diệt theo nguyên tắc đổi quân quyết liệt.'
                      : 'Aircraft operating within anti-air envelopes trigger mutual destruction attrition.'}
                  </li>
                </ul>
              </div>
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

      <footer className={styles.footer}>
        <p>
          Commander Chess AI Platform — Saigon University (2026) | Advanced Artificial Intelligence
        </p>
      </footer>
    </>
  );
};

