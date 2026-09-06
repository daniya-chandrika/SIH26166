/**
 * SIH26166 – Scientific Lunar Image Registration System
 * Dashboard Frontend Controller & API Integration Engine
 * Pure Vanilla JavaScript (Modular, Clean, Zero heavy dependencies)
 */

(() => {
  'use strict';

  // =========================================================================
  // API Base Configuration (Same-Origin Default)
  // =========================================================================
  const API_BASE = window.location.origin;

  // =========================================================================
  // Application State
  // =========================================================================
  const state = {
    allRuns: [],
    activeRunId: null,
    activeRunDetails: null,
    summaryData: null,
    healthData: null,
    scenarios: [],
    selectedRunsForCompare: new Set(),
    activeJobs: new Map(), // job_id -> status
    currentView: 'dashboard',
    activeVizTab: 'curtain',
    autoRefreshInterval: 5000,
    autoRefreshTimer: null,
    zoomScale: 1.0,
  };

  // =========================================================================
  // DOM Cache
  // =========================================================================
  const dom = {
    // Header
    statusPill: document.getElementById('header-status-pill'),
    statusDot: document.getElementById('header-status-dot'),
    statusText: document.getElementById('header-status-text'),
    syncTime: document.getElementById('header-sync-time'),
    toggleAutoRefresh: document.getElementById('toggle-auto-refresh'),
    btnRefresh: document.getElementById('btn-refresh'),
    btnOpenModal: document.getElementById('btn-open-run-modal'),
    toastHub: document.getElementById('toast-hub'),

    // Nav
    navItems: document.querySelectorAll('.nav-item'),
    navBadgeRuns: document.getElementById('nav-badge-runs-count'),
    viewPanels: document.querySelectorAll('.view-panel'),

    // Dashboard Hero & KPIs
    activeRunSelect: document.getElementById('active-run-select'),
    heroExpTitle: document.getElementById('hero-experiment-title'),
    heroExpSub: document.getElementById('hero-experiment-sub'),
    heroScenarioPill: document.getElementById('hero-scenario-pill'),
    heroStatusPill: document.getElementById('hero-status-pill'),
    heroMetaDetector: document.getElementById('hero-meta-detector'),
    heroMetaGeometry: document.getElementById('hero-meta-geometry'),
    heroMetaSeed: document.getElementById('hero-meta-seed'),
    heroMetaSubpixel: document.getElementById('hero-meta-subpixel'),

    kpiValTotal: document.getElementById('kpi-val-total'),
    kpiValSuccess: document.getElementById('kpi-val-success'),
    kpiValFailed: document.getElementById('kpi-val-failed'),
    kpiValRmse: document.getElementById('kpi-val-rmse'),
    kpiValInlier: document.getElementById('kpi-val-inlier'),
    kpiValCoverage: document.getElementById('kpi-val-coverage'),
    kpiValBestQuality: document.getElementById('kpi-val-best-quality'),
    kpiValActive: document.getElementById('kpi-val-active'),

    // Card 1: Upload / Trigger
    dropzoneTrigger: document.getElementById('dropzone-trigger'),
    btnTriggerActiveRun: document.getElementById('btn-trigger-active-run'),
    btnQuickConfig: document.getElementById('btn-quick-config'),

    // Card 2: Pipeline & Terminal
    pipelineStatusTag: document.getElementById('pipeline-status-tag'),
    pipelineStatusLabel: document.getElementById('pipeline-status-label'),
    processingLogBody: document.getElementById('processing-log-body'),
    logAutoscroll: document.getElementById('log-autoscroll'),
    btnCopyLog: document.getElementById('btn-copy-log'),

    // Card 3: Results & Quality
    resultStatusBanner: document.getElementById('result-status-banner'),
    resultStatusTitle: document.getElementById('result-status-title'),
    gaugeScoreFill: document.getElementById('gauge-score-fill'),
    gaugeScoreNum: document.getElementById('gauge-score-num'),
    gaugeScoreVerdict: document.getElementById('gauge-score-verdict'),
    resInlierRatio: document.getElementById('res-inlier-ratio'),
    resRmsePx: document.getElementById('res-rmse-px'),
    resNccVal: document.getElementById('res-ncc-val'),
    resSpatialCov: document.getElementById('res-spatial-cov'),

    paramEstTx: document.getElementById('param-est-tx'),
    paramGtTx: document.getElementById('param-gt-tx'),
    paramStatusTx: document.getElementById('param-status-tx'),
    paramEstTy: document.getElementById('param-est-ty'),
    paramGtTy: document.getElementById('param-gt-ty'),
    paramStatusTy: document.getElementById('param-status-ty'),
    paramEstRot: document.getElementById('param-est-rot'),
    paramGtRot: document.getElementById('param-gt-rot'),
    paramStatusRot: document.getElementById('param-status-rot'),
    paramEstScale: document.getElementById('param-est-scale'),
    paramGtScale: document.getElementById('param-gt-scale'),
    paramStatusScale: document.getElementById('param-status-scale'),

    btnViewDetailedReport: document.getElementById('btn-view-detailed-report'),
    btnDownloadReport: document.getElementById('btn-download-report'),

    // Card 4: Registered Images Thumbnails
    thumbImgSource: document.getElementById('thumb-img-source'),
    thumbImgReference: document.getElementById('thumb-img-reference'),
    thumbImgRegistered: document.getElementById('thumb-img-registered'),
    thumbImgDifference: document.getElementById('thumb-img-difference'),
    thumbAlignedSummary: document.getElementById('thumb-aligned-summary'),

    // Card 5: Interactive Visual Stage
    vizTabBtns: document.querySelectorAll('.viz-tab-btn'),
    stageViewport: document.getElementById('stage-viewport'),
    vizOpacityControlGroup: document.getElementById('viz-opacity-control-group'),
    vizOpacitySlider: document.getElementById('viz-opacity-slider'),
    vizOpacityVal: document.getElementById('viz-opacity-val'),
    vizCurtainInstructions: document.getElementById('viz-curtain-instructions'),
    btnZoomIn: document.getElementById('btn-zoom-in'),
    btnZoomOut: document.getElementById('btn-zoom-out'),
    btnZoomReset: document.getElementById('btn-zoom-reset'),
    btnFullscreenViz: document.getElementById('btn-fullscreen-viz'),

    curtainContainer: document.getElementById('curtain-container'),
    curtainImgBg: document.getElementById('curtain-img-bg'),
    curtainImgFg: document.getElementById('curtain-img-fg'),
    curtainOverlay: document.getElementById('curtain-overlay'),
    curtainDivider: document.getElementById('curtain-divider'),

    overlayImgBg: document.getElementById('overlay-img-bg'),
    overlayImgFg: document.getElementById('overlay-img-fg'),

    imgStageInliers: document.getElementById('img-stage-inliers'),
    imgStageCheckerboard: document.getElementById('img-stage-checkerboard'),
    imgStageAlignment: document.getElementById('img-stage-alignment'),
    imgStageDifference: document.getElementById('img-stage-difference'),
    imgStageSummary: document.getElementById('img-stage-summary'),

    // Card 6: History Table
    historyTable: document.getElementById('history-table'),
    historyTbody: document.getElementById('history-tbody'),
    historySearchInput: document.getElementById('history-search-input'),
    historyScenarioFilter: document.getElementById('history-scenario-filter'),
    historyStatusFilter: document.getElementById('history-status-filter'),
    checkAllRuns: document.getElementById('check-all-runs'),
    compareBar: document.getElementById('compare-bar'),
    compareCountText: document.getElementById('compare-count-text'),
    btnTriggerComparison: document.getElementById('btn-trigger-comparison'),

    // Card 7: Comparison Chart
    comparisonSvg: document.getElementById('comparison-svg'),
    chartMeanRmse: document.getElementById('chart-mean-rmse'),

    // Card 8: Evidence
    evDatasetScenario: document.getElementById('ev-dataset-scenario'),
    evCornerRmse: document.getElementById('ev-corner-rmse'),
    evFrobeniusDiff: document.getElementById('ev-frobenius-diff'),
    evAuditStatus: document.getElementById('ev-audit-status'),
    btnEvidenceDownload: document.getElementById('btn-evidence-download'),

    // Modal
    runModal: document.getElementById('run-modal'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    btnCancelModal: document.getElementById('btn-cancel-modal'),
    triggerForm: document.getElementById('trigger-form'),
    modalScenario: document.getElementById('modal-scenario'),
    modalScenarioHint: document.getElementById('modal-scenario-hint'),
    modalProgressArea: document.getElementById('modal-progress-area'),
    modalProgressStatus: document.getElementById('modal-progress-status'),
    modalProgressSub: document.getElementById('modal-progress-sub'),
    btnSubmitRun: document.getElementById('btn-submit-run'),

    // Standalone Config Form
    standaloneForm: document.getElementById('standalone-trigger-form'),
    pageScenarioSelect: document.getElementById('page-scenario-select'),
    pageScenarioDesc: document.getElementById('page-scenario-desc'),

    // Other Views Targets
    experimentsFullTarget: document.getElementById('experiments-full-table-target'),
    fullMatrixDisplay: document.getElementById('full-matrix-display'),
    fullParamsDisplay: document.getElementById('full-params-display'),
    fullJsonViewer: document.getElementById('full-json-viewer'),
    fullGalleryGrid: document.getElementById('full-gallery-grid'),
    evidenceDetailCard: document.getElementById('evidence-detail-card'),
    systemDiagnosticsGrid: document.getElementById('system-diagnostics-grid'),
    settingPollInterval: document.getElementById('setting-poll-interval'),

    // Lightbox
    lightboxModal: document.getElementById('lightbox-modal'),
    lightboxImg: document.getElementById('lightbox-img'),
    lightboxTitle: document.getElementById('lightbox-title'),
    btnCloseLightbox: document.getElementById('btn-close-lightbox'),
  };

  // =========================================================================
  // HTML Safety Utility (Prevents XSS)
  // =========================================================================
  function escapeHTML(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // =========================================================================
  // Toast Notification System
  // =========================================================================
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '&#x2713;' : type === 'error' ? '&#x26A0;' : '&#x2139;';
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHTML(message)}</span>`;
    dom.toastHub.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // =========================================================================
  // API Fetch Helpers
  // =========================================================================
  async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, options);
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status}: ${errText || res.statusText}`);
    }
    return res;
  }

  async function fetchJSON(endpoint, options = {}) {
    const res = await fetchAPI(endpoint, options);
    return res.json();
  }

  // =========================================================================
  // Data Loading & Syncing
  // =========================================================================
  async function syncAllData(isBackground = false) {
    try {
      // 1. Fetch Health & Summary in parallel
      const [health, summary, scenariosRes, runsData] = await Promise.all([
        fetchJSON('/api/health').catch(err => ({ status: 'OFFLINE', error: err.message })),
        fetchJSON('/api/summary').catch(() => null),
        fetchJSON('/api/scenarios').catch(() => ({ scenarios: [] })),
        fetchJSON('/api/runs').catch(() => ({ runs: [] })),
      ]);

      state.healthData = health;
      state.summaryData = summary;
      state.scenarios = scenariosRes.scenarios || [];
      state.allRuns = runsData.runs || [];

      renderHealth();
      renderSummary();
      populateScenarioDropdowns();
      renderRunsSelector();
      renderHistoryTable();
      renderComparativeChart();

      // If we have an active run, refresh its details
      if (state.activeRunId) {
        await loadRunDetails(state.activeRunId, isBackground);
      } else if (state.allRuns.length > 0) {
        await selectRun(state.allRuns[0].id);
      } else {
        renderEmptyState();
      }

      // Check active background jobs
      await pollActiveJobs();

      // Update sync time
      const now = new Date();
      dom.syncTime.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      if (!isBackground) {
        showToast('Dashboard synchronized with lunar engine.', 'success');
      }
    } catch (err) {
      console.error('Data sync error:', err);
      renderHealthOffline();
      if (!isBackground) {
        showToast(`Sync failed: ${err.message}`, 'error');
      }
    }
  }

  // =========================================================================
  // Health & System Status Rendering
  // =========================================================================
  function renderHealth() {
    const h = state.healthData;
    if (!h) return;

    const status = (h.status || 'UNKNOWN').toUpperCase();
    dom.statusText.textContent = `${status} (${h.database_mode || 'OFFLINE'})`;

    dom.statusPill.className = 'system-status-pill';
    if (status === 'ONLINE') {
      // default green
    } else if (status === 'PROCESSING') {
      dom.statusPill.classList.add('status-processing');
    } else {
      dom.statusPill.classList.add('status-offline');
    }

    // Render System Status View if open
    if (state.currentView === 'system') {
      renderSystemStatusView();
    }
  }

  function renderHealthOffline() {
    dom.statusText.textContent = 'OFFLINE';
    dom.statusPill.className = 'system-status-pill status-offline';
  }

  function renderSystemStatusView() {
    const h = state.healthData || {};
    dom.systemDiagnosticsGrid.innerHTML = `
      <div class="diag-card">
        <div class="diag-title">Engine Health Status</div>
        <div class="diag-val text-emerald">${escapeHTML(h.status || 'OFFLINE')}</div>
      </div>
      <div class="diag-card">
        <div class="diag-title">Scientific Service</div>
        <div class="diag-val text-cyan" style="font-size: 0.95rem;">${escapeHTML(h.service || 'SIH26166 Pipeline')}</div>
      </div>
      <div class="diag-card">
        <div class="diag-title">Database Subsystem</div>
        <div class="diag-val text-amber" style="font-size: 0.95rem;">${escapeHTML(h.database_mode || 'OFFLINE / MOCK MODE')}</div>
      </div>
      <div class="diag-card">
        <div class="diag-title">Python Runtime</div>
        <div class="diag-val font-mono">${escapeHTML(h.python_version || '3.11')}</div>
      </div>
      <div class="diag-card">
        <div class="diag-title">Archived Experiments</div>
        <div class="diag-val font-mono text-cyan">${h.total_runs_on_disk || state.allRuns.length} runs</div>
      </div>
      <div class="diag-card">
        <div class="diag-title">Active Workers</div>
        <div class="diag-val font-mono text-emerald">${h.active_processing_jobs || 0} active</div>
      </div>
    `;
  }

  // =========================================================================
  // Top KPI Area Rendering (From Real Backend Summary)
  // =========================================================================
  function renderSummary() {
    const s = state.summaryData;
    if (!s) return;

    dom.kpiValTotal.textContent = s.total_experiments ?? state.allRuns.length;
    dom.kpiValSuccess.textContent = s.successful_experiments ?? '--';
    dom.kpiValFailed.textContent = s.failed_experiments ?? '--';

    dom.kpiValRmse.textContent = s.average_rmse != null ? `${s.average_rmse.toFixed(3)} px` : 'N/A';
    dom.kpiValInlier.textContent = s.average_inlier_ratio != null ? `${(s.average_inlier_ratio * 100).toFixed(1)}%` : 'N/A';
    dom.kpiValCoverage.textContent = s.average_spatial_coverage != null ? `${s.average_spatial_coverage.toFixed(1)}%` : 'N/A';

    dom.kpiValBestQuality.textContent = s.best_registration_quality != null ? s.best_registration_quality.toFixed(3) : 'N/A';
    dom.kpiValActive.textContent = s.active_processing_runs ?? state.activeJobs.size;

    dom.navBadgeRuns.textContent = state.allRuns.length;
  }

  // =========================================================================
  // Dropdown Scenario Population
  // =========================================================================
  function populateScenarioDropdowns() {
    const scenarios = state.scenarios;
    if (!scenarios || scenarios.length === 0) return;

    // Filter select in history table
    const currentHistVal = dom.historyScenarioFilter.value;
    dom.historyScenarioFilter.innerHTML = '<option value="ALL">All Scenarios</option>' +
      scenarios.map(sc => `<option value="${escapeHTML(sc.id)}">${escapeHTML(sc.name)}</option>`).join('');
    if (currentHistVal) dom.historyScenarioFilter.value = currentHistVal;

    // Modal select
    dom.modalScenario.innerHTML = scenarios.map(sc =>
      `<option value="${escapeHTML(sc.id)}">${escapeHTML(sc.name)}</option>`
    ).join('');

    // Standalone page select
    dom.pageScenarioSelect.innerHTML = scenarios.map(sc =>
      `<option value="${escapeHTML(sc.id)}">${escapeHTML(sc.name)}</option>`
    ).join('');

    // Update scenario description on change
    const updateModalHint = () => {
      const selected = scenarios.find(s => s.id === dom.modalScenario.value);
      dom.modalScenarioHint.textContent = selected ? selected.description : '';
    };
    dom.modalScenario.onchange = updateModalHint;
    updateModalHint();

    const updatePageHint = () => {
      const selected = scenarios.find(s => s.id === dom.pageScenarioSelect.value);
      dom.pageScenarioDesc.textContent = selected ? selected.description : '';
    };
    dom.pageScenarioSelect.onchange = updatePageHint;
    updatePageHint();
  }

  // =========================================================================
  // Runs Selector in Header / Hero
  // =========================================================================
  function renderRunsSelector() {
    const runs = state.allRuns;
    if (runs.length === 0) {
      dom.activeRunSelect.innerHTML = '<option value="">No experiment runs available</option>';
      return;
    }

    dom.activeRunSelect.innerHTML = runs.map(r => {
      const scenario = r.config?.scenario || 'COMBINED';
      const statusSymbol = r.success ? '✓' : '✗';
      const dateStr = new Date(r.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return `<option value="${escapeHTML(r.id)}" ${r.id === state.activeRunId ? 'selected' : ''}>
        ${statusSymbol} ${escapeHTML(r.id)} [${escapeHTML(scenario.toUpperCase())} &bull; ${dateStr}]
      </option>`;
    }).join('');
  }

  // =========================================================================
  // Select and Load Run Details
  // =========================================================================
  async function selectRun(runId) {
    if (!runId) return;
    state.activeRunId = runId;
    renderRunsSelector();
    await loadRunDetails(runId, false);
  }

  async function loadRunDetails(runId, isSilent = false) {
    try {
      const details = await fetchJSON(`/api/run/${encodeURIComponent(runId)}/details`);
      state.activeRunDetails = details;
      renderActiveRun(details);
    } catch (err) {
      console.error(`Failed to load details for run ${runId}:`, err);
      if (!isSilent) showToast(`Failed to load run ${runId}`, 'error');
    }
  }

  // =========================================================================
  // Render Active Run Details Across All Cards
  // =========================================================================
  function renderActiveRun(d) {
    if (!d) return;

    const m = d.metrics || {};
    const t = d.transform || {};
    const cfg = d.config || {};
    const gt = d.ground_truth || {};
    const isSuccess = d.success;

    // --- Hero Banner ---
    const scenario = cfg.scenario || 'COMBINED';
    dom.heroScenarioPill.textContent = `SCENARIO: ${scenario.toUpperCase()}`;
    dom.heroExpTitle = document.getElementById('hero-experiment-title');
    if (dom.heroExpTitle) dom.heroExpTitle.textContent = d.id;

    const dateStr = new Date(d.timestamp * 1000).toLocaleString();
    if (dom.heroExpSub) dom.heroExpSub.textContent = `Executed: ${dateStr} | Random Seed: ${cfg.seed ?? 42} | Grid: ${cfg.grid ?? '8x8'}`;

    dom.heroStatusPill.textContent = isSuccess ? 'SUCCESS' : 'FAILED';
    dom.heroStatusPill.className = `status-pill ${isSuccess ? 'status-success' : 'status-failed'}`;

    dom.heroMetaDetector.textContent = (cfg.detector || 'SIFT').toUpperCase();
    dom.heroMetaGeometry.textContent = (cfg.model || 'HOMOGRAPHY').toUpperCase();
    dom.heroMetaSeed.textContent = cfg.seed ?? '42';
    dom.heroMetaSubpixel.textContent = m.subpixel_convergence_rate != null ? 'ENABLED (NCC)' : 'DISABLED';

    // --- Card 2: Pipeline Stepper & Logs ---
    renderPipelineProgress(d);
    renderTerminalLogs(d.logs || '');

    // --- Card 3: Registration Results & Quality Score ---
    renderQualityScoreCard(d);

    // --- Card 4: Registered Image Thumbnails ---
    renderRegisteredThumbnails(d);

    // --- Card 5: Interactive Visual Stage Images ---
    renderVisualizationStage(d);

    // --- Card 8: Scientific Evidence & Ground Truth ---
    renderScientificEvidence(d);

    // --- Full Results View ---
    renderFullResultsView(d);

    // --- Full Gallery View ---
    renderFullGalleryView(d);

    // Update active row in history table
    document.querySelectorAll('.history-table tbody tr').forEach(row => {
      row.classList.toggle('active', row.dataset.runId === d.id);
    });
  }

  // =========================================================================
  // Pipeline Stepper Progress Renderer
  // =========================================================================
  function renderPipelineProgress(d) {
    const isSuccess = d.success;
    const isRunning = d.status === 'RUNNING';
    const isFailed = d.status === 'FAILED' || (d.status !== 'SUCCESS' && !isRunning);

    dom.pipelineStatusLabel.textContent = d.status || 'IDLE';
    dom.pipelineStatusTag.style.color = isSuccess ? 'var(--accent-emerald)' : isRunning ? 'var(--accent-cyan)' : 'var(--accent-rose)';

    // 8 stages
    for (let i = 1; i <= 8; i++) {
      const node = document.getElementById(`pipe-stage-${i}`);
      const line = document.getElementById(`pipe-line-${i}`);
      if (!node) continue;

      node.className = 'step-node';
      if (line) line.className = 'step-line';

      if (isSuccess) {
        node.classList.add('completed');
        if (line) line.classList.add('active');
      } else if (isRunning) {
        if (i < 5) node.classList.add('completed');
        else if (i === 5) node.classList.add('running');
      } else if (isFailed) {
        if (i <= 4) node.classList.add('completed');
        else if (i === 5) node.classList.add('failed');
      }
    }
  }

  // =========================================================================
  // Terminal Logs Renderer
  // =========================================================================
  function renderTerminalLogs(rawLogs) {
    if (!rawLogs) {
      dom.processingLogBody.innerHTML = '<div class="log-line text-muted">No execution logs recorded for this experiment run.</div>';
      return;
    }

    const lines = rawLogs.split('\n');
    const formattedHtml = lines.map(line => {
      let escaped = escapeHTML(line);
      // Highlight SUCCESS in green, FAILED in red, info in cyan
      escaped = escaped
        .replace(/(SUCCESS)/g, '<span class="log-success">$1</span>')
        .replace(/(FAILED|ERROR)/g, '<span class="log-fail">$1</span>')
        .replace(/(\[\d+\/\d+\])/g, '<span class="log-info">$1</span>')
        .replace(/(\[\d{2}:\d{2}:\d{2}\])/g, '<span class="log-ts">$1</span>');
      return `<div class="log-line">${escaped}</div>`;
    }).join('');

    dom.processingLogBody.innerHTML = formattedHtml;

    if (dom.logAutoscroll.checked) {
      dom.processingLogBody.scrollTop = dom.processingLogBody.scrollHeight;
    }
  }

  // =========================================================================
  // Registration Quality Score & Metrics Card Renderer
  // =========================================================================
  function renderQualityScoreCard(d) {
    const m = d.metrics || {};
    const t = d.transform || {};
    const isSuccess = d.success;

    // Status Banner
    dom.resultStatusTitle.textContent = isSuccess ? 'Registration Successful!' : 'Registration Incomplete / Failed';
    dom.resultStatusBanner.className = `result-status-pill ${isSuccess ? '' : 'failed'}`;

    // Quality Score (0.0 to 1.0)
    const score = d.quality_score != null ? d.quality_score : 0.0;
    dom.gaugeScoreNum.textContent = score > 0 ? score.toFixed(2) : '--';

    // SVG Circumference = 2 * PI * 50 = 314.159
    const circumference = 314.159;
    const offset = circumference * (1 - Math.min(1.0, Math.max(0.0, score)));
    dom.gaugeScoreFill.style.strokeDasharray = `${circumference}`;
    dom.gaugeScoreFill.style.strokeDashoffset = `${offset}`;

    if (score >= 0.85) {
      dom.gaugeScoreVerdict.textContent = 'Excellent';
      dom.gaugeScoreFill.style.stroke = 'var(--accent-emerald)';
    } else if (score >= 0.65) {
      dom.gaugeScoreVerdict.textContent = 'Optimal';
      dom.gaugeScoreFill.style.stroke = 'var(--accent-cyan)';
    } else if (score > 0) {
      dom.gaugeScoreVerdict.textContent = 'Acceptable';
      dom.gaugeScoreFill.style.stroke = 'var(--accent-amber)';
    } else {
      dom.gaugeScoreVerdict.textContent = 'Failed';
      dom.gaugeScoreFill.style.stroke = 'var(--accent-rose)';
    }

    // Key Metric Pills
    dom.resInlierRatio.textContent = m.inlier_ratio != null ? `${(m.inlier_ratio * 100).toFixed(1)}%` : '--';
    const rmseVal = m.reprojection_rmse_px ?? m.rmse;
    dom.resRmsePx.textContent = rmseVal != null ? `${rmseVal.toFixed(3)} px` : '--';
    dom.resNccVal.textContent = m.normalized_cross_correlation != null ? m.normalized_cross_correlation.toFixed(3) : 'N/A';
    dom.resSpatialCov.textContent = m.spatial_coverage_percentage != null ? `${m.spatial_coverage_percentage.toFixed(1)}%` : '--';

    // Ground Truth vs Estimated Parameters Table
    const gtMetrics = m.ground_truth_metrics || {};
    const matrix = t.matrix;

    let estTx = '--', estTy = '--', estRot = '--', estScale = '--';
    let gtTx = '--', gtTy = '--', gtRot = '--', gtScale = '--';

    if (gtMetrics.estimated_translation_px) {
      estTx = `${gtMetrics.estimated_translation_px[0]?.toFixed(2)} px`;
      estTy = `${gtMetrics.estimated_translation_px[1]?.toFixed(2)} px`;
    }
    if (gtMetrics.ground_truth_translation_px) {
      gtTx = `${gtMetrics.ground_truth_translation_px[0]?.toFixed(2)} px`;
      gtTy = `${gtMetrics.ground_truth_translation_px[1]?.toFixed(2)} px`;
    }

    if (gtMetrics.estimated_rotation_deg != null) estRot = `${gtMetrics.estimated_rotation_deg.toFixed(2)}°`;
    if (gtMetrics.ground_truth_rotation_deg != null) gtRot = `${gtMetrics.ground_truth_rotation_deg.toFixed(2)}°`;

    if (gtMetrics.estimated_scale != null) estScale = `${gtMetrics.estimated_scale.toFixed(3)}×`;
    if (gtMetrics.ground_truth_scale != null) gtScale = `${gtMetrics.ground_truth_scale.toFixed(3)}×`;

    dom.paramEstTx.textContent = estTx;
    dom.paramGtTx.textContent = `(Expected: ${gtTx})`;
    dom.paramEstTy.textContent = estTy;
    dom.paramGtTy.textContent = `(Expected: ${gtTy})`;
    dom.paramEstRot.textContent = estRot;
    dom.paramGtRot.textContent = `(Expected: ${gtRot})`;
    dom.paramEstScale.textContent = estScale;
    dom.paramGtScale.textContent = `(Expected: ${gtScale})`;

    const checkIcon = isSuccess ? '✓' : '✗';
    dom.paramStatusTx.textContent = checkIcon;
    dom.paramStatusTy.textContent = checkIcon;
    dom.paramStatusRot.textContent = checkIcon;
    dom.paramStatusScale.textContent = checkIcon;
  }

  // =========================================================================
  // Registered Images Thumbnails Renderer
  // =========================================================================
  function renderRegisteredThumbnails(d) {
    const base = `${API_BASE}/api/run/${encodeURIComponent(d.id)}`;

    dom.thumbImgSource.src = `${base}/registered/source.png`;
    dom.thumbImgReference.src = `${base}/registered/reference.png`;
    dom.thumbImgRegistered.src = `${base}/registered/registered.png`;
    dom.thumbImgDifference.src = `${base}/registered/difference.png`;
    dom.thumbAlignedSummary.src = `${base}/visualizations/03_registration_alignment.png`;
  }

  // =========================================================================
  // Visualization Stage Renderer
  // =========================================================================
  function renderVisualizationStage(d) {
    const base = `${API_BASE}/api/run/${encodeURIComponent(d.id)}`;

    // Curtain images
    dom.curtainImgBg.src = `${base}/registered/registered.png`;
    dom.curtainImgFg.src = `${base}/registered/reference.png`;

    // Overlay blend images
    dom.overlayImgBg.src = `${base}/registered/reference.png`;
    dom.overlayImgFg.src = `${base}/registered/registered.png`;

    // Single visual image tabs
    dom.imgStageInliers.src = `${base}/visualizations/02_inlier_matches.png`;
    dom.imgStageCheckerboard.src = `${base}/visualizations/04_checkerboard_and_blend.png`;
    dom.imgStageAlignment.src = `${base}/visualizations/03_registration_alignment.png`;
    dom.imgStageDifference.src = `${base}/registered/difference.png`;
    dom.imgStageSummary.src = `${base}/visualizations/registration_dashboard_summary.png`;
  }

  // =========================================================================
  // Scientific Evidence & Ground Truth Renderer
  // =========================================================================
  function renderScientificEvidence(d) {
    const m = d.metrics || {};
    const gtMetrics = m.ground_truth_metrics || {};
    const cfg = d.config || {};

    dom.evDatasetScenario.textContent = (cfg.scenario || 'COMBINED').toUpperCase();

    if (gtMetrics.corner_reprojection_rmse_px != null) {
      dom.evCornerRmse.textContent = `${gtMetrics.corner_reprojection_rmse_px.toFixed(3)} px`;
    } else {
      dom.evCornerRmse.textContent = 'N/A';
    }

    if (gtMetrics.matrix_frobenius_norm_diff != null) {
      dom.evFrobeniusDiff.textContent = gtMetrics.matrix_frobenius_norm_diff.toFixed(4);
    } else {
      dom.evFrobeniusDiff.textContent = 'N/A';
    }

    if (d.success) {
      dom.evAuditStatus.textContent = 'Pass (Sub-pixel Precision Confirmed)';
      dom.evAuditStatus.className = 'ev-v text-emerald';
    } else {
      dom.evAuditStatus.textContent = 'Failed / Incomplete';
      dom.evAuditStatus.className = 'ev-v text-rose';
    }

    // Details View
    if (dom.evidenceDetailCard) {
      dom.evidenceDetailCard.innerHTML = `
        <div class="evidence-grid" style="font-size: 0.82rem;">
          <div class="evidence-row"><span class="ev-k">Experiment ID</span><span class="ev-v font-mono text-cyan">${escapeHTML(d.id)}</span></div>
          <div class="evidence-row"><span class="ev-k">Translation Error (&Delta;Trans)</span><span class="ev-v font-mono">${gtMetrics.translation_error_px != null ? gtMetrics.translation_error_px.toFixed(3) + ' px' : 'N/A'}</span></div>
          <div class="evidence-row"><span class="ev-k">Rotation Error (&Delta;Rot)</span><span class="ev-v font-mono">${gtMetrics.rotation_error_deg != null ? gtMetrics.rotation_error_deg.toFixed(3) + '°' : 'N/A'}</span></div>
          <div class="evidence-row"><span class="ev-k">Scale Error (&Delta;Scale)</span><span class="ev-v font-mono">${gtMetrics.scale_error != null ? gtMetrics.scale_error.toFixed(5) : 'N/A'}</span></div>
          <div class="evidence-row"><span class="ev-k">Corner Reprojection RMSE</span><span class="ev-v font-mono">${gtMetrics.corner_reprojection_rmse_px != null ? gtMetrics.corner_reprojection_rmse_px.toFixed(3) + ' px' : 'N/A'}</span></div>
          <div class="evidence-row"><span class="ev-k">Frobenius Norm Difference</span><span class="ev-v font-mono">${gtMetrics.matrix_frobenius_norm_diff != null ? gtMetrics.matrix_frobenius_norm_diff.toFixed(5) : 'N/A'}</span></div>
        </div>
      `;
    }
  }

  // =========================================================================
  // Full Results View (Matrix & JSON Viewers)
  // =========================================================================
  function renderFullResultsView(d) {
    const t = d.transform || {};
    const matrix = t.matrix;

    if (matrix && Array.isArray(matrix)) {
      const rows = matrix.map(r => `[ ${r.map(v => (typeof v === 'number' ? v.toFixed(6).padStart(12, ' ') : v)).join('   ')} ]`).join('\n');
      dom.fullMatrixDisplay.innerHTML = `<pre>${escapeHTML(rows)}</pre>`;
    } else {
      dom.fullMatrixDisplay.innerHTML = '<pre>No matrix recorded</pre>';
    }

    dom.fullJsonViewer.textContent = JSON.stringify(d, null, 2);
  }

  // =========================================================================
  // Full Visualizations Gallery View
  // =========================================================================
  function renderFullGalleryView(d) {
    const base = `${API_BASE}/api/run/${encodeURIComponent(d.id)}`;
    const vizFiles = d.visualizations || [
      '01_input_pair.png',
      '02_inlier_matches.png',
      '03_registration_alignment.png',
      '04_checkerboard_and_blend.png',
      'registration_dashboard_summary.png',
    ];
    const regFiles = d.registered || ['source.png', 'reference.png', 'registered.png', 'difference.png'];

    const allImages = [
      ...vizFiles.map(f => ({ name: f, path: `${base}/visualizations/${f}` })),
      ...regFiles.map(f => ({ name: `registered/${f}`, path: `${base}/registered/${f}` })),
    ];

    dom.fullGalleryGrid.innerHTML = allImages.map(img => `
      <div class="gallery-card">
        <span class="gallery-title">${escapeHTML(img.name)}</span>
        <img src="${escapeHTML(img.path)}" alt="${escapeHTML(img.name)}" loading="lazy" onclick="openLightbox('${escapeHTML(img.path)}', '${escapeHTML(img.name)}')" />
        <button class="btn btn-secondary btn-sm" onclick="openLightbox('${escapeHTML(img.path)}', '${escapeHTML(img.name)}')">Inspect Fullscreen</button>
      </div>
    `).join('');
  }

  // =========================================================================
  // Experiment History Table
  // =========================================================================
  function renderHistoryTable() {
    const runs = state.allRuns;
    if (runs.length === 0) {
      dom.historyTbody.innerHTML = '<tr><td colspan="8" class="table-loading-cell">No experiment runs found. Launch one above!</td></tr>';
      return;
    }

    const query = dom.historySearchInput.value.toLowerCase().trim();
    const scenarioFilter = dom.historyScenarioFilter.value;
    const statusFilter = dom.historyStatusFilter.value;

    const filtered = runs.filter(r => {
      const matchQuery = !query || r.id.toLowerCase().includes(query) || (r.config?.scenario || '').toLowerCase().includes(query);
      const matchScenario = scenarioFilter === 'ALL' || (r.config?.scenario || '').toLowerCase() === scenarioFilter.toLowerCase();
      const matchStatus = statusFilter === 'ALL' || (statusFilter === 'SUCCESS' ? r.success : !r.success);
      return matchQuery && matchScenario && matchStatus;
    });

    if (filtered.length === 0) {
      dom.historyTbody.innerHTML = '<tr><td colspan="8" class="table-loading-cell">No experiments match the filter criteria.</td></tr>';
      return;
    }

    dom.historyTbody.innerHTML = filtered.map(r => {
      const cfg = r.config || {};
      const m = r.metrics || {};
      const isSelected = state.selectedRunsForCompare.has(r.id);
      const isActive = r.id === state.activeRunId;
      const dateStr = new Date(r.timestamp * 1000).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
      const inlierPct = m.inlier_ratio != null ? `${(m.inlier_ratio * 100).toFixed(1)}%` : '--';
      const rmseVal = (m.reprojection_rmse_px ?? m.rmse) != null ? `${(m.reprojection_rmse_px ?? m.rmse).toFixed(2)}px` : '--';
      const qScore = r.quality_score != null ? r.quality_score.toFixed(2) : '--';
      const statusPill = r.success ? '<span class="status-pill status-success">SUCCESS</span>' : '<span class="status-pill status-failed">FAILED</span>';

      return `
        <tr data-run-id="${escapeHTML(r.id)}" class="${isActive ? 'active' : ''}">
          <td class="col-checkbox">
            <input type="checkbox" class="run-select-check" data-run-id="${escapeHTML(r.id)}" ${isSelected ? 'checked' : ''} />
          </td>
          <td><strong class="font-mono text-cyan">${escapeHTML(r.id)}</strong></td>
          <td class="text-muted">${escapeHTML(dateStr)}</td>
          <td><span class="scenario-pill">${escapeHTML((cfg.scenario || 'COMBINED').toUpperCase())}</span></td>
          <td>${escapeHTML((cfg.detector || 'SIFT').toUpperCase())} &bull; ${escapeHTML((cfg.model || 'HOMOGRAPHY').toUpperCase())}</td>
          <td><strong class="font-mono">${escapeHTML(qScore)}</strong></td>
          <td>${statusPill}</td>
          <td>
            <button class="tbl-action-btn" data-action="view" data-run-id="${escapeHTML(r.id)}">View</button>
            <button class="tbl-action-btn" data-action="report" data-run-id="${escapeHTML(r.id)}">Report</button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach listeners
    dom.historyTbody.querySelectorAll('.run-select-check').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const id = e.target.dataset.runId;
        if (e.target.checked) state.selectedRunsForCompare.add(id);
        else state.selectedRunsForCompare.delete(id);
        updateCompareBar();
      });
    });

    dom.historyTbody.querySelectorAll('[data-action="view"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectRun(btn.dataset.runId);
      });
    });

    dom.historyTbody.querySelectorAll('[data-action="report"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        downloadReport(btn.dataset.runId);
      });
    });

    dom.historyTbody.querySelectorAll('tr').forEach(tr => {
      tr.addEventListener('click', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
        selectRun(tr.dataset.runId);
      });
    });

    // Also populate full experiments view if active
    if (dom.experimentsFullTarget && state.currentView === 'experiments') {
      dom.experimentsFullTarget.innerHTML = dom.historyTable.outerHTML;
    }
  }

  function updateCompareBar() {
    const count = state.selectedRunsForCompare.size;
    if (count > 1) {
      dom.compareBar.style.display = 'flex';
      dom.compareCountText.textContent = `${count} runs selected for comparison`;
    } else {
      dom.compareBar.style.display = 'none';
    }
  }

  // =========================================================================
  // Comparative Analytics Dynamic SVG Chart
  // =========================================================================
  function renderComparativeChart() {
    const runs = state.allRuns.filter(r => r.metrics && r.metrics.reprojection_rmse_px != null || r.metrics?.rmse != null).reverse();
    if (runs.length === 0) return;

    const width = 480;
    const height = 180;
    const padX = 40;
    const padY = 20;

    const rmseList = runs.map(r => r.metrics.reprojection_rmse_px ?? r.metrics.rmse);
    const maxRmse = Math.max(3.0, Math.max(...rmseList) * 1.2);

    const stepX = (width - 2 * padX) / Math.max(1, runs.length - 1);

    const points = runs.map((r, i) => {
      const val = r.metrics.reprojection_rmse_px ?? r.metrics.rmse;
      const x = padX + i * stepX;
      const y = height - padY - (val / maxRmse) * (height - 2 * padY);
      return { x, y, val, id: r.id, detector: r.config?.detector || 'SIFT' };
    });

    // Build SVG Path
    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

    // Benchmark line at 1.0 px
    const benchY = height - padY - (1.0 / maxRmse) * (height - 2 * padY);

    dom.comparisonSvg.innerHTML = `
      <!-- Gridlines -->
      <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="rgba(148,163,184,0.2)" stroke-width="1" />
      <line x1="${padX}" y1="${padY}" x2="${width - padX}" y2="${padY}" stroke="rgba(148,163,184,0.1)" stroke-width="1" />
      
      <!-- Sub-pixel Benchmark Line (1.0 px) -->
      <line x1="${padX}" y1="${benchY}" x2="${width - padX}" y2="${benchY}" stroke="rgba(16,185,129,0.5)" stroke-width="1.5" stroke-dasharray="4" />
      <text x="${width - padX - 5}" y="${benchY - 4}" fill="#10b981" font-size="9" text-anchor="end" font-family="JetBrains Mono">1.0 px (Sub-pixel)</text>

      <!-- Area fill -->
      <path d="${pathD} L ${points[points.length - 1].x} ${height - padY} L ${points[0].x} ${height - padY} Z" fill="url(#chart-grad)" opacity="0.25" />

      <!-- Curve Line -->
      <path d="${pathD}" fill="none" stroke="#00e5ff" stroke-width="2.5" />

      <!-- Data Dots -->
      ${points.map(p => `
        <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4" fill="#060911" stroke="#00e5ff" stroke-width="2">
          <title>${escapeHTML(p.id)}: ${p.val.toFixed(3)} px</title>
        </circle>
      `).join('')}

      <defs>
        <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#00e5ff" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#00e5ff" stop-opacity="0"/>
        </linearGradient>
      </defs>
    `;

    const avgRmse = (rmseList.reduce((a, b) => a + b, 0) / rmseList.length).toFixed(3);
    dom.chartMeanRmse.textContent = `${avgRmse} px`;
  }

  // =========================================================================
  // Interactive Split Curtain Slider (Mouse & Touch Drag)
  // =========================================================================
  function setupCurtainSlider() {
    const container = dom.curtainContainer;
    const overlay = dom.curtainOverlay;
    const divider = dom.curtainDivider;
    let isDragging = false;

    const setPosition = (clientX) => {
      const rect = container.getBoundingClientRect();
      let x = clientX - rect.left;
      x = Math.max(0, Math.min(x, rect.width));
      const pct = (x / rect.width) * 100;
      overlay.style.width = `${pct}%`;
      divider.style.left = `${pct}%`;
    };

    container.addEventListener('mousedown', (e) => {
      isDragging = true;
      setPosition(e.clientX);
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      setPosition(e.clientX);
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    // Touch Support
    container.addEventListener('touchstart', (e) => {
      isDragging = true;
      if (e.touches[0]) setPosition(e.touches[0].clientX);
    });

    window.addEventListener('touchmove', (e) => {
      if (!isDragging || !e.touches[0]) return;
      setPosition(e.touches[0].clientX);
    });

    window.addEventListener('touchend', () => {
      isDragging = false;
    });

    // Overlay Opacity Slider
    dom.vizOpacitySlider.addEventListener('input', (e) => {
      const val = e.target.value;
      dom.vizOpacityVal.textContent = `${val}%`;
      dom.overlayImgFg.style.opacity = (val / 100).toString();
    });

    // Sub Tabs Switching
    dom.vizTabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        dom.vizTabBtns.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');

        const mode = btn.dataset.viz;
        state.activeVizTab = mode;

        document.querySelectorAll('.viz-mode-panel').forEach(p => p.classList.remove('active'));
        const activePanel = document.getElementById(`viz-panel-${mode}`);
        if (activePanel) activePanel.classList.add('active');

        // Toggle opacity control vs curtain instructions
        if (mode === 'overlay') {
          dom.vizOpacityControlGroup.style.display = 'flex';
          dom.vizCurtainInstructions.style.display = 'none';
        } else if (mode === 'curtain') {
          dom.vizOpacityControlGroup.style.display = 'none';
          dom.vizCurtainInstructions.style.display = 'block';
        } else {
          dom.vizOpacityControlGroup.style.display = 'none';
          dom.vizCurtainInstructions.style.display = 'none';
        }
      });
    });

    // Zoom Controls
    dom.btnZoomIn.addEventListener('click', () => {
      state.zoomScale = Math.min(3.0, state.zoomScale + 0.25);
      applyZoom();
    });
    dom.btnZoomOut.addEventListener('click', () => {
      state.zoomScale = Math.max(0.5, state.zoomScale - 0.25);
      applyZoom();
    });
    dom.btnZoomReset.addEventListener('click', () => {
      state.zoomScale = 1.0;
      applyZoom();
    });

    // Fullscreen View
    dom.btnFullscreenViz.addEventListener('click', () => {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        dom.stageViewport.requestFullscreen().catch(() => {});
      }
    });
  }

  function applyZoom() {
    const panels = document.querySelectorAll('.viz-mode-panel img');
    panels.forEach(img => {
      img.style.transform = `scale(${state.zoomScale})`;
      img.style.transition = 'transform 0.15s ease';
    });
  }

  // =========================================================================
  // Asynchronous Experiment Trigger & Polling
  // =========================================================================
  async function triggerExperiment(params) {
    showToast('Queuing registration pipeline in background...', 'info');

    try {
      const res = await fetchJSON('/api/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });

      const jobId = res.job_id;
      if (!jobId) throw new Error('No Job ID returned');

      state.activeJobs.set(jobId, 'QUEUED');
      showToast(`Job ${jobId} started asynchronously.`, 'info');

      // Poll this job until completion
      pollJobStatus(jobId);
      renderSummary();
    } catch (err) {
      console.error('Trigger failure:', err);
      showToast(`Execution trigger failed: ${err.message}`, 'error');
      throw err;
    }
  }

  async function pollJobStatus(jobId) {
    const pollInterval = 1500;
    const maxPolls = 120; // 3 minutes timeout
    let count = 0;

    const timer = setInterval(async () => {
      count++;
      try {
        const job = await fetchJSON(`/api/jobs/${encodeURIComponent(jobId)}`);
        const status = job.status;
        state.activeJobs.set(jobId, status);

        // Update modal progress if open
        if (dom.modalProgressArea.style.display !== 'none') {
          dom.modalProgressStatus.textContent = `Status: ${status} (${count * 1.5}s)`;
          if (job.logs && job.logs.length > 0) {
            dom.modalProgressSub.textContent = job.logs[job.logs.length - 1];
          }
        }

        if (status === 'SUCCESS') {
          clearInterval(timer);
          state.activeJobs.delete(jobId);
          showToast(`Pipeline ${jobId} completed successfully!`, 'success');
          closeModal();
          await syncAllData();
          if (job.experiment_id) {
            await selectRun(job.experiment_id);
          }
        } else if (status === 'FAILED') {
          clearInterval(timer);
          state.activeJobs.delete(jobId);
          showToast(`Pipeline ${jobId} failed: ${job.error || 'Unknown error'}`, 'error');
          if (dom.modalProgressArea) {
            dom.modalProgressStatus.textContent = `Failed: ${job.error || 'Error'}`;
            dom.modalProgressStatus.style.color = 'var(--accent-rose)';
          }
        } else if (count >= maxPolls) {
          clearInterval(timer);
          state.activeJobs.delete(jobId);
          showToast(`Job ${jobId} timed out.`, 'error');
        }
      } catch (err) {
        console.warn(`Job poll error for ${jobId}:`, err);
      }
    }, pollInterval);
  }

  async function pollActiveJobs() {
    if (state.activeJobs.size === 0) return;
    for (const [jobId, currentStatus] of state.activeJobs.entries()) {
      if (currentStatus === 'QUEUED' || currentStatus === 'RUNNING') {
        pollJobStatus(jobId);
      }
    }
  }

  // =========================================================================
  // Download Report
  // =========================================================================
  function downloadReport(runId) {
    const id = runId || state.activeRunId;
    if (!id) {
      showToast('Please select an experiment run first.', 'error');
      return;
    }
    const url = `${API_BASE}/api/run/${encodeURIComponent(id)}/report`;
    window.open(url, '_blank');
  }

  // =========================================================================
  // Lightbox Modal
  // =========================================================================
  window.openLightbox = function(imgSrc, title) {
    dom.lightboxImg.src = imgSrc;
    dom.lightboxTitle.textContent = title || 'Image Inspection';
    dom.lightboxModal.style.display = 'flex';
  };

  function closeLightbox() {
    dom.lightboxModal.style.display = 'none';
  }

  // =========================================================================
  // Modal Handling
  // =========================================================================
  function openModal() {
    dom.runModal.classList.add('active');
    dom.modalProgressArea.style.display = 'none';
    dom.btnSubmitRun.disabled = false;
  }

  function closeModal() {
    dom.runModal.classList.remove('active');
    dom.modalProgressArea.style.display = 'none';
    dom.btnSubmitRun.disabled = false;
  }

  // =========================================================================
  // View Switching Controller
  // =========================================================================
  function switchView(viewName) {
    state.currentView = viewName;

    // Update Nav
    dom.navItems.forEach(item => {
      item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Update View Panels
    dom.viewPanels.forEach(panel => {
      panel.classList.toggle('active', panel.id === `view-${viewName}`);
    });

    // Sub-view renders
    if (viewName === 'system') {
      renderSystemStatusView();
    } else if (viewName === 'experiments') {
      renderHistoryTable();
    } else if (viewName === 'evidence' && state.activeRunDetails) {
      renderScientificEvidence(state.activeRunDetails);
    }
  }

  // =========================================================================
  // Setup Event Listeners
  // =========================================================================
  function setupEventListeners() {
    // Nav Items
    dom.navItems.forEach(item => {
      item.addEventListener('click', () => switchView(item.dataset.view));
    });

    // Refresh Button
    dom.btnRefresh.addEventListener('click', () => {
      dom.btnRefresh.classList.add('rotating');
      syncAllData(false).then(() => {
        setTimeout(() => dom.btnRefresh.classList.remove('rotating'), 600);
      });
    });

    // Auto-Refresh Toggle
    dom.toggleAutoRefresh.addEventListener('change', (e) => {
      if (e.target.checked) {
        startAutoRefresh();
        showToast('Live Auto-Sync activated (every 5s)', 'info');
      } else {
        stopAutoRefresh();
        showToast('Live Auto-Sync paused', 'info');
      }
    });

    // Run Selector Change
    dom.activeRunSelect.addEventListener('change', (e) => {
      selectRun(e.target.value);
    });

    // Modal Trigger
    dom.btnOpenModal.addEventListener('click', openModal);
    dom.btnCloseModal.addEventListener('click', closeModal);
    dom.btnCancelModal.addEventListener('click', closeModal);
    dom.runModal.addEventListener('click', (e) => {
      if (e.target === dom.runModal) closeModal();
    });

    // Quick Trigger Buttons
    dom.btnTriggerActiveRun.addEventListener('click', openModal);
    dom.dropzoneTrigger.addEventListener('click', openModal);
    if (dom.btnQuickConfig) dom.btnQuickConfig.addEventListener('click', () => switchView('upload'));

    // Modal Form Submit
    dom.triggerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const params = {
        scenario: dom.modalScenario.value,
        seed: parseInt(document.getElementById('modal-seed').value, 10),
        image_size: parseInt(document.getElementById('modal-size').value, 10),
        detector: document.getElementById('modal-detector').value,
        model_type: document.getElementById('modal-model').value,
        refine_subpixel: document.getElementById('modal-subpixel').checked,
      };

      dom.modalProgressArea.style.display = 'flex';
      dom.btnSubmitRun.disabled = true;

      try {
        await triggerExperiment(params);
      } catch (err) {
        dom.btnSubmitRun.disabled = false;
      }
    });

    // Standalone Page Form Submit
    if (dom.standaloneForm) {
      dom.standaloneForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const params = {
          scenario: dom.pageScenarioSelect.value,
          seed: parseInt(document.getElementById('page-seed-input').value, 10),
          image_size: parseInt(document.getElementById('page-size-select').value, 10),
          detector: document.getElementById('page-detector-select').value,
          model_type: document.getElementById('page-model-select').value,
          refine_subpixel: document.getElementById('page-subpixel-check').checked,
        };
        await triggerExperiment(params);
        switchView('dashboard');
      });
    }

    // Report Download Buttons
    dom.btnDownloadReport.addEventListener('click', () => downloadReport());
    dom.btnEvidenceDownload.addEventListener('click', () => downloadReport());
    dom.btnViewDetailedReport.addEventListener('click', () => switchView('results'));

    // Copy Log Button
    dom.btnCopyLog.addEventListener('click', () => {
      const logText = dom.processingLogBody.innerText;
      navigator.clipboard.writeText(logText).then(() => {
        showToast('Processing log copied to clipboard.', 'success');
      });
    });

    // Search & Filters in History
    dom.historySearchInput.addEventListener('input', renderHistoryTable);
    dom.historyScenarioFilter.addEventListener('change', renderHistoryTable);
    dom.historyStatusFilter.addEventListener('change', renderHistoryTable);

    // Check All Runs in History
    dom.checkAllRuns.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      state.allRuns.forEach(r => {
        if (isChecked) state.selectedRunsForCompare.add(r.id);
        else state.selectedRunsForCompare.delete(r.id);
      });
      renderHistoryTable();
      updateCompareBar();
    });

    // Lightbox Close
    dom.btnCloseLightbox.addEventListener('click', closeLightbox);
    dom.lightboxModal.addEventListener('click', (e) => {
      if (e.target === dom.lightboxModal) closeLightbox();
    });

    // Keyboard Accessibility (Escape to close modals)
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal();
        closeLightbox();
      }
    });

    // Setting Poll Interval
    if (dom.settingPollInterval) {
      dom.settingPollInterval.addEventListener('change', (e) => {
        state.autoRefreshInterval = parseInt(e.target.value, 10);
        if (dom.toggleAutoRefresh.checked) {
          startAutoRefresh();
        }
      });
    }

    // Thumbnail Inspect Actions
    document.querySelectorAll('.thumb-card .thumb-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = btn.dataset.target;
        const base = `${API_BASE}/api/run/${encodeURIComponent(state.activeRunId)}`;
        const imgSrc = `${base}/registered/${target}.png`;
        window.openLightbox(imgSrc, `${target.toUpperCase()} Layer`);
      });
    });
  }

  // =========================================================================
  // Auto-Refresh Timers
  // =========================================================================
  function startAutoRefresh() {
    stopAutoRefresh();
    state.autoRefreshTimer = setInterval(() => {
      syncAllData(true);
    }, state.autoRefreshInterval);
  }

  function stopAutoRefresh() {
    if (state.autoRefreshTimer) {
      clearInterval(state.autoRefreshTimer);
      state.autoRefreshTimer = null;
    }
  }

  function renderEmptyState() {
    dom.heroExpTitle.textContent = 'No experiment data available.';
    dom.heroExpSub.textContent = 'Launch a new experiment run to begin scientific registration.';
    dom.processingLogBody.innerHTML = '<div class="log-line text-muted">Awaiting first experiment execution...</div>';
  }

  // =========================================================================
  // Initialization on DOM Ready
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupCurtainSlider();
    syncAllData(false);
    startAutoRefresh();
  });

})();
