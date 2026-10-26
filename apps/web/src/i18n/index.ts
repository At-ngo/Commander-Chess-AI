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
      replays: 'Xem lại ván',
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
      gameOver: 'Kết thúc ván',
      newGame: 'Ván mới',
      resign: 'Đầu hàng',
      drawOffer: 'Cầu hòa',
      backToHome: 'Trang chủ',
      swapTurn: 'Đổi lượt',
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
      replays: 'Replays',
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
