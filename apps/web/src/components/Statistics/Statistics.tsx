import React, { useState, useEffect } from 'react';
import { Language, translations } from '../../i18n';
import styles from './Statistics.module.css';

interface StatisticsProps {
  lang: Language;
}

type FilterTab = 'ALL' | 'EXP07' | 'EXP08' | 'EXP09' | 'EXP10';

interface LightboxState {
  isOpen: boolean;
  src: string;
  title: string;
}

export const Statistics: React.FC<StatisticsProps> = ({ lang }) => {
  const t = translations[lang];
  const [activeFilter, setActiveFilter] = useState<FilterTab>('ALL');
  const [lightbox, setLightbox] = useState<LightboxState>({
    isOpen: false,
    src: '',
    title: '',
  });

  // ESC to close modal
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setLightbox((prev) => ({ ...prev, isOpen: false }));
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const openZoom = (src: string, title: string) => {
    setLightbox({ isOpen: true, src, title });
  };

  return (
    <div className={styles.container}>
      {/* 1. Header & Navigation Filters */}
      <header className={styles.header}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>{t.stats.title}</h1>
          <p className={styles.subtitle}>{t.stats.subtitle}</p>
        </div>

        <div className={styles.filterGroup}>
          <button
            type="button"
            className={`${styles.filterBtn} ${activeFilter === 'ALL' ? styles.filterBtnActive : ''}`}
            onClick={() => setActiveFilter('ALL')}
          >
            {t.stats.filterAll}
          </button>
          <button
            type="button"
            className={`${styles.filterBtn} ${activeFilter === 'EXP07' ? styles.filterBtnActive : ''}`}
            onClick={() => setActiveFilter('EXP07')}
          >
            {t.stats.filterExp07}
          </button>
          <button
            type="button"
            className={`${styles.filterBtn} ${activeFilter === 'EXP08' ? styles.filterBtnActive : ''}`}
            onClick={() => setActiveFilter('EXP08')}
          >
            {t.stats.filterExp08}
          </button>
          <button
            type="button"
            className={`${styles.filterBtn} ${activeFilter === 'EXP09' ? styles.filterBtnActive : ''}`}
            onClick={() => setActiveFilter('EXP09')}
          >
            {t.stats.filterExp09}
          </button>
          <button
            type="button"
            className={`${styles.filterBtn} ${activeFilter === 'EXP10' ? styles.filterBtnActive : ''}`}
            onClick={() => setActiveFilter('EXP10')}
          >
            {t.stats.filterExp10}
          </button>
        </div>
      </header>

      {/* 2. Key Performance Indicators (KPI Overview) */}
      <section className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>{t.stats.totalMatchesLabel}</span>
          <strong className={styles.kpiValue}>{t.stats.totalMatchesValue}</strong>
          <span className={styles.kpiHint}>
            {lang === 'vi' ? '400 (E07) + 1.280 (E08) + 1.200 (E09) + 200 (E10)' : '400 (E07) + 1,280 (E08) + 1,200 (E09) + 200 (E10)'}
          </span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>{t.stats.maxWinRateLabel}</span>
          <strong className={styles.kpiValue} style={{ color: '#22c55e' }}>100.0%</strong>
          <span className={styles.kpiHint}>
            {lang === 'vi' ? 'CCHEF H6 (490/490) & Minimax d=2 (199/199)' : 'CCHEF H6 (490/490) & Minimax d=2 (199/199)'}
          </span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>{t.stats.bestAgentLabel}</span>
          <strong className={styles.kpiValue} style={{ fontSize: '1.25rem' }}>CCHEF H6</strong>
          <span className={styles.kpiHint}>
            {lang === 'vi' ? '7 đặc trưng quân sự + Lượng giá nước đi ghép' : '7 Military features + Compound action eval'}
          </span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>{t.stats.testSeedsLabel}</span>
          <strong className={styles.kpiValue} style={{ fontSize: '1.15rem' }}>10 Fixed Seeds</strong>
          <span className={styles.kpiHint}>[2026, 42, 0, 7, 123, 1337, 2024, 2025, 3407, 9999]</span>
        </div>
      </section>

      {/* Environment Standard Box */}
      <div className={styles.envCard}>
        <span className={styles.envBadge}>⚙</span>
        <div>
          <strong style={{ color: 'var(--gold-primary)', marginRight: '0.5rem' }}>
            {t.stats.hardwareTitle}:
          </strong>
          <span>{t.stats.hardwareDesc}</span>
        </div>
      </div>

      {/* 3. EXPERIMENT 07: RANDOM AGENT BASELINE */}
      {(activeFilter === 'ALL' || activeFilter === 'EXP07') && (
        <section className={styles.expSection}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleGroup}>
              <h2 className={styles.sectionTitle}>
                <span>🎲</span> {t.stats.exp07Title}
              </h2>
              <p className={styles.sectionDesc}>{t.stats.exp07Desc}</p>
            </div>
            <span className="badge">400 {lang === 'vi' ? 'ván đấu' : 'matches'}</span>
          </div>

          {/* Table 07 */}
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Chế độ' : 'Mode'}</th>
                  <th>{lang === 'vi' ? 'Tổng ván' : 'Total'}</th>
                  <th>{lang === 'vi' ? 'Hoàn tất' : 'Completed'}</th>
                  <th>{lang === 'vi' ? 'Chạm trần 200 lượt' : 'Truncated (200t)'}</th>
                  <th>{lang === 'vi' ? 'Thắng - Thua (Đỏ-Xanh)' : 'Win - Loss (Red-Blue)'}</th>
                  <th>{lang === 'vi' ? 'Tỷ lệ thắng (95% CI)' : 'Win Rate (95% CI)'}</th>
                  <th>{lang === 'vi' ? 'Độ trễ TB/nước' : 'Avg Latency/Move'}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>default</code> (Không giới hạn)</td>
                  <td>200</td>
                  <td>12</td>
                  <td>188 (94.0%)</td>
                  <td>6 — 6</td>
                  <td className={styles.winRateMid}>0.500 [0.254, 0.746]</td>
                  <td><strong>0.0063 ms</strong> (&gt;150k n/s)</td>
                </tr>
                <tr>
                  <td><code>controlled</code> (1000 ms)</td>
                  <td>200</td>
                  <td>12</td>
                  <td>188 (94.0%)</td>
                  <td>6 — 6</td>
                  <td className={styles.winRateMid}>0.500 [0.254, 0.746]</td>
                  <td><strong>0.0075 ms</strong> (&gt;130k n/s)</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Charts Grid 07 */}
          <div className={styles.galleryGrid}>
            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp07_fig_01_uniformity_distribution.png',
                  lang === 'vi'
                    ? 'Hình 4.1: Kiểm định phân phối đồng đều nước đi (Chi-Square Test p > 0.05)'
                    : 'Fig 4.1: Chi-Square Uniformity Test of Legal Moves'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp07_fig_01_uniformity_distribution.png"
                  alt="Uniformity Distribution"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân phối đồng đều nước đi (Chi-Square Test)' : 'Uniformity Distribution (Chi-Square)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp07_fig_02_wdl_rates.png',
                  lang === 'vi'
                    ? 'Hình 4.2: Tỷ lệ Thắng / Hòa / Thua giữa Random vs Random (50% đối xứng hoàn hảo)'
                    : 'Fig 4.2: Win / Draw / Loss Rates (Random vs Random)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp07_fig_02_wdl_rates.png"
                  alt="Win Loss Distribution"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Tỷ lệ Thắng/Hòa/Thua (Đối xứng 50% - 50%)' : 'W/D/L Rates (50% Symmetry)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp07_fig_03_score_ci.png',
                  lang === 'vi'
                    ? 'Hình 4.3: Khoảng tin cậy Bootstrap 95% điểm số của RandomAgent'
                    : 'Fig 4.3: Bootstrap 95% Confidence Intervals for Scores'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp07_fig_03_score_ci.png"
                  alt="Score Confidence Intervals"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Khoảng tin cậy Bootstrap 95% điểm số' : 'Bootstrap 95% Score CI'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp07_fig_05_latency_comparison.png',
                  lang === 'vi'
                    ? 'Hình 4.4: Phân phối độ trễ ra quyết định của RandomAgent (<0.01 ms)'
                    : 'Fig 4.4: Decision Latency Distribution of RandomAgent'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp07_fig_05_latency_comparison.png"
                  alt="Decision Latency"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân phối độ trễ suy nghĩ (<0.01 ms/nước)' : 'Decision Latency (<0.01 ms/move)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 4. EXPERIMENT 08: RULE-BASED AGENT */}
      {(activeFilter === 'ALL' || activeFilter === 'EXP08') && (
        <section className={styles.expSection}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleGroup}>
              <h2 className={styles.sectionTitle}>
                <span>🛡️</span> {t.stats.exp08Title}
              </h2>
              <p className={styles.sectionDesc}>{t.stats.exp08Desc}</p>
            </div>
            <span className="badge">1.280 {lang === 'vi' ? 'ván đấu' : 'matches'}</span>
          </div>

          {/* Table 08 */}
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Cặp đối đầu' : 'Matchup'}</th>
                  <th>{lang === 'vi' ? 'Chế độ' : 'Mode'}</th>
                  <th>{lang === 'vi' ? 'Tổng ván' : 'Total'}</th>
                  <th>{lang === 'vi' ? 'Thắng (A)' : 'Win (A)'}</th>
                  <th>{lang === 'vi' ? 'Hòa' : 'Draw'}</th>
                  <th>{lang === 'vi' ? 'Thua (A)' : 'Loss (A)'}</th>
                  <th>{lang === 'vi' ? 'Tỷ lệ thắng (95% CI)' : 'Win Rate (95% CI)'}</th>
                  <th>{lang === 'vi' ? 'Độ trễ TB' : 'Avg Latency'}</th>
                </tr>
              </thead>
              <tbody>
                <tr className={styles.highlightRow}>
                  <td><strong>Ruleset_A vs Random</strong></td>
                  <td><code>default</code></td>
                  <td>200</td>
                  <td>153</td>
                  <td>0</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [0.976, 1.000] (100%)</td>
                  <td>97.11 ms</td>
                </tr>
                <tr>
                  <td>Ruleset_B vs Random</td>
                  <td><code>default</code></td>
                  <td>200</td>
                  <td>187</td>
                  <td>0</td>
                  <td>1</td>
                  <td className={styles.winRateHigh}>0.995 [0.970, 0.999]</td>
                  <td>95.07 ms</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Ruleset_B vs Ruleset_A (Ablation)</strong></td>
                  <td><code>default</code></td>
                  <td>200</td>
                  <td>34</td>
                  <td>2</td>
                  <td>63 (A thắng 63.6%)</td>
                  <td className={styles.winRateLow}>0.343 [0.257, 0.441]</td>
                  <td>38.84 ms</td>
                </tr>
                <tr>
                  <td>Ruleset_A vs Random</td>
                  <td><code>controlled</code></td>
                  <td>200</td>
                  <td>153</td>
                  <td>0</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [0.976, 1.000] (100%)</td>
                  <td>102.38 ms</td>
                </tr>
                <tr>
                  <td>Ruleset_B vs Random</td>
                  <td><code>controlled</code></td>
                  <td>200</td>
                  <td>180</td>
                  <td>0</td>
                  <td>1</td>
                  <td className={styles.winRateHigh}>0.994 [0.969, 0.999]</td>
                  <td>95.99 ms</td>
                </tr>
                <tr>
                  <td>Ruleset_B vs Ruleset_A</td>
                  <td><code>controlled</code></td>
                  <td>200</td>
                  <td>33</td>
                  <td>2</td>
                  <td>63</td>
                  <td className={styles.winRateLow}>0.337 [0.251, 0.435]</td>
                  <td>44.57 ms</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Charts Grid 08 */}
          <div className={styles.galleryGrid}>
            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp08_fig_01_wdl_rules.png',
                  lang === 'vi'
                    ? 'Hình 4.5: Tỷ lệ Thắng/Hòa/Thua của các hệ luật so với Random'
                    : 'Fig 4.5: Win / Draw / Loss Rates of Rulesets vs Random'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp08_fig_01_wdl_rules.png"
                  alt="Ruleset WDL"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Thành tích áp đảo trước Random (~100% thắng)' : 'Dominant Win Rate vs Random (~100%)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp08_fig_04_check_safety_ablation.png',
                  lang === 'vi'
                    ? 'Hình 4.6: Ablation Study — Hiệu quả cốt lõi của quy tắc Check Safety (Ruleset_A thắng 63.6%)'
                    : 'Fig 4.6: Ablation Study — Impact of Check Safety Rule'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp08_fig_04_check_safety_ablation.png"
                  alt="Check Safety Ablation"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Ablation Check Safety: Ruleset_A thắng áp đảo 63.6%' : 'Check Safety Ablation: Ruleset_A wins 63.6%'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp08_fig_03_rule_frequency.png',
                  lang === 'vi'
                    ? 'Hình 4.7: Tần suất kích hoạt các quy tắc chiến thuật (Bảo vệ Tư lệnh, Ăn quân, Thoát hiểm)'
                    : 'Fig 4.7: Activation Frequency of Tactical Rules'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp08_fig_03_rule_frequency.png"
                  alt="Rule Activation Frequency"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Tần suất kích hoạt các quy tắc chiến thuật' : 'Rule Activation Frequency'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp08_fig_06_red_blue_split.png',
                  lang === 'vi'
                    ? 'Hình 4.8: So sánh thành tích theo màu cờ Đỏ (đi trước) và Xanh'
                    : 'Fig 4.8: Performance Split by Faction Color (Red vs Blue)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp08_fig_06_red_blue_split.png"
                  alt="Red vs Blue Split"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'So sánh thành tích phe Đỏ (đi trước) và Xanh' : 'Performance Split by Red and Blue'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 5. EXPERIMENT 09: CCHEF HEURISTIC (H1 -> H7) */}
      {(activeFilter === 'ALL' || activeFilter === 'EXP09') && (
        <section className={styles.expSection}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleGroup}>
              <h2 className={styles.sectionTitle}>
                <span>⭐</span> {t.stats.exp09Title}
              </h2>
              <p className={styles.sectionDesc}>{t.stats.exp09Desc}</p>
            </div>
            <span className="badge">1.200 {lang === 'vi' ? 'ván Round-Robin' : 'Round-Robin matches'}</span>
          </div>

          {/* Optimal Weights Formula */}
          <div className={styles.formulaBox}>
            <span className={styles.formulaTitle}>
              {lang === 'vi' ? 'Bộ Trọng Số CCHEF Tối Ưu Qua Grid Search (Biến thể H6):' : 'Optimal CCHEF Grid Search Weights (Variant H6):'}
            </span>
            <div className={styles.formulaText}>
              w* = [ M: 0.30 (Vật chất) | K: 0.30 (An toàn Tư lệnh) | Q: 0.10 (Tiềm năng chiếu) | P: 0.10 (Địa hình) | C: 0.05 (Cơ động) | D: 0.05 (Triển khai) | T: 0.10 (Rủi ro) ]
            </div>
          </div>

          {/* Table 09 */}
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Biến thể' : 'Variant'}</th>
                  <th>{lang === 'vi' ? 'Đặc trưng tích hợp' : 'Active Features'}</th>
                  <th>{lang === 'vi' ? 'Hoàn tất' : 'Completed'}</th>
                  <th>{lang === 'vi' ? 'Thắng' : 'Wins'}</th>
                  <th>{lang === 'vi' ? 'Thua' : 'Losses'}</th>
                  <th>{lang === 'vi' ? 'Tỷ lệ thắng (95% CI)' : 'Win Rate (95% CI)'}</th>
                  <th>{lang === 'vi' ? 'Độ trễ TB' : 'Avg Latency'}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>H1</strong></td>
                  <td>M (Vật chất thuần túy)</td>
                  <td>728</td>
                  <td>37</td>
                  <td>691</td>
                  <td className={styles.winRateLow}>0.051 [0.037, 0.069] (5.1%)</td>
                  <td>47.33 ms</td>
                </tr>
                <tr>
                  <td><strong>H2</strong></td>
                  <td>M, P, C (+ Địa hình, Cơ động)</td>
                  <td>559</td>
                  <td>85</td>
                  <td>474</td>
                  <td className={styles.winRateLow}>0.152 [0.125, 0.184] (15.2%)</td>
                  <td>83.23 ms</td>
                </tr>
                <tr>
                  <td><strong>H3</strong></td>
                  <td>M, P, C, K (+ An toàn Tư lệnh)</td>
                  <td>219</td>
                  <td>62</td>
                  <td>157</td>
                  <td className={styles.winRateMid}>0.283 [0.228, 0.346] (28.3%)</td>
                  <td>62.75 ms</td>
                </tr>
                <tr>
                  <td><strong>H4</strong></td>
                  <td>M, P, C, K, Q (+ Tiềm năng chiếu)</td>
                  <td>220</td>
                  <td>93</td>
                  <td>127</td>
                  <td className={styles.winRateMid}>0.423 [0.359, 0.489] (42.3%)</td>
                  <td>63.36 ms</td>
                </tr>
                <tr>
                  <td><strong>H5</strong></td>
                  <td>M, P, C, K, Q, D (+ Triển khai quân)</td>
                  <td>233</td>
                  <td>186</td>
                  <td>47</td>
                  <td className={styles.winRateHigh}>0.798 [0.742, 0.845] (79.8%)</td>
                  <td>72.08 ms</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>H6 (Best)</strong></td>
                  <td><strong>Đầy đủ 7 đặc trưng + Nước đi ghép (CO Synergy)</strong></td>
                  <td><strong>490</strong></td>
                  <td><strong>490</strong></td>
                  <td><strong>0</strong></td>
                  <td className={styles.winRateHigh}><strong>1.000 [0.992, 1.000] (100.0%)</strong></td>
                  <td><strong>179.23 ms</strong></td>
                </tr>
                <tr>
                  <td><strong>H7</strong></td>
                  <td>Đầy đủ + Trọng số thích ứng 3 giai đoạn</td>
                  <td>543</td>
                  <td>543</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [0.993, 1.000] (100.0%)</td>
                  <td>207.51 ms</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Charts Grid 09 */}
          <div className={styles.galleryGrid}>
            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_01_round_robin_heatmap_score.png',
                  lang === 'vi'
                    ? 'Hình 4.9: Ma trận điểm số giải đấu Round-Robin giữa 7 biến thể Heuristic'
                    : 'Fig 4.9: Round-Robin Score Heatmap (H1 to H7)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_01_round_robin_heatmap_score.png"
                  alt="Round-Robin Score Heatmap"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Ma trận điểm số Round-Robin Heatmap' : 'Round-Robin Score Heatmap'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_03_formula_contribution_h1_h7.png',
                  lang === 'vi'
                    ? 'Hình 4.10: Biểu đồ Radar — Đóng góp biên của từng thành phần đặc trưng CCHEF'
                    : 'Fig 4.10: Radar Chart of Marginal Feature Contributions'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_03_formula_contribution_h1_h7.png"
                  alt="Radar Feature Contribution"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Biểu đồ Radar: Đóng góp biên các đặc trưng' : 'Radar Chart: Feature Contributions'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_04_grid_search_weights.png',
                  lang === 'vi'
                    ? 'Hình 4.11: Bản đồ nhiệt tối ưu hóa trọng số qua Coarse-to-Fine Grid Search'
                    : 'Fig 4.11: Coarse-to-Fine Grid Search Weight Optimization'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_04_grid_search_weights.png"
                  alt="Grid Search Weights"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Bản đồ nhiệt tối ưu hóa trọng số Grid Search' : 'Grid Search Weight Heatmap'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_07_red_vs_blue_advantage.png',
                  lang === 'vi'
                    ? 'Hình 4.12: Phân tích lợi thế đi trước giữa phe Đỏ và phe Xanh'
                    : 'Fig 4.12: First-Move Advantage Analysis (Red vs Blue)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_07_red_vs_blue_advantage.png"
                  alt="Red vs Blue Advantage"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân tích lợi thế đi trước (Đỏ vs Xanh)' : 'First-Move Advantage (Red vs Blue)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 6. EXPERIMENT 10: MINIMAX AGENT & SEARCH TREE */}
      {(activeFilter === 'ALL' || activeFilter === 'EXP10') && (
        <section className={styles.expSection}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleGroup}>
              <h2 className={styles.sectionTitle}>
                <span>🌲</span> {t.stats.exp10Title}
              </h2>
              <p className={styles.sectionDesc}>{t.stats.exp10Desc}</p>
            </div>
            <span className="badge">Minimax d=2 (Alpha-Beta, k=20)</span>
          </div>

          {/* Minimax Tree Diagram Card */}
          <div
            className={styles.treeCard}
            onClick={() =>
              openZoom(
                '/assets/stats/sample_minimax_tree.png',
                lang === 'vi'
                  ? 'Hình 4.13: Sơ đồ Cây tìm kiếm Minimax thực tế độ sâu d=2 với phân tầng MAX/MIN, cắt tỉa Alpha-Beta và lượng giá lá CCHEF H6'
                  : 'Fig 4.13: Real Adversarial Minimax Search Tree (depth d=2 with Alpha-Beta and CCHEF H6 leaf values)'
              )
            }
          >
            <div className={styles.treeImgWrapper}>
              <img
                src="/assets/stats/sample_minimax_tree.png"
                alt="Minimax Search Tree Structure"
                className={styles.treeImg}
              />
            </div>
            <div className={styles.chartCaption}>
              <span>
                {lang === 'vi'
                  ? 'Sơ đồ Cây tìm kiếm Minimax thực tế độ sâu d=2 (Trích xuất từ bàn cờ mở màn)'
                  : 'Actual Minimax Adversarial Search Tree d=2 (Opening Board State)'}
              </span>
              <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
            </div>
          </div>

          {/* Table 10 */}
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Cấu hình thực nghiệm' : 'Experiment Setup'}</th>
                  <th>{lang === 'vi' ? 'Đối thủ' : 'Opponent'}</th>
                  <th>{lang === 'vi' ? 'Tổng ván' : 'Total'}</th>
                  <th>{lang === 'vi' ? 'Kết quả Thắng - Thua' : 'Wins - Losses'}</th>
                  <th>{lang === 'vi' ? 'Tỷ lệ thắng (95% CI)' : 'Win Rate (95% CI)'}</th>
                  <th>{lang === 'vi' ? 'Nút duyệt / Tốc độ (NPS)' : 'Nodes Visited / NPS'}</th>
                </tr>
              </thead>
              <tbody>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=1 (Ablation Depth)</strong></td>
                  <td>Ruleset_A</td>
                  <td>28</td>
                  <td>28 — 0 (Thắng tuyệt đối)</td>
                  <td className={styles.winRateHigh}>1.000 [0.877, 1.000] (100%)</td>
                  <td>20 nodes / 80 - 150 NPS</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 (Alpha-Beta, k=20)</strong></td>
                  <td>RandomAgent</td>
                  <td>200</td>
                  <td>199 — 0 (1 hòa chạm trần)</td>
                  <td className={styles.winRateHigh}>1.000 [0.981, 1.000] (100%)</td>
                  <td>834 - 1.362 nodes / 180 - 300 NPS</td>
                </tr>
                <tr>
                  <td>Minimax d=2 (Ngân sách n=1000)</td>
                  <td>Ruleset_A</td>
                  <td>40</td>
                  <td>Đang vận hành thực nghiệm</td>
                  <td className={styles.winRateMid}>Đang hoàn tất 40 ván</td>
                  <td>Giới hạn ngân sách 1.000 nút duyệt</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Lightbox Zoom Modal */}
      {lightbox.isOpen && (
        <div className={styles.modalOverlay} onClick={() => setLightbox((prev) => ({ ...prev, isOpen: false }))}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>{lightbox.title}</h3>
              <button
                type="button"
                className={styles.modalCloseBtn}
                onClick={() => setLightbox((prev) => ({ ...prev, isOpen: false }))}
                title={t.stats.closeModal}
              >
                ✕
              </button>
            </div>
            <div className={styles.modalBody}>
              <img src={lightbox.src} alt={lightbox.title} className={styles.modalImg} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

