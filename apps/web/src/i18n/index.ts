export type Language = 'vi' | 'en';

export interface Translations {
  appName: string;
  appSubtitle: string;
  nav: {
    home: string;
    play: string;
    aiVsAi: string;
    replays: string;
    stats: string;
    rules: string;
  };
  home: {
    heroBadge: string;
    heroTitle: string;
    heroSubtitle: string;
    heroDesc: string;
    btnPlayNow: string;
    btnViewRules: string;
    modesTitle: string;
    playAiTitle: string;
    playAiDesc: string;
    playHumanTitle: string;
    playHumanDesc: string;
    aiVsAiTitle: string;
    aiVsAiDesc: string;
    analysisTitle: string;
    analysisDesc: string;
    rulesTitle: string;
    rulesDesc: string;
    statusReady: string;
    statusDev: string;
    pillarsTitle: string;
    pillar1Title: string;
    pillar1Desc: string;
    pillar2Title: string;
    pillar2Desc: string;
    pillar3Title: string;
    pillar3Desc: string;
  };
  game: {
    turn: string;
    redSide: string;
    blueSide: string;
    selectedPiece: string;
    noPieceSelected: string;
    coordinates: string;
    score: string;
    status: string;
    inProgress: string;
    gameOver: string;
    newGame: string;
    resign: string;
    drawOffer: string;
    backToHome: string;
    swapTurn: string;
    timer: string;
    activeSession: string;
    btnReviewBoard: string;
    btnReopenModal: string;
    confirmNewGameTitle: string;
    confirmNewGameDesc: string;
    confirmResignTitle: string;
    confirmResignDesc: string;
    confirmDrawTitle: string;
    confirmDrawDesc: string;
    confirmYes: string;
    confirmCancel: string;
    victoryRed: string;
    victoryBlue: string;
    drawMatch: string;
    reasonCheckmate: string;
    reasonStalemate: string;
    reasonCommanderCaptured: string;
    reasonResignation: string;
    reasonDraw: string;
    totalTurns: string;
    totalMoves: string;
    finalScore: string;
    duration: string;
    capturedCommanderTitle: string;
    backendOnline: string;
    backendOffline: string;
    aiThinking: string;
    aiMoveBtn: string;
    modeHumanVsAi: string;
    modeHumanVsHuman: string;
    modeAiVsAi: string;
    modeLabel: string;
    aiBotName: string;
    selectOpponent: string;
    redAgentLabel: string;
    blueAgentLabel: string;
    agentRuleBased: string;
    agentHeuristic: string;
    agentRandom: string;
    agentMinimax: string;
    btnStartMatch: string;
    btnPauseMatch: string;
    btnResumeMatch: string;
    btnStepMatch: string;
    speedLabel: string;
    btnCopyLog: string;
    btnAnalyzeMatch: string;
    copySuccessToast: string;
    aiTimeLimitLabel: string;
    aiTimeLimitUnlimited: string;
    humanNoTimeLimit: string;
    navFirst: string;
    navPrev: string;
    navNext: string;
    navLast: string;
    reviewingHistoryBanner: string;
    returnToLiveBtn: string;
    flipBoard: string;
    stepLabel: string;
  };
  analysis: {
    title: string;
    subtitle: string;
    inputTitle: string;
    inputHint: string;
    placeholder: string;
    btnAnalyze: string;
    btnClear: string;
    btnUploadFile: string;
    btnLoadSampleNotation: string;
    btnLoadSampleAiJson: string;
    btnAutoPlay: string;
    btnPause: string;
    speedLabel: string;
    matchMetaTitle: string;
    detectedFormat: string;
    redAgent: string;
    blueAgent: string;
    winnerLabel: string;
    reasonLabel: string;
    seedLabel: string;
    totalMovesLabel: string;
    telemetryTitle: string;
    noTelemetry: string;
    ruleTriggered: string;
    heuristicScore: string;
    decisionTime: string;
    nodesVisited: string;
    searchDepth: string;
    nodesPerSecond: string;
    simulations: string;
    selectedActionRaw: string;
    heuristicBreakdown: string;
    moveListTitle: string;
    initialBoardLabel: string;
    emptyPrompt: string;
    warningsTitle: string;
    copyCurrentNotation: string;
    useCurrentMatch: string;
    tagBoard: string;
    tagPickup: string;
    tagCarrying: string;
    tagSoloSplit: string;
    tagDeploy: string;
    tagEndCompound: string;
    compoundActiveBadge: string;
  };
  stats: {
    title: string;
    subtitle: string;
    filterAll: string;
    filterExp07: string;
    filterExp08: string;
    filterExp09: string;
    filterExp10: string;
    totalMatchesLabel: string;
    totalMatchesValue: string;
    maxWinRateLabel: string;
    bestAgentLabel: string;
    testSeedsLabel: string;
    hardwareTitle: string;
    hardwareDesc: string;
    btnZoom: string;
    closeModal: string;
    exp07Title: string;
    exp07Desc: string;
    exp08Title: string;
    exp08Desc: string;
    exp09Title: string;
    exp09Desc: string;
    exp10Title: string;
    exp10Desc: string;
  };
  pieces: Record<string, string>;
}

export const translations: Record<Language, Translations> = {
  vi: {
    appName: 'Cờ Tư Lệnh AI',
    appSubtitle: 'Nền tảng thi đấu & nghiên cứu AI Cờ Tư Lệnh',
    nav: {
      home: 'Trang chủ',
      play: 'Bàn cờ',
      aiVsAi: 'AI vs AI',
      replays: 'Phân tích ván',
      stats: 'Thống kê',
      rules: 'Luật chơi',
    },
    home: {
      heroBadge: 'CHIẾN TRANH TỔNG LỰC — CHIẾN THUẬT HIỆN ĐẠI',
      heroTitle: 'CỜ TƯ LỆNH',
      heroSubtitle: 'Trò chơi cờ quân sự hiện đại của Việt Nam',
      heroDesc:
        'Kết hợp tác chiến 3 quân chủng Lục quân — Hải quân — Không quân trên bàn cờ 132 giao điểm. Nền tảng phát triển, thi đấu và thực nghiệm các tác tử trí tuệ nhân tạo.',
      btnPlayNow: 'Vào bàn cờ ngay',
      btnViewRules: 'Xem luật chơi',
      modesTitle: 'LỰA CHỌN PHƯƠNG THỨC TÁC CHIẾN',
      playAiTitle: 'Chơi với AI',
      playAiDesc: 'Thử thách tư duy chiến lược cùng các tác tử AI được xây dựng theo nhiều cấp độ.',
      playHumanTitle: 'Người đấu Người',
      playHumanDesc: 'Thi đấu trực tiếp hai người trên cùng một thiết bị với đầy đủ 38 quân cờ.',
      aiVsAiTitle: 'AI đấu với AI',
      aiVsAiDesc: 'Quan sát các trận đấu tự động giữa hai tác tử AI để đánh giá và thu thập dữ liệu nghiên cứu.',
      analysisTitle: 'Game Analysis Record',
      analysisDesc: 'Dán biên bản ván đấu hoặc log JSON của AI vs AI để phát lại từng nước đi và phân tích quyết định.',
      rulesTitle: 'Luật chơi & Cẩm nang',
      rulesDesc: 'Tra cứu quy định vượt sông, vùng biển, hành quân cõng quân và vành đai phòng không.',
      statusReady: 'Sẵn sàng',
      statusDev: 'Đang phát triển',
      pillarsTitle: 'ĐẶC TRƯNG CHIẾN THUẬT CỐT LÕI',
      pillar1Title: 'Tác chiến 3 Quân chủng',
      pillar1Desc: 'Phối hợp nhịp nhàng giữa Lục quân, Hải quân và Không quân để bảo vệ Tư lệnh và công phá đối phương.',
      pillar2Title: 'Hành quân thần tốc',
      pillar2Desc: 'Xe tăng chở bộ binh, Tàu chiến chở máy bay, Công binh bắc cầu qua sông sâu với tối đa 3 hành động trong một lượt.',
      pillar3Title: 'Vành đai lửa phòng không',
      pillar3Desc: 'Hệ thống cao xạ và tên lửa thiết lập vùng cấm bay, tạo thế 1 đổi 1 quyết liệt khi máy bay địch xâm nhập.',
    },
    game: {
      turn: 'Lượt đi',
      redSide: 'Phe Đỏ',
      blueSide: 'Phe Xanh',
      selectedPiece: 'Quân đang chọn',
      noPieceSelected: 'Nhấp chọn một quân trên bàn cờ để xem chi tiết chiến thuật',
      coordinates: 'Tọa độ',
      score: 'Điểm số',
      status: 'Trạng thái',
      inProgress: 'Đang diễn ra',
      gameOver: 'Trận đấu kết thúc',
      newGame: 'Ván mới',
      resign: 'Đầu hàng',
      drawOffer: 'Cầu hòa',
      backToHome: 'Trang chủ',
      swapTurn: 'Đổi lượt',
      timer: 'Thời gian',
      activeSession: 'Đang tác chiến',
      btnReviewBoard: 'Quan sát thế cờ',
      btnReopenModal: 'Xem kết quả',
      confirmNewGameTitle: 'Khởi tạo ván mới?',
      confirmNewGameDesc: 'Trận đánh hiện tại chưa kết thúc. Khởi tạo ván mới sẽ xóa toàn bộ tiến trình và biên bản hiện tại.',
      confirmResignTitle: 'Xác nhận đầu hàng?',
      confirmResignDesc: 'Bạn có chắc chắn muốn đầu hàng? Phe đối phương sẽ được tuyên bố chiến thắng ngay lập tức.',
      confirmDrawTitle: 'Đề nghị hòa chiến?',
      confirmDrawDesc: 'Bạn có chắc muốn đề nghị hòa? Hai bên sẽ kết thúc trận đấu với kết quả hòa đồng thuận.',
      confirmYes: 'Xác nhận',
      confirmCancel: 'Hủy bỏ',
      victoryRed: 'PHE ĐỎ TOÀN THẮNG!',
      victoryBlue: 'PHE XANH TOÀN THẮNG!',
      drawMatch: 'TRẬN ĐẤU BẤT PHÂN THẮNG BẠI',
      reasonCheckmate: 'Chiếu hết Tư lệnh đối phương (+50 điểm)',
      reasonStalemate: 'Hòa cờ bí (Stalemate): bên đi kế tiếp hết nước đi hợp lệ nhưng không bị chiếu',
      reasonCommanderCaptured: 'Tư lệnh đối phương đã bị bắt giữ (+50 điểm)',
      reasonResignation: 'Đối phương đã chủ động đầu hàng',
      reasonDraw: 'Hai bên đồng thuận đình chiến hòa bình',
      totalTurns: 'Tổng số hiệp',
      totalMoves: 'Tổng số nước đi',
      finalScore: 'Điểm số chung cuộc',
      duration: 'Thời gian tác chiến',
      capturedCommanderTitle: 'TƯ LỆNH BỊ BẮT GIỮ',
      backendOnline: 'API Trực tuyến (FastAPI)',
      backendOffline: 'Ngoại tuyến (Local Engine)',
      aiThinking: '🤖 AI đang suy nghĩ...',
      aiMoveBtn: '🤖 AI đi hộ',
      modeHumanVsAi: 'Người vs AI',
      modeHumanVsHuman: 'Hai người chơi',
      modeAiVsAi: 'AI đối đầu AI (Khán đài)',
      modeLabel: 'Chế độ đối kháng',
      aiBotName: 'Tác tử AI',
      selectOpponent: 'Chọn Tác Tử Đối Thủ:',
      redAgentLabel: 'Tác tử phe Đỏ:',
      blueAgentLabel: 'Tác tử phe Xanh:',
      agentRuleBased: 'RULE-BASE AGENT',
      agentHeuristic: 'HEURISTIC_AGENT',
      agentRandom: 'RANDOM AGENT',
      agentMinimax: 'MINIMAX AGENT (depth=2)',
      btnStartMatch: '▶ Bắt đầu trận',
      btnPauseMatch: '⏸ Tạm dừng',
      btnResumeMatch: '▶ Tiếp tục',
      btnStepMatch: '⏭ Đi 1 bước',
      speedLabel: 'Tốc độ:',
      btnCopyLog: '📋 Sao chép biên bản',
      btnAnalyzeMatch: '📊 Phân tích trận này →',
      copySuccessToast: 'Đã sao chép biên bản trận đấu!',
      aiTimeLimitLabel: 'Giới hạn suy nghĩ AI:',
      aiTimeLimitUnlimited: 'Không giới hạn',
      humanNoTimeLimit: 'Người chơi & AI: Không giới hạn thời gian',
      navFirst: 'Đầu',
      navPrev: 'Lùi',
      navNext: 'Tiến',
      navLast: 'Cuối',
      reviewingHistoryBanner: 'Đang xem lại lịch sử ván đấu — nhấn "Cuối" để quay lại bàn cờ trực tiếp',
      returnToLiveBtn: 'Quay lại trực tiếp (Cuối)',
      flipBoard: 'Xoay bàn cờ',
      stepLabel: 'Bước',
    },
    analysis: {
      title: 'Game Analysis Record',
      subtitle: 'Dán biên bản bàn cờ (MoveHistory / COTULENH-NOTATION) hoặc JSON log trận AI vs AI (game_records/*.json) để phát lại và phân tích từng nước đi.',
      inputTitle: 'Nạp biên bản / Log trận đấu',
      inputHint: 'Hỗ trợ: JSON log từ research (game_XXXX.json), chuỗi selected_action (MOVE:... / CMD:END_TURN), biên bản sao chép từ Bàn cờ, hoặc định dạng COTULENH-NOTATION.',
      placeholder: 'Dán biên bản nước đi hoặc nội dung file game_0001.json vào đây...',
      btnAnalyze: 'Phân tích & Phát lại',
      btnClear: 'Xóa',
      btnUploadFile: 'Tải tệp (.json/.txt/.ctn)',
      btnLoadSampleNotation: 'Nạp mẫu biên bản chữ',
      btnLoadSampleAiJson: 'Nạp mẫu log AI vs AI (JSON)',
      btnAutoPlay: 'Tự động phát',
      btnPause: 'Tạm dừng',
      speedLabel: 'Tốc độ',
      matchMetaTitle: 'Thông tin trận đấu',
      detectedFormat: 'Định dạng nhận diện',
      redAgent: 'Phe Đỏ',
      blueAgent: 'Phe Xanh',
      winnerLabel: 'Kết quả',
      reasonLabel: 'Lý do kết thúc',
      seedLabel: 'Seed',
      totalMovesLabel: 'Số bước hợp lệ',
      telemetryTitle: 'Chi tiết quyết định AI tại bước đang xem',
      noTelemetry: 'Bước này không có thông số telemetry AI (biên bản ký pháp thuần hoặc trạng thái xuất phát).',
      ruleTriggered: 'Luật kích hoạt',
      heuristicScore: 'Điểm Heuristic',
      decisionTime: 'Thời gian nghĩ',
      nodesVisited: 'Số nút duyệt',
      searchDepth: 'Độ sâu tìm kiếm',
      nodesPerSecond: 'Tốc độ duyệt',
      simulations: 'Số mô phỏng',
      selectedActionRaw: 'Hành động gốc',
      heuristicBreakdown: 'Thành phần Heuristic',
      moveListTitle: 'Danh sách nước đi phân tích',
      initialBoardLabel: 'Trạng thái xuất phát (0)',
      emptyPrompt: 'Chưa có dữ liệu phân tích. Dán biên bản hoặc nạp mẫu thử ở trên rồi bấm "Phân tích & Phát lại".',
      warningsTitle: 'Lưu ý phân tích',
      copyCurrentNotation: 'Sao chép biên bản đã chuẩn hóa',
      useCurrentMatch: 'Nạp từ ván đang đánh',
      tagBoard: 'Lên xe',
      tagPickup: 'Đón quân',
      tagCarrying: 'Cõng',
      tagSoloSplit: 'Tách lẻ',
      tagDeploy: 'Triển khai',
      tagEndCompound: 'Chốt tổ hợp',
      compoundActiveBadge: 'Đang mở lượt tổ hợp',
    },
    stats: {
      title: 'Báo Cáo Thống Kê & Thực Nghiệm AI',
      subtitle: 'Tổng hợp định lượng kết quả đối đầu giải đấu, ma trận điểm số, kiểm định thống kê và trực quan hóa cây tìm kiếm qua 4 bài thực nghiệm chuẩn.',
      filterAll: 'Tất cả thực nghiệm',
      filterExp07: 'Bài 07: Random Baseline',
      filterExp08: 'Bài 08: Rule-Based Agent',
      filterExp09: 'Bài 09: Heuristic CCHEF (H1–H7)',
      filterExp10: 'Bài 10: Minimax & Cây duyệt',
      totalMatchesLabel: 'Tổng ván đấu thực nghiệm',
      totalMatchesValue: '3.080+ ván',
      maxWinRateLabel: 'Tỷ lệ thắng cao nhất (H6/MM)',
      bestAgentLabel: 'Hàm tốt nhất: CCHEF H6',
      testSeedsLabel: 'Bộ hạt giống chuẩn cố định',
      hardwareTitle: 'Môi trường thực nghiệm chuẩn hóa',
      hardwareDesc: '16 Cores CPU, 16GB RAM, Windows 11, Python 3.10, 10 Seeds cố định, max_turns = 200.',
      btnZoom: '🔍 Phóng to biểu đồ',
      closeModal: 'Đóng',
      exp07Title: 'Thực nghiệm 07 — Tác tử Ngẫu nhiên (RandomAgent Baseline)',
      exp07Desc: 'Kiểm định phân phối đồng đều nước đi (Chi-Square Test), tính đối xứng của Game Engine qua 400 ván đấu và độ trễ ra quyết định siêu tốc.',
      exp08Title: 'Thực nghiệm 08 — Tác tử Dựa trên Luật (Rule-based Agent)',
      exp08Desc: 'Giải đấu 1.280 ván giữa Ruleset_A (ưu tiên giải chiếu) và Ruleset_B (ưu tiên ăn quân) đối đầu Random và đối đầu trực tiếp (Ablation Check Safety).',
      exp09Title: 'Thực nghiệm 09 — Thiết kế, Tối ưu & Đánh giá Hàm Heuristic CCHEF',
      exp09Desc: 'Giải đấu vòng tròn Round-Robin 1.200 ván giữa 7 biến thể H1 -> H7 kết hợp Coarse-to-Fine Grid Search tìm bộ trọng số tối ưu toàn diện.',
      exp10Title: 'Thực nghiệm 10 — Tác tử Minimax & Khảo sát Cây Tìm Kiếm Đối Kháng',
      exp10Desc: 'Trực quan hóa cây tìm kiếm Minimax thực tế độ sâu d=2 với cắt tỉa Alpha-Beta, Candidate Pruning k=20 và hàm lượng giá lá CCHEF H6.',
    },
    pieces: {
      COMMANDER: 'Tư lệnh',
      INFANTRY: 'Bộ binh',
      TANK: 'Xe tăng',
      MILITIA: 'Dân quân',
      ENGINEER: 'Công binh',
      ARTILLERY: 'Pháo binh',
      ANTI_AIR: 'Cao xạ',
      MISSILE: 'Tên lửa',
      AIRCRAFT: 'Không quân',
      NAVY: 'Tàu chiến',
      HEADQUARTERS: 'Sở chỉ huy',
    },
  },
  en: {
    appName: 'Commander Chess AI',
    appSubtitle: 'AI Research & Commander Chess Platform',
    nav: {
      home: 'Home',
      play: 'Board',
      aiVsAi: 'AI vs AI',
      replays: 'Game Analysis',
      stats: 'Statistics',
      rules: 'Rules',
    },
    home: {
      heroBadge: 'TOTAL FORCE — MODERN MILITARY STRATEGY',
      heroTitle: 'COMMANDER CHESS',
      heroSubtitle: 'Modern Vietnamese Military Board Game',
      heroDesc:
        'Combining Land, Naval, and Air warfare across 132 intersections. A rigorous platform for gameplay, artificial intelligence research, and agent evaluation.',
      btnPlayNow: 'Enter Board Now',
      btnViewRules: 'Read Rules',
      modesTitle: 'OPERATIONAL COMMAND MODES',
      playAiTitle: 'Play vs AI',
      playAiDesc: 'Challenge your tactical decision-making against AI agents of various algorithm levels.',
      playHumanTitle: 'Human vs Human',
      playHumanDesc: 'Local two-player hotseat mode with the full 38-piece standard starting deployment.',
      aiVsAiTitle: 'AI vs AI Spectator',
      aiVsAiDesc: 'Spectate automated matches between AI algorithms to analyze thinking time and outcomes.',
      analysisTitle: 'Game Analysis Record',
      analysisDesc: 'Paste match notation or AI vs AI JSON logs to replay every move and inspect agent decisions.',
      rulesTitle: 'Rules & Tactics',
      rulesDesc: 'Official regulations on river crossings, naval corridors, mechanized transport, and anti-air rings.',
      statusReady: 'Ready',
      statusDev: 'In Development',
      pillarsTitle: 'TACTICAL PILLARS',
      pillar1Title: 'Combined Arms Warfare',
      pillar1Desc: 'Seamless coordination between Army, Navy, and Air Force units to protect the Commander.',
      pillar2Title: 'Mechanized Transport',
      pillar2Desc: 'Tanks carry infantry, warships transport aircraft, and combat engineers bridge deep rivers.',
      pillar3Title: 'Anti-Air Defense Ring',
      pillar3Desc: 'Passive anti-aircraft and missile umbrellas trigger lethal 1-for-1 aerial exchanges.',
    },
    game: {
      turn: 'Turn to move',
      redSide: 'Red Force',
      blueSide: 'Blue Force',
      selectedPiece: 'Selected Piece',
      noPieceSelected: 'Click any piece on the board to view tactical specs',
      coordinates: 'Coordinates',
      score: 'Score',
      status: 'Status',
      inProgress: 'In Progress',
      gameOver: 'Game Over',
      newGame: 'New Game',
      resign: 'Resign',
      drawOffer: 'Offer Draw',
      backToHome: 'Home',
      swapTurn: 'Swap Turn',
      timer: 'Match Time',
      activeSession: 'Active Session',
      btnReviewBoard: 'Review Board',
      btnReopenModal: 'View Result',
      confirmNewGameTitle: 'Start New Match?',
      confirmNewGameDesc: 'The current battle is still active. Starting a new game will reset all progress and move history.',
      confirmResignTitle: 'Confirm Resignation?',
      confirmResignDesc: 'Are you sure you want to resign? The opposing force will immediately be declared the victor.',
      confirmDrawTitle: 'Offer Mutual Draw?',
      confirmDrawDesc: 'Are you sure you want to offer a draw? Both forces will conclude the match in an honorable stalemate.',
      confirmYes: 'Confirm',
      confirmCancel: 'Cancel',
      victoryRed: 'RED FORCE VICTORY!',
      victoryBlue: 'BLUE FORCE VICTORY!',
      drawMatch: 'HONORABLE STALEMATE',
      reasonCheckmate: 'Checkmate: Opposing Commander has no escape (+50 pts)',
      reasonStalemate: 'Stalemate Draw: Side to move has no legal moves and is not in check',
      reasonCommanderCaptured: 'Opposing Commander captured (+50 victory pts)',
      reasonResignation: 'Opposing force has surrendered',
      reasonDraw: 'Mutual agreement for peaceful armistice',
      totalTurns: 'Total Turns',
      totalMoves: 'Total Moves',
      finalScore: 'Final Score',
      duration: 'Combat Duration',
      capturedCommanderTitle: 'COMMANDER CAPTURED',
      backendOnline: 'API Online (FastAPI)',
      backendOffline: 'Offline (Local Engine)',
      aiThinking: '🤖 AI is thinking...',
      aiMoveBtn: '🤖 AI Move',
      modeHumanVsAi: 'Human vs AI',
      modeHumanVsHuman: 'Two Players',
      modeAiVsAi: 'AI vs AI (Spectator)',
      modeLabel: 'Combat Mode',
      aiBotName: 'AI Agent',
      selectOpponent: 'Select AI Opponent:',
      redAgentLabel: 'Red Force Agent:',
      blueAgentLabel: 'Blue Force Agent:',
      agentRuleBased: 'RULE-BASE AGENT',
      agentHeuristic: 'HEURISTIC_AGENT',
      agentRandom: 'RANDOM AGENT',
      agentMinimax: 'MINIMAX AGENT (depth=2)',
      btnStartMatch: '▶ Start Match',
      btnPauseMatch: '⏸ Pause',
      btnResumeMatch: '▶ Resume',
      btnStepMatch: '⏭ Step Next',
      speedLabel: 'Speed:',
      btnCopyLog: '📋 Copy Action Log',
      btnAnalyzeMatch: '📊 Analyze Match →',
      copySuccessToast: 'Action log copied to clipboard!',
      aiTimeLimitLabel: 'AI Time Limit:',
      aiTimeLimitUnlimited: 'Unlimited',
      humanNoTimeLimit: 'Human & AI: No time limit',
      navFirst: 'First',
      navPrev: 'Prev',
      navNext: 'Next',
      navLast: 'Last',
      reviewingHistoryBanner: 'Reviewing historical move — press "Last" to return to live play',
      returnToLiveBtn: 'Back to Live (Last)',
      flipBoard: 'Flip Board',
      stepLabel: 'Step',
    },
    analysis: {
      title: 'Game Analysis Record',
      subtitle: 'Paste board notation (MoveHistory / COTULENH-NOTATION) or AI vs AI JSON logs (game_records/*.json) to replay and inspect every decision.',
      inputTitle: 'Load Match Record / Log',
      inputHint: 'Supports: Research JSON logs (game_XXXX.json), selected_action strings (MOVE:... / CMD:END_TURN), copied Action Log text, or COTULENH-NOTATION.',
      placeholder: 'Paste move notation or game_0001.json contents here...',
      btnAnalyze: 'Analyze & Replay',
      btnClear: 'Clear',
      btnUploadFile: 'Upload File (.json/.txt/.ctn)',
      btnLoadSampleNotation: 'Load Sample Notation',
      btnLoadSampleAiJson: 'Load Sample AI vs AI JSON',
      btnAutoPlay: 'Auto Play',
      btnPause: 'Pause',
      speedLabel: 'Speed',
      matchMetaTitle: 'Match Summary',
      detectedFormat: 'Detected Format',
      redAgent: 'Red Force',
      blueAgent: 'Blue Force',
      winnerLabel: 'Result',
      reasonLabel: 'Termination',
      seedLabel: 'Seed',
      totalMovesLabel: 'Replayed Steps',
      telemetryTitle: 'AI Decision Telemetry (Current Step)',
      noTelemetry: 'No AI telemetry attached to this step (plain notation or initial board).',
      ruleTriggered: 'Rule Triggered',
      heuristicScore: 'Heuristic Score',
      decisionTime: 'Decision Time',
      nodesVisited: 'Nodes Visited',
      searchDepth: 'Search Depth',
      nodesPerSecond: 'Search Speed',
      simulations: 'Simulations',
      selectedActionRaw: 'Raw Action',
      heuristicBreakdown: 'Heuristic Components',
      moveListTitle: 'Replayed Move List',
      initialBoardLabel: 'Initial Setup (0)',
      emptyPrompt: 'No record loaded yet. Paste a game log above or load a sample record, then click "Analyze & Replay".',
      warningsTitle: 'Parser Notes',
      copyCurrentNotation: 'Copy Normalized Notation',
      useCurrentMatch: 'Import From Active Board',
      tagBoard: 'Board',
      tagPickup: 'Pickup',
      tagCarrying: 'Carrying',
      tagSoloSplit: 'Solo Split',
      tagDeploy: 'Deploy',
      tagEndCompound: 'End Stack',
      compoundActiveBadge: 'Compound Turn Active',
    },
    stats: {
      title: 'AI Research & Tournament Statistics',
      subtitle: 'Quantitative benchmark results, score matrices, statistical tests, and search tree visualizer across 4 standardized research experiments.',
      filterAll: 'All Experiments',
      filterExp07: 'Exp 07: Random Baseline',
      filterExp08: 'Exp 08: Rule-Based Agent',
      filterExp09: 'Exp 09: Heuristic CCHEF (H1–H7)',
      filterExp10: 'Exp 10: Minimax & Search Tree',
      totalMatchesLabel: 'Total Evaluated Matches',
      totalMatchesValue: '3,080+ Matches',
      maxWinRateLabel: 'Peak Win Rate (H6/MM)',
      bestAgentLabel: 'Top Evaluator: CCHEF H6',
      testSeedsLabel: 'Standard Test Seeds',
      hardwareTitle: 'Standardized Environment',
      hardwareDesc: '16 Cores CPU, 16GB RAM, Windows 11, Python 3.10, 10 Fixed Seeds, max_turns = 200.',
      btnZoom: '🔍 Zoom Diagram',
      closeModal: 'Close',
      exp07Title: 'Experiment 07 — Random Tactical Agent Baseline',
      exp07Desc: 'Uniform move distribution test (Chi-Square), Game Engine symmetry verification over 400 matches, and high-throughput decision latency.',
      exp08Title: 'Experiment 08 — Rule-based Tactical Agent',
      exp08Desc: '1,280-match tournament between Ruleset_A (check safety first) and Ruleset_B (greedy capture) vs Random and Head-to-Head (Check Safety Ablation).',
      exp09Title: 'Experiment 09 — CCHEF Military Heuristic Design & Tuning',
      exp09Desc: '1,200-match Round-Robin tournament among 7 variants H1 -> H7 combined with Coarse-to-Fine Grid Search for optimal military feature weights.',
      exp10Title: 'Experiment 10 — Minimax Adversarial Search & Tree Survey',
      exp10Desc: 'Search tree visualization of depth d=2 Minimax with Alpha-Beta pruning, Candidate Pruning k=20, and CCHEF H6 leaf evaluation.',
    },
    pieces: {
      COMMANDER: 'Commander',
      INFANTRY: 'Infantry',
      TANK: 'Tank',
      MILITIA: 'Militia',
      ENGINEER: 'Engineer',
      ARTILLERY: 'Artillery',
      ANTI_AIR: 'Anti-Air',
      MISSILE: 'Missile',
      AIRCRAFT: 'Aircraft',
      NAVY: 'Navy Ship',
      HEADQUARTERS: 'Headquarters',
    },
  },
};
