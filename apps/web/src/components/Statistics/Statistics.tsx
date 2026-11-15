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
            {lang === 'vi' ? '400 (E07) + 1.280 (E08) + 1.200 (E09) + 1.360 (E10)' : '400 (E07) + 1,280 (E08) + 1,200 (E09) + 1,360 (E10)'}
          </span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>{t.stats.maxWinRateLabel}</span>
          <strong className={styles.kpiValue} style={{ color: '#22c55e' }}>100.0%</strong>
          <span className={styles.kpiHint}>
            {lang === 'vi' ? 'CCHEF H6 (490/490) & Minimax d=2 (516/516 unconstrained)' : 'CCHEF H6 (490/490) & Minimax d=2 (516/516 unconstrained)'}
          </span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>{t.stats.bestAgentLabel}</span>
          <strong className={styles.kpiValue} style={{ fontSize: '1.25rem' }}>Minimax d=2</strong>
          <span className={styles.kpiHint}>
            {lang === 'vi' ? 'Tìm kiếm đối kháng 2-ply + Lượng giá lá CCHEF H6' : 'Adversarial 2-ply Search + CCHEF H6 Leaf Eval'}
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
                  '/assets/stats/exp08_fig_02_score_ci.png',
                  lang === 'vi'
                    ? 'Hình 4.6: Khoảng tin cậy Bootstrap 95% điểm số của các hệ luật (Ruleset_A vs Random, Ruleset_B vs Random, A vs B)'
                    : 'Fig 4.6: Bootstrap 95% Confidence Intervals for Ruleset Scores'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp08_fig_02_score_ci.png"
                  alt="Ruleset Score CI"
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
                  '/assets/stats/exp08_fig_04_check_safety_ablation.png',
                  lang === 'vi'
                    ? 'Hình 4.7: Ablation Study — Hiệu quả cốt lõi của quy tắc Check Safety (Ruleset_A thắng 63.6%)'
                    : 'Fig 4.7: Ablation Study — Impact of Check Safety Rule'
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
                    ? 'Hình 4.8: Tần suất kích hoạt các quy tắc chiến thuật (Bảo vệ Tư lệnh, Ăn quân, Thoát hiểm)'
                    : 'Fig 4.8: Activation Frequency of Tactical Rules'
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
                  '/assets/stats/exp08_fig_05_latency.png',
                  lang === 'vi'
                    ? 'Hình 4.9: Phân phối thời gian ra quyết định của RuleBasedAgent (38 - 102 ms/nước, phản hồi thời gian thực tức thì)'
                    : 'Fig 4.9: Decision Latency Distribution of RuleBasedAgent (38 - 102 ms/move)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp08_fig_05_latency.png"
                  alt="Ruleset Latency"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân phối độ trễ suy nghĩ (38 - 102 ms/nước)' : 'Decision Latency (38 - 102 ms/move)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp08_fig_06_red_blue_split.png',
                  lang === 'vi'
                    ? 'Hình 4.10: So sánh thành tích theo màu cờ Đỏ (đi trước) và Xanh'
                    : 'Fig 4.10: Performance Split by Faction Color (Red vs Blue)'
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
                  '/assets/stats/exp09_fig_05_h1_h7_vs_random_budgets.png',
                  lang === 'vi'
                    ? 'Hình 4.13: Thành tích đối đầu giữa H1 -> H7 và RandomAgent qua 2 chế độ ngân sách'
                    : 'Fig 4.13: H1 to H7 Performance vs RandomAgent Across Budget Modes'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_05_h1_h7_vs_random_budgets.png"
                  alt="H1-H7 vs Random"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Thành tích H1 -> H7 vs Random qua 2 chế độ' : 'H1-H7 vs Random Across Budgets'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_06_h1_h7_vs_rulesA_budgets.png',
                  lang === 'vi'
                    ? 'Hình 4.14: Bước nhảy vọt thành tích từ 7.2% lên 98.8% khi H1 -> H7 đối đầu Ruleset_A'
                    : 'Fig 4.14: Win Rate Leap (7.2% to 98.8%) of H1 to H7 vs Ruleset_A'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_06_h1_h7_vs_rulesA_budgets.png"
                  alt="H1-H7 vs Ruleset_A"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Bước nhảy vọt thành tích vs Ruleset_A (7.2% -> 98.8%)' : 'Win Rate Leap vs Ruleset_A (7.2% -> 98.8%)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_08_latency_and_timeout_1000ms.png',
                  lang === 'vi'
                    ? 'Hình 4.15: Phân phối độ trễ suy nghĩ (238 - 350 ms/nước) và kiểm soát an toàn trần 1000 ms của Heuristic'
                    : 'Fig 4.15: Decision Latency (238 - 350 ms/move) and 1000 ms Timeout Compliance'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp09_fig_08_latency_and_timeout_1000ms.png"
                  alt="Heuristic Latency & Timeout"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Độ trễ suy nghĩ & kiểm soát trần 1000 ms' : 'Decision Latency & 1000 ms Budget'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp09_fig_07_red_vs_blue_advantage.png',
                  lang === 'vi'
                    ? 'Hình 4.16: Phân tích lợi thế đi trước giữa phe Đỏ và phe Xanh'
                    : 'Fig 4.16: First-Move Advantage Analysis (Red vs Blue)'
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
            <span className="badge">1.200 {lang === 'vi' ? 'ván Giải đấu + 160 ván Ablation' : 'Tournament + 160 Ablation matches'}</span>
          </div>

          {/* Minimax Architecture & Strategy Box */}
          <div className={styles.formulaBox}>
            <span className={styles.formulaTitle}>
              {lang === 'vi' ? 'Kiến Trúc Tìm Kiếm Đối Kháng & Kiểm Soát Bùng Nổ Tổ Hợp:' : 'Adversarial Search Architecture & Complexity Control:'}
            </span>
            <div className={styles.formulaText}>
              {lang === 'vi'
                ? 'Minimax d = 2 (MAX → MIN) | Cắt tỉa Alpha-Beta | Candidate Pruning k = 20 (thu hẹp cây ~8.100 → ≤400 nút) | Lượng giá lá: CCHEF H6'
                : 'Minimax d = 2 (MAX → MIN) | Alpha-Beta Pruning | Candidate Pruning k = 20 (prunes ~8,100 → ≤400 nodes) | Leaf Evaluation: CCHEF H6'}
            </div>
          </div>

          {/* Minimax Tree Diagram Card */}
          <div
            className={styles.treeCard}
            onClick={() =>
              openZoom(
                '/assets/stats/exp10_fig_10_minimax_search_tree.png',
                lang === 'vi'
                  ? 'Hình 4.13: Sơ đồ Cây tìm kiếm Minimax thực tế độ sâu d=2 với phân tầng MAX/MIN, cắt tỉa Alpha-Beta và lượng giá lá CCHEF H6'
                  : 'Fig 4.13: Real Adversarial Minimax Search Tree (depth d=2 with Alpha-Beta and CCHEF H6 leaf values)'
              )
            }
          >
            <div className={styles.treeImgWrapper}>
              <img
                src="/assets/stats/exp10_fig_10_minimax_search_tree.png"
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

          {/* Subheading: Tournament Results */}
          <div style={{ marginTop: '0.5rem', marginBottom: '-0.5rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--gold-primary)', fontFamily: 'var(--font-display)', margin: 0 }}>
              {lang === 'vi' ? '1. Kết Quả Giải Đấu 1.200 Ván Đối Đầu Các Đường Cơ Sở (6 Cặp Đấu):' : '1. Tournament Results (1,200 Matches Across 6 Matchups):'}
            </h3>
          </div>

          {/* Table 10a: Tournament */}
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Cặp đối đầu' : 'Matchup'}</th>
                  <th>{lang === 'vi' ? 'Chế độ' : 'Mode'}</th>
                  <th>{lang === 'vi' ? 'Tổng ván' : 'Total'}</th>
                  <th>{lang === 'vi' ? 'Thắng (MM)' : 'Win (MM)'}</th>
                  <th>{lang === 'vi' ? 'Hòa (Truncated)' : 'Draw (Trunc)'}</th>
                  <th>{lang === 'vi' ? 'Thua (MM)' : 'Loss (MM)'}</th>
                  <th>{lang === 'vi' ? 'Tỷ lệ thắng (95% CI)' : 'Win Rate (95% CI)'}</th>
                  <th>{lang === 'vi' ? 'Điểm số (Score)' : 'Score'}</th>
                  <th>{lang === 'vi' ? 'Độ trễ TB' : 'Avg Latency'}</th>
                  <th>{lang === 'vi' ? 'Nút duyệt / NPS' : 'Nodes / NPS'}</th>
                </tr>
              </thead>
              <tbody>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 vs Random</strong></td>
                  <td><code>default</code></td>
                  <td>200</td>
                  <td>199</td>
                  <td>1</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [1.000, 1.000] (100%)</td>
                  <td className={styles.winRateHigh}>0.998 [0.995, 1.000]</td>
                  <td>11.82 ms (p95: 57.65 ms)</td>
                  <td>834.7 nodes / 83.8 NPS</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 vs Ruleset_A</strong></td>
                  <td><code>default</code></td>
                  <td>200</td>
                  <td>181</td>
                  <td>19</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [1.000, 1.000] (100%)</td>
                  <td className={styles.winRateHigh}>0.953 [0.925, 0.980]</td>
                  <td>12.87 ms (p95: 59.83 ms)</td>
                  <td>1.256.8 nodes / 114.6 NPS</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 vs Heuristic_H6</strong></td>
                  <td><code>default</code></td>
                  <td>200</td>
                  <td>136</td>
                  <td>64</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [1.000, 1.000] (100%)</td>
                  <td className={styles.winRateHigh}>0.840 [0.790, 0.890]</td>
                  <td>8.21 ms (p95: 39.46 ms)</td>
                  <td>586.6 nodes / 197.0 NPS</td>
                </tr>
                <tr>
                  <td>Minimax d=2 vs Random</td>
                  <td><code>controlled</code> (1000ms)</td>
                  <td>200</td>
                  <td>190</td>
                  <td>10</td>
                  <td>0</td>
                  <td className={styles.winRateHigh}>1.000 [0.980, 1.000] (100%)</td>
                  <td className={styles.winRateHigh}>0.975 [0.955, 0.995]</td>
                  <td>893.9 ms (0 quá giờ)</td>
                  <td>56.4 nodes / 65.8 NPS</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 vs Ruleset_A</strong></td>
                  <td><code>controlled</code> (1000ms)</td>
                  <td>200</td>
                  <td>162</td>
                  <td>36</td>
                  <td>2</td>
                  <td className={styles.winRateHigh}>0.988 [0.970, 1.000] (98.8%)</td>
                  <td className={styles.winRateHigh}>0.900 [0.860, 0.940]</td>
                  <td>870.0 ms (0 quá giờ)</td>
                  <td>94.4 nodes / 116.4 NPS</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 vs Heuristic_H6</strong></td>
                  <td><code>controlled</code> (1000ms)</td>
                  <td>200</td>
                  <td>58</td>
                  <td>139</td>
                  <td>3</td>
                  <td className={styles.winRateHigh}>0.951 [0.885, 1.000] (95.1%)</td>
                  <td className={styles.winRateMid}>0.638 [0.575, 0.700]</td>
                  <td>801.0 ms (0 quá giờ)</td>
                  <td>171.7 nodes / 247.4 NPS</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Subheading: Ablation Study */}
          <div style={{ marginTop: '0.75rem', marginBottom: '-0.5rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--gold-primary)', fontFamily: 'var(--font-display)', margin: 0 }}>
              {lang === 'vi' ? '2. Khảo Sát Ablation Study — Độ Sâu & Độ Nhạy Ngân Sách Nút (160 Ván):' : '2. Ablation Study — Search Depth & Node Budget Sensitivity (160 Matches):'}
            </h3>
          </div>

          {/* Table 10b: Ablation */}
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{lang === 'vi' ? 'Cấu hình Ablation' : 'Ablation Setup'}</th>
                  <th>{lang === 'vi' ? 'Đối thủ' : 'Opponent'}</th>
                  <th>{lang === 'vi' ? 'Số ván' : 'Games'}</th>
                  <th>{lang === 'vi' ? 'Thắng — Hòa — Thua' : 'W — D — L'}</th>
                  <th>{lang === 'vi' ? 'Tỷ lệ thắng (Win Rate)' : 'Win Rate'}</th>
                  <th>{lang === 'vi' ? 'Điểm số (Score)' : 'Score'}</th>
                  <th>{lang === 'vi' ? 'Nút duyệt TB' : 'Avg Nodes'}</th>
                  <th>{lang === 'vi' ? 'Độ trễ TB' : 'Avg Latency'}</th>
                  <th>{lang === 'vi' ? 'Phân tích chiến thuật & Hiện tượng' : 'Tactical Analysis & Phenomenon'}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Minimax d=1 (1-ply)</strong></td>
                  <td>Ruleset_A</td>
                  <td>40</td>
                  <td>40 — 0 — 0</td>
                  <td className={styles.winRateHigh}>1.000 (100.0%)</td>
                  <td className={styles.winRateHigh}>1.000</td>
                  <td>20.0</td>
                  <td>1.05 ms</td>
                  <td>{lang === 'vi' ? 'Đánh giá 1 tầng nhanh tức thì, không nhìn trước phản công' : 'Instant 1-ply evaluation, no lookahead for counters'}</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Minimax d=2 (2-ply)</strong></td>
                  <td>Ruleset_A</td>
                  <td>40</td>
                  <td>40 — 0 — 0</td>
                  <td className={styles.winRateHigh}>1.000 (100.0%)</td>
                  <td className={styles.winRateHigh}>1.000</td>
                  <td>1.362.4</td>
                  <td>11.23 ms</td>
                  <td>{lang === 'vi' ? 'Lường trước đòn phản công 2 tầng, tránh bẫy chiếu chết hiểm' : 'Foresees 2-ply counter-threats, avoids fatal check traps'}</td>
                </tr>
                <tr>
                  <td>Ngân sách nút N = 500</td>
                  <td>Ruleset_A</td>
                  <td>20</td>
                  <td>1 — 12 — 7</td>
                  <td className={styles.winRateLow}>0.125 (12.5%)</td>
                  <td className={styles.winRateLow}>0.350</td>
                  <td>500.0</td>
                  <td>4.89 ms</td>
                  <td>{lang === 'vi' ? 'Cắt tỉa cụt giữa chừng tầng MIN, ngộ nhận thế cờ an toàn' : 'Prematurely truncated in MIN ply, false sense of safety'}</td>
                </tr>
                <tr style={{ background: 'rgba(239, 68, 68, 0.08)' }}>
                  <td><strong>Ngân sách nút N = 1.000</strong></td>
                  <td>Ruleset_A</td>
                  <td>20</td>
                  <td>0 — 12 — 8</td>
                  <td className={styles.winRateLow} style={{ color: '#ef4444', fontWeight: 800 }}>0.000 (0.0%)</td>
                  <td className={styles.winRateLow}>0.300</td>
                  <td>1.000.0</td>
                  <td>9.87 ms</td>
                  <td><strong style={{ color: '#ef4444' }}>{lang === 'vi' ? 'Đỉnh điểm Horizon Effect: mù đòn phản công bắt Tư lệnh' : 'Peak Horizon Effect: blind to opponent counter-check'}</strong></td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Ngân sách nút N = 2.000</strong></td>
                  <td>Ruleset_A</td>
                  <td>20</td>
                  <td>8 — 9 — 3</td>
                  <td className={styles.winRateHigh}>0.727 (72.7%)</td>
                  <td className={styles.winRateMid}>0.625</td>
                  <td>1.942.1</td>
                  <td>19.54 ms</td>
                  <td>{lang === 'vi' ? 'Vượt ngưỡng tới hạn N*, khôi phục năng lực đối kháng' : 'Crosses critical threshold N*, restores tactical defense'}</td>
                </tr>
                <tr className={styles.highlightRow}>
                  <td><strong>Ngân sách nút N = 5.000</strong></td>
                  <td>Ruleset_A</td>
                  <td>20</td>
                  <td>16 — 4 — 0</td>
                  <td className={styles.winRateHigh}>1.000 (100.0%)</td>
                  <td className={styles.winRateHigh}>0.900</td>
                  <td>3.821.5</td>
                  <td>48.72 ms</td>
                  <td>{lang === 'vi' ? 'Đủ không gian tìm kiếm, duy trì toàn thắng tuyệt đối' : 'Sufficient search capacity, maintains 100% win rate'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Scientific Callout Box: Horizon Effect */}
          <div className={styles.envCard} style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(30, 15, 20, 0.6)' }}>
            <span className={styles.envBadge} style={{ color: '#ef4444' }}>⚠️</span>
            <div>
              <strong style={{ color: '#ef4444', marginRight: '0.5rem' }}>
                {lang === 'vi' ? 'Phát hiện khoa học — Hiện tượng Chân trời (Horizon Effect):' : 'Key Scientific Finding — Horizon Effect:'}
              </strong>
              <span>
                {lang === 'vi'
                  ? 'Khi giới hạn ngân sách tìm kiếm dưới 1.000 nút, Minimax bị ngắt giữa chừng ở tầng MIN khiến tỷ lệ thắng sụp về 0.0%. Khi cấp ngân sách vượt ngưỡng tới hạn N* ≥ 2.000 nút (hoàn tất đánh giá đòn phản công của đối thủ), tỷ lệ thắng hồi phục mạnh mẽ lên 72.7% và đạt 100.0% tại 5.000 nút.'
                  : 'When search budget is capped under 1,000 nodes, Minimax is prematurely truncated in the MIN ply, dropping win rate to 0.0%. When budget exceeds critical threshold N* ≥ 2,000 nodes (fully evaluating opponent counter-threats), win rate rebounds to 72.7% and reaches 100.0% at 5,000 nodes.'}
              </span>
            </div>
          </div>

          {/* Charts Grid 10: 8 Comprehensive Charts */}
          <div className={styles.galleryGrid}>
            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_01_minimax_vs_baselines_score_ci.png',
                  lang === 'vi'
                    ? 'Hình 4.14: Tỷ lệ điểm số Score và 95% Bootstrap CI của Minimax d=2 trước 3 baseline (1.200 ván)'
                    : 'Fig 4.14: Minimax d=2 Score Ratio and 95% Bootstrap CI vs 3 Baselines (1,200 matches)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_01_minimax_vs_baselines_score_ci.png"
                  alt="Minimax Score vs Baselines"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Điểm số Score & 95% CI vs Baselines' : 'Score Ratio & 95% CI vs Baselines'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_02_wdl_comparison.png',
                  lang === 'vi'
                    ? 'Hình 4.15: Phân phối Thắng / Hòa / Thua qua 6 cặp đấu (Toàn thắng 100% ở default)'
                    : 'Fig 4.15: Win / Draw / Loss Distribution Across 6 Matchups'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_02_wdl_comparison.png"
                  alt="Minimax WDL Comparison"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân phối Thắng/Hòa/Thua qua 6 cặp đấu' : 'W/D/L Distribution across 6 Matchups'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_07_ablation_search_budget_curve.png',
                  lang === 'vi'
                    ? 'Hình 4.16: Đường cong độ nhạy ngân sách nút (500 -> 5000) & Hiện tượng Chân trời (Horizon Effect)'
                    : 'Fig 4.16: Node Budget Sensitivity Curve (500 to 5000) & Horizon Effect'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_07_ablation_search_budget_curve.png"
                  alt="Search Budget Curve"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Độ nhạy ngân sách nút & Horizon Effect' : 'Budget Sensitivity & Horizon Effect'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_06_ablation_depth_1_vs_2.png',
                  lang === 'vi'
                    ? 'Hình 4.17: Ablation độ sâu d=1 vs d=2 (Hiệu năng, số nút duyệt và chất lượng chiến thuật)'
                    : 'Fig 4.17: Depth Ablation d=1 vs d=2 (Performance & Tactical Quality)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_06_ablation_depth_1_vs_2.png"
                  alt="Depth Ablation d=1 vs d=2"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Ablation độ sâu: d=1 vs d=2' : 'Depth Ablation: d=1 vs d=2'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_04_latency_and_budget_comparison.png',
                  lang === 'vi'
                    ? 'Hình 4.18: Độ trễ phản hồi thời gian thực và kiểm soát ngưỡng trần 1000 ms của Minimax'
                    : 'Fig 4.18: Decision Latency and 1000 ms Time Budget Compliance'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_04_latency_and_budget_comparison.png"
                  alt="Minimax Latency Comparison"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Độ trễ và kiểm soát trần thời gian 1000 ms' : 'Latency & 1000 ms Budget Compliance'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_03_nodes_visited_and_nps.png',
                  lang === 'vi'
                    ? 'Hình 4.19: Số nút duyệt trung bình và tốc độ duyệt nút (NPS) qua các cặp đối đầu'
                    : 'Fig 4.19: Nodes Visited and NPS Across Matchup Pairs'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_03_nodes_visited_and_nps.png"
                  alt="Nodes Visited and NPS"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Số nút duyệt trung bình & NPS' : 'Nodes Visited & NPS'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_05_red_vs_blue_advantage.png',
                  lang === 'vi'
                    ? 'Hình 4.20: Phân tích lợi thế đi trước Đỏ vs Xanh (Minimax khắc phục bất lợi khi cầm quân Xanh)'
                    : 'Fig 4.20: First-Move Advantage Analysis (Red vs Blue)'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_05_red_vs_blue_advantage.png"
                  alt="Red vs Blue Advantage"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân tích lợi thế đi trước (Đỏ vs Xanh)' : 'First-Move Advantage (Red vs Blue)'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>

            <div
              className={styles.chartCard}
              onClick={() =>
                openZoom(
                  '/assets/stats/exp10_fig_09_game_length_distribution.png',
                  lang === 'vi'
                    ? 'Hình 4.21: Phân phối độ dài ván đấu của tác tử Minimax d=2 (kết thúc ván quyết liệt)'
                    : 'Fig 4.21: Game Length Distribution for Minimax d=2'
                )
              }
            >
              <div className={styles.chartImgWrapper}>
                <img
                  src="/assets/stats/exp10_fig_09_game_length_distribution.png"
                  alt="Game Length Distribution"
                  className={styles.chartImg}
                />
              </div>
              <div className={styles.chartCaption}>
                <span>{lang === 'vi' ? 'Phân phối độ dài số nước đi ván đấu' : 'Game Length Distribution'}</span>
                <span className={styles.zoomHint}>{t.stats.btnZoom}</span>
              </div>
            </div>
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

