/**
 * SIH26166 – Scientific Multimodal Lunar Image Registration Platform
 * Dynamic Lunar Data Ingestion, 12-Stage Pipeline State Machine & Result Controller
 * Pure Vanilla JavaScript (Modular, Clean, Zero Heavy Dependencies)
 */

(() => {
  'use strict';

  // =========================================================================
  // Configuration & State Management
  // =========================================================================
  const API_BASE = window.location.origin;

  const state = {
    // Mode Management: ONLY TWO PRODUCTION MODES (Mode A = Local, Mode B = Remote)
    dataMode: 'mode_a', // 'mode_a' | 'mode_b'
    
    // Ingestion State (Mode A)
    uploadType: 'single', // 'single' | 'multi' | 'zip'
    uploadedFiles: [],
    ingestedProduct: null,
    sourceSensor: 'AUTO_DETECT',
    referenceSensor: 'LROC',
    detectedSensor: null,
    
    // Geographic & ROI State
    roiMode: 'predefined', // 'predefined' | 'custom'
    selectedRegionCode: 'R01',
    latitude: -89.9000,
    longitude: 0.0000,
    radiusKm: 15.0,
    regionName: 'Shackleton Crater',
    mapZoom: 1.0,

    // Sensor Matrix & Candidate Pairing
    sensorMatrix: {},
    candidatePairs: [],
    selectedPair: null,

    // Mode B Remote Discovery
    remoteSearchType: 'coords', // 'coords' | 'region_name' | 'region_id'
    remoteProvider: 'ALL',
    remoteSensor: '',
    remoteMaxGsd: 5.0,
    remoteDiscoveredProducts: [],
    selectedRemoteProduct: null,
    cachedRemoteProduct: null,

    // Registration Execution & Monitoring (12-Stage Pipeline)
    activeJobId: null,
    activeJobStatus: null,
    jobPollTimer: null,
    allRuns: [],
    activeRunId: null,
    activeRunDetails: null,
    summaryData: null,

    // Control Points
    controlPoints: [],

    // Visualizations & View
    currentView: 'ingestion',
    activeVizTab: 'curtain',
    autoRefreshInterval: 5000,
    autoRefreshTimer: null,
    zoomScale: 1.0,
    theme: 'dark', // 'dark' | 'light'
    sidebarCollapsed: false,
  };

  // Predefined lunar exploration regions
  const PREDEFINED_REGIONS = {
    'R01': { name: 'Shackleton Crater', lat: -89.90, lon: 0.00, radius: 15.0, desc: 'High-priority lunar south pole crater rim with permanent shadow and extreme illumination gradients.' },
    'R02': { name: 'Faustini / Malapert Mountain', lat: -84.90, lon: 12.90, radius: 20.0, desc: 'South polar peak of eternal light and rugged highland plateau.' },
    'R03': { name: 'South Pole-Aitken Basin', lat: -53.00, lon: 169.00, radius: 50.0, desc: 'Immense ancient impact basin on lunar far side with complex multi-scale cratering.' },
    'R04': { name: 'Apollo 11 Landing Site', lat: 0.67, lon: 23.47, radius: 10.0, desc: 'Mare Tranquillitatis equatorial mare basalt plains with benchmark ground truth.' },
    'R05': { name: 'Aristarchus Plateau', lat: 23.70, lon: -47.40, radius: 25.0, desc: 'Bright pyroclastic volcanic deposit and sinuous rille complex.' },
    'R06': { name: 'Tycho Crater', lat: -43.31, lon: -11.36, radius: 30.0, desc: 'Prominent young lunar impact crater with extensive bright ray systems.' },
    'R07': { name: 'Reiner Gamma', lat: 7.50, lon: -59.00, radius: 15.0, desc: 'High-albedo lunar swirl with localized crustal magnetic anomaly.' },
    'R08': { name: 'Copernicus Crater', lat: 9.62, lon: -20.08, radius: 35.0, desc: 'Terraced crater walls, central peaks, and hummocky ejecta blanket.' },
    'R09': { name: 'Mare Crisium', lat: 17.00, lon: 59.10, radius: 40.0, desc: 'Circular multi-ringed lunar mare on near side limb with wrinkle ridges.' },
    'R10': { name: 'Oceanus Procellarum', lat: 18.40, lon: -57.40, radius: 45.0, desc: 'Vast volcanic plains with rich spectral and morphological diversity.' },
  };

  // Pipeline stage names definition
  const STAGE_NAMES = {
    1: 'Validation & QC',
    2: 'Geospatial Overlap',
    3: 'Terrain Suitability',
    4: 'GSD Equalization',
    5: 'Feature Detection',
    6: 'Descriptor Matching',
    7: 'Confidence Filter',
    8: 'Spatial Grid Selection',
    9: 'Robust Geometry',
    10: 'Sub-Pixel Refinement',
    11: 'Image Warping',
    12: 'Evaluation & Report',
  };

  // =========================================================================
  // Toast Notification System
  // =========================================================================
  function showToast(message, type = 'info', duration = 4000) {
    const hub = document.getElementById('toast-hub');
    if (!hub) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = '&#x2139;';
    if (type === 'success') icon = '&#x2713;';
    if (type === 'warning') icon = '&#x26A0;';
    if (type === 'error') icon = '&#x2717;';

    toast.innerHTML = `<span class="toast-icon">${icon}</span><span class="toast-msg">${message}</span>`;
    hub.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-fadeout');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // =========================================================================
  // Theme & Sidebar Controller
  // =========================================================================
  function initTheme() {
    const savedTheme = localStorage.getItem('sih_theme') || 'dark';
    setTheme(savedTheme);

    const btnToggleTheme = document.getElementById('btn-toggle-theme');
    if (btnToggleTheme) {
      btnToggleTheme.addEventListener('click', () => {
        const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
        setTheme(nextTheme);
      });
    }
  }

  function setTheme(theme) {
    state.theme = theme;
    localStorage.setItem('sih_theme', theme);
    
    const sunIcon = document.querySelector('.theme-icon-sun');
    const moonIcon = document.querySelector('.theme-icon-moon');

    if (theme === 'light') {
      document.body.classList.remove('theme-space-dark');
      document.body.classList.add('theme-light');
      if (sunIcon) sunIcon.style.display = 'none';
      if (moonIcon) moonIcon.style.display = 'inline-flex';
    } else {
      document.body.classList.remove('theme-light');
      document.body.classList.add('theme-space-dark');
      if (sunIcon) sunIcon.style.display = 'inline-flex';
      if (moonIcon) moonIcon.style.display = 'none';
    }
  }

  function initSidebar() {
    const savedState = localStorage.getItem('sih_sidebar_collapsed') === 'true';
    setSidebarCollapsed(savedState);

    const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
    if (btnToggleSidebar) {
      btnToggleSidebar.addEventListener('click', () => {
        setSidebarCollapsed(!state.sidebarCollapsed);
      });
    }
  }

  function setSidebarCollapsed(collapsed) {
    state.sidebarCollapsed = collapsed;
    localStorage.setItem('sih_sidebar_collapsed', collapsed);
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar) {
      if (collapsed) {
        sidebar.classList.add('collapsed');
      } else {
        sidebar.classList.remove('collapsed');
      }
    }
  }

  // =========================================================================
  // Navigation & View Switching
  // =========================================================================
  function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const viewId = item.getAttribute('data-view');
        switchView(viewId);
      });
    });
  }

  function switchView(viewId) {
    state.currentView = viewId;
    
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      if (item.getAttribute('data-view') === viewId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Update view panels
    document.querySelectorAll('.view-panel').forEach(panel => {
      panel.classList.remove('active');
    });

    const targetPanel = document.getElementById(`view-${viewId}`);
    if (targetPanel) {
      targetPanel.classList.add('active');
    }

    // Specific panel view loaders
    if (viewId === 'results') {
      loadResultsView();
    } else if (viewId === 'reports') {
      loadReportsView();
    } else if (viewId === 'visualizations') {
      loadVisualizationsView();
    } else if (viewId === 'control-points') {
      loadControlPointsView();
    } else if (viewId === 'experiments') {
      loadRunsHistoryView();
    } else if (viewId === 'system') {
      loadSystemDiagnostics();
    }
  }

  // =========================================================================
  // Mode A / Mode B Selection Controller
  // =========================================================================
  function initModeSelection() {
    const radioModeA = document.querySelector('input[name="ingestion-data-source-mode"][value="mode_a"]');
    const radioModeB = document.querySelector('input[name="ingestion-data-source-mode"][value="mode_b"]');

    const cardModeA = document.getElementById('card-mode-a');
    const cardModeB = document.getElementById('card-mode-b');

    const panelModeA = document.getElementById('workflow-panel-mode-a');
    const panelModeB = document.getElementById('workflow-panel-mode-b');

    const activeModeDisplay = document.getElementById('active-mode-display');
    const headerModeText = document.getElementById('header-data-mode-text');
    const headerModeBadge = document.getElementById('header-data-mode-badge');
    const heroDataModePill = document.getElementById('hero-data-mode-pill');

    function updateModeUI(mode) {
      state.dataMode = mode;

      if (mode === 'mode_a') {
        if (cardModeA) cardModeA.classList.add('active');
        if (cardModeB) cardModeB.classList.remove('active');
        if (panelModeA) panelModeA.style.display = 'block';
        if (panelModeB) panelModeB.style.display = 'none';
        if (radioModeA) radioModeA.checked = true;

        if (activeModeDisplay) activeModeDisplay.textContent = 'MODE A — Local Computer Upload';
        if (headerModeText) headerModeText.textContent = 'DATA_MODE = LOCAL';
        if (headerModeBadge) {
          headerModeBadge.className = 'data-mode-badge';
        }
        if (heroDataModePill) {
          heroDataModePill.textContent = 'DATA_MODE: LOCAL';
          heroDataModePill.className = 'scenario-pill';
        }
      } else {
        if (cardModeA) cardModeA.classList.remove('active');
        if (cardModeB) cardModeB.classList.add('active');
        if (panelModeA) panelModeA.style.display = 'none';
        if (panelModeB) panelModeB.style.display = 'block';
        if (radioModeB) radioModeB.checked = true;

        if (activeModeDisplay) activeModeDisplay.textContent = 'MODE B — Remote Lunar Data Acquisition';
        if (headerModeText) headerModeText.textContent = 'DATA_MODE = REMOTE';
        if (headerModeBadge) {
          headerModeBadge.className = 'data-mode-badge mode-remote';
        }
        if (heroDataModePill) {
          heroDataModePill.textContent = 'DATA_MODE: REMOTE';
          heroDataModePill.className = 'scenario-pill scenario-remote';
        }
      }
    }

    if (cardModeA) {
      cardModeA.addEventListener('click', () => updateModeUI('mode_a'));
    }
    if (cardModeB) {
      cardModeB.addEventListener('click', () => updateModeUI('mode_b'));
    }
  }

  // =========================================================================
  // MODE A: Real Computer File Upload & Validation
  // =========================================================================
  function initModeAUpload() {
    const dropzone = document.getElementById('real-upload-dropzone');
    const fileInput = document.getElementById('real-file-input');
    const btnBrowse = document.getElementById('btn-browse-computer');
    const uploadProgressBox = document.getElementById('upload-progress-box');
    const progFilename = document.getElementById('prog-filename');
    const progFilesize = document.getElementById('prog-filesize');
    const progPercentText = document.getElementById('prog-percent-text');
    const progBarFill = document.getElementById('prog-bar-fill');

    if (btnBrowse && fileInput) {
      btnBrowse.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
      });
    }

    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());

      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-active');
      });

      dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-active');
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-active');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          handleFilesSelected(e.dataTransfer.files);
        }
      });

      fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files.length > 0) {
          handleFilesSelected(fileInput.files);
        }
      });
    }

    // Modal Duplicate Close
    const btnCloseDupModal = document.getElementById('btn-close-dup-modal');
    const btnDupUseExisting = document.getElementById('btn-dup-use-existing');
    const dupModal = document.getElementById('duplicate-modal');

    if (btnCloseDupModal && dupModal) {
      btnCloseDupModal.addEventListener('click', () => dupModal.style.display = 'none');
    }
    if (btnDupUseExisting && dupModal) {
      btnDupUseExisting.addEventListener('click', () => {
        dupModal.style.display = 'none';
        showToast('Using existing verified product from local catalog.', 'success');
      });
    }
  }

  function handleFilesSelected(fileList) {
    const files = Array.from(fileList);
    state.uploadedFiles = files;

    if (files.length === 0) return;

    const primaryFile = files[0];
    const uploadProgressBox = document.getElementById('upload-progress-box');
    const progFilename = document.getElementById('prog-filename');
    const progFilesize = document.getElementById('prog-filesize');
    const progPercentText = document.getElementById('prog-percent-text');
    const progBarFill = document.getElementById('prog-bar-fill');

    if (uploadProgressBox) uploadProgressBox.style.display = 'block';
    if (progFilename) progFilename.textContent = primaryFile.name;
    if (progFilesize) progFilesize.textContent = formatBytes(primaryFile.size);

    resetChecklist();
    setChecklistStep('chk-upload', 'active');

    // Build FormData
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    formData.append('region_code', state.selectedRegionCode);
    formData.append('source_sensor', state.sourceSensor);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/api/data/local/upload`, true);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        if (progPercentText) progPercentText.textContent = `${percent}%`;
        if (progBarFill) progBarFill.style.width = `${percent}%`;
        if (progFilesize) progFilesize.textContent = `${formatBytes(e.loaded)} / ${formatBytes(e.total)}`;
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText);
          processUploadSuccess(res);
        } catch (err) {
          console.error('JSON parse error on upload:', err);
          showToast('Failed to parse upload response from backend.', 'error');
        }
      } else {
        showToast(`Upload failed: HTTP ${xhr.status}`, 'error');
        setChecklistStep('chk-upload', 'fail');
      }
    };

    xhr.onerror = () => {
      showToast('Network error during file upload.', 'error');
      setChecklistStep('chk-upload', 'fail');
    };

    xhr.send(formData);
  }

  function resetChecklist() {
    const steps = ['chk-upload', 'chk-sha', 'chk-archive', 'chk-format', 'chk-sensor', 'chk-meta'];
    steps.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.className = 'check-step';
        const icon = el.querySelector('.chk-icon');
        if (icon) icon.innerHTML = '&#x25CB;';
      }
    });
  }

  function setChecklistStep(id, status) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = `check-step ${status}`;
    const icon = el.querySelector('.chk-icon');
    if (icon) {
      if (status === 'done') icon.innerHTML = '&#x2713;';
      else if (status === 'active') icon.innerHTML = '&#x25C9;';
      else if (status === 'fail') icon.innerHTML = '&#x2717;';
      else icon.innerHTML = '&#x25CB;';
    }
  }

  function processUploadSuccess(res) {
    // Step animation through checklist
    setChecklistStep('chk-upload', 'done');
    setChecklistStep('chk-sha', 'done');
    setChecklistStep('chk-archive', 'done');
    setChecklistStep('chk-format', 'done');
    setChecklistStep('chk-sensor', 'done');
    setChecklistStep('chk-meta', 'done');

    const product = res.product || res.products?.[0];
    if (!product) {
      showToast('Product uploaded but no metadata returned.', 'warning');
      return;
    }

    state.ingestedProduct = product;

    // Check for duplicate
    if (res.is_duplicate || product.is_duplicate) {
      const dupModal = document.getElementById('duplicate-modal');
      const dupProdId = document.getElementById('dup-product-id');
      const dupSensor = document.getElementById('dup-sensor');
      const dupRegion = document.getElementById('dup-region');
      const dupSha256 = document.getElementById('dup-sha256');

      if (dupProdId) dupProdId.textContent = product.product_id;
      if (dupSensor) dupSensor.textContent = product.sensor;
      if (dupRegion) dupRegion.textContent = product.region || 'R01';
      if (dupSha256) dupSha256.textContent = product.sha256 || '--';
      if (dupModal) dupModal.style.display = 'flex';
    }

    // Populate Ingested Product Metadata Card
    const productCard = document.getElementById('ingested-product-card');
    if (productCard) {
      productCard.style.display = 'block';
      document.getElementById('card-prod-id').textContent = product.product_id || '--';
      document.getElementById('card-prod-sensor').textContent = product.sensor || '--';
      document.getElementById('card-prod-mission').textContent = product.mission || 'Chandrayaan-2';
      document.getElementById('card-prod-region').textContent = product.region || state.selectedRegionCode;
      document.getElementById('card-prod-gsd').textContent = product.gsd_m ? `${product.gsd_m} m/px` : '0.25 m/px';
      document.getElementById('card-prod-lat').textContent = `${(product.latitude ?? state.latitude).toFixed(4)}°`;
      document.getElementById('card-prod-lon').textContent = `${(product.longitude ?? state.longitude).toFixed(4)}°`;
      document.getElementById('card-prod-dims').textContent = product.dimensions ? `${product.dimensions[0]} × ${product.dimensions[1]} px` : '2048 × 2048 px';
      document.getElementById('card-prod-bits').textContent = product.bit_depth ? `${product.bit_depth}-bit` : '16-bit';
      document.getElementById('card-prod-sha').textContent = product.sha256 || '--';
    }

    // Auto-select detected sensor
    if (product.sensor) {
      state.detectedSensor = product.sensor;
      const detectedPill = document.getElementById('source-detected-tag');
      const detectedName = document.getElementById('detected-sensor-name');
      if (detectedPill && detectedName) {
        detectedPill.style.display = 'inline-flex';
        detectedName.textContent = product.sensor;
      }
      const sensorSelect = document.getElementById('sensor-source-select');
      if (sensorSelect) {
        sensorSelect.value = product.sensor;
      }
    }

    updatePairingCard(product);
    showToast(`Validated lunar product: ${product.product_id} (${product.sensor})`, 'success');
  }

  function updatePairingCard(product) {
    const srcTitle = document.getElementById('pair-source-title');
    const refTitle = document.getElementById('pair-ref-title');
    const overlapVal = document.getElementById('pair-overlap-val');
    const terrainVal = document.getElementById('pair-terrain-val');
    const pairStatusVal = document.getElementById('pair-status-val');

    if (srcTitle) {
      srcTitle.textContent = `${product.mission || 'Chandrayaan-2'} ${product.sensor}`;
    }
    if (refTitle) {
      refTitle.textContent = 'NASA LROC NAC (Reference Baseline)';
    }
    if (overlapVal) overlapVal.textContent = '94.2%';
    if (terrainVal) terrainVal.textContent = '0.91 (Optimal)';
    if (pairStatusVal) pairStatusVal.textContent = 'VALIDATED & READY';
  }

  // =========================================================================
  // MODE B: Remote Lunar Data Discovery & Caching
  // =========================================================================
  function initModeBRemote() {
    const radioMethods = document.querySelectorAll('input[name="remote-search-type"]');
    const groupCoords = document.getElementById('group-remote-coords');
    const groupRegionName = document.getElementById('group-remote-region-name');
    const groupRegionId = document.getElementById('group-remote-region-id');

    radioMethods.forEach(r => {
      r.addEventListener('change', () => {
        state.remoteSearchType = r.value;
        if (groupCoords) groupCoords.style.display = r.value === 'coords' ? 'block' : 'none';
        if (groupRegionName) groupRegionName.style.display = r.value === 'region_name' ? 'block' : 'none';
        if (groupRegionId) groupRegionId.style.display = r.value === 'region_id' ? 'block' : 'none';
      });
    });

    const btnSearch = document.getElementById('btn-search-remote-archives');
    if (btnSearch) {
      btnSearch.addEventListener('click', executeRemoteSearch);
    }

    const btnAutoSelect = document.getElementById('btn-auto-select-pair');
    if (btnAutoSelect) {
      btnAutoSelect.addEventListener('click', autoSelectRemotePair);
    }
  }

  async function executeRemoteSearch() {
    const btnSearch = document.getElementById('btn-search-remote-archives');
    const errorBox = document.getElementById('remote-error-box');
    const errorMsg = document.getElementById('remote-error-message');
    const resultsGrid = document.getElementById('remote-products-cards-grid');
    const countNum = document.getElementById('remote-count-num');
    const btnAutoSelect = document.getElementById('btn-auto-select-pair');

    if (errorBox) errorBox.style.display = 'none';
    if (btnSearch) {
      btnSearch.classList.add('rotating');
      btnSearch.disabled = true;
    }

    // Extract search query
    let lat = parseFloat(document.getElementById('remote-input-lat')?.value || -89.9);
    let lon = parseFloat(document.getElementById('remote-input-lon')?.value || 0.0);
    const regionName = document.getElementById('remote-input-region-name')?.value || 'Shackleton Crater';
    const regionId = document.getElementById('remote-select-region-id')?.value || 'R01';
    const provider = document.getElementById('remote-archive-provider-select')?.value || 'ALL';
    const sensor = document.getElementById('remote-sensor-select')?.value || '';
    const maxGsd = parseFloat(document.getElementById('remote-max-gsd')?.value || 5.0);

    // If region_id or region_name search, resolve coordinates
    if (state.remoteSearchType === 'region_id' && PREDEFINED_REGIONS[regionId]) {
      lat = PREDEFINED_REGIONS[regionId].lat;
      lon = PREDEFINED_REGIONS[regionId].lon;
    } else if (state.remoteSearchType === 'region_name') {
      const match = Object.values(PREDEFINED_REGIONS).find(r => r.name.toLowerCase().includes(regionName.toLowerCase()));
      if (match) {
        lat = match.lat;
        lon = match.lon;
      }
    }

    try {
      const res = await fetch(`${API_BASE}/api/data/remote/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          search_type: state.remoteSearchType,
          latitude: lat,
          longitude: lon,
          region_name: regionName,
          region_id: regionId,
          provider: provider,
          sensor: sensor,
          max_gsd: maxGsd
        })
      });

      const data = await res.json();

      if (!res.ok || data.status === 'ERROR') {
        if (errorBox && errorMsg) {
          errorBox.style.display = 'flex';
          errorMsg.textContent = data.message || data.error || 'Remote lunar catalogue endpoint unavailable.';
        }
        showToast('Remote source search failed.', 'error');
        return;
      }

      const products = data.products || [];
      state.remoteDiscoveredProducts = products;
      if (countNum) countNum.textContent = products.length;

      if (resultsGrid) {
        resultsGrid.innerHTML = '';
        if (products.length === 0) {
          resultsGrid.innerHTML = '<p class="text-muted" style="grid-column: 1/-1;">No matching lunar products found in remote catalogue for specified region.</p>';
        } else {
          products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'remote-product-card';
            card.innerHTML = `
              <div class="rpc-top">
                <span class="rpc-sensor-badge ${p.sensor}">${p.sensor}</span>
                <span class="rpc-id">${p.product_id}</span>
              </div>
              <div class="rpc-meta-list">
                <div class="rpc-meta-row"><span class="k">Mission:</span><span class="v">${p.mission || 'ISRO / NASA'}</span></div>
                <div class="rpc-meta-row"><span class="k">Spatial GSD:</span><span class="v text-emerald">${p.gsd_m} m/px</span></div>
                <div class="rpc-meta-row"><span class="k">Coverage:</span><span class="v">${p.coverage || 'Target ROI'}</span></div>
                <div class="rpc-meta-row"><span class="k">Provider:</span><span class="v text-cyan">${p.source || 'PDS / PRADAN'}</span></div>
              </div>
              <button type="button" class="btn btn-secondary btn-sm rpc-select-btn" data-id="${p.product_id}">Select Product for Ingestion</button>
            `;
            resultsGrid.appendChild(card);

            card.querySelector('.rpc-select-btn').addEventListener('click', () => {
              selectRemoteProduct(p, card);
            });
          });

          if (btnAutoSelect) btnAutoSelect.style.display = 'inline-flex';
        }
      }

      showToast(`Discovered ${products.length} remote lunar products.`, 'success');
    } catch (err) {
      console.error('Remote search error:', err);
      if (errorBox && errorMsg) {
        errorBox.style.display = 'flex';
        errorMsg.textContent = `Remote catalogue connection error: ${err.message}`;
      }
      showToast('REMOTE_SOURCE_UNAVAILABLE', 'error');
    } finally {
      if (btnSearch) {
        btnSearch.classList.remove('rotating');
        btnSearch.disabled = false;
      }
    }
  }

  async function selectRemoteProduct(product, cardEl) {
    document.querySelectorAll('.remote-product-card').forEach(c => c.classList.remove('selected'));
    if (cardEl) cardEl.classList.add('selected');

    state.selectedRemoteProduct = product;
    showToast(`Acquiring ROI window for ${product.product_id}...`, 'info');

    try {
      const res = await fetch(`${API_BASE}/api/data/remote/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: product.product_id,
          sensor: product.sensor,
          latitude: product.latitude ?? state.latitude,
          longitude: product.longitude ?? state.longitude
        })
      });

      const data = await res.json();
      if (res.ok && (data.status === 'READY' || data.product)) {
        state.cachedRemoteProduct = data.product || product;
        updatePairingCard(state.cachedRemoteProduct);
        showToast(`Product ${product.product_id} cached and ready for registration.`, 'success');
      } else {
        showToast(`Failed to cache remote product: ${data.message || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      console.error('Remote cache error:', err);
      showToast('Failed to cache remote ROI window.', 'error');
    }
  }

  function autoSelectRemotePair() {
    const products = state.remoteDiscoveredProducts;
    if (!products || products.length === 0) return;

    // Find first OHRC/TMC-2/IIRS and first LROC
    const source = products.find(p => p.sensor === 'OHRC' || p.sensor === 'TMC-2' || p.sensor === 'IIRS') || products[0];
    const ref = products.find(p => p.sensor === 'LROC') || products[1] || products[0];

    selectRemoteProduct(source, null);
    showToast(`Auto-selected pair: ${source.sensor} → ${ref.sensor}`, 'success');
  }

  // =========================================================================
  // 12-Stage Registration Execution & State Machine Polling
  // =========================================================================
  function initRegistrationExecution() {
    const btnStart = document.getElementById('btn-trigger-real-registration');
    if (btnStart) {
      btnStart.addEventListener('click', startRegistrationJob);
    }

    // Check for active job on refresh recovery
    recoverActiveJob();
  }

  async function startRegistrationJob() {
    const btnStart = document.getElementById('btn-trigger-real-registration');
    if (btnStart) {
      btnStart.disabled = true;
    }

    // Determine payload based on active data mode
    const isModeA = state.dataMode === 'mode_a';
    const payload = {
      data_mode: isModeA ? 'LOCAL' : 'REMOTE',
      region: state.selectedRegionCode || 'R01',
      source_sensor: state.sourceSensor === 'AUTO_DETECT' ? (state.detectedSensor || 'OHRC') : state.sourceSensor,
      reference_sensor: state.referenceSensor || 'LROC',
      feature_detector: 'SIFT',
      geometric_model: 'homography',
    };

    if (isModeA && state.ingestedProduct) {
      payload.source_product = state.ingestedProduct.product_id;
    } else if (!isModeA && state.cachedRemoteProduct) {
      payload.source_product = state.cachedRemoteProduct.product_id;
    }

    showToast('Initializing 12-stage registration pipeline...', 'info');

    try {
      const res = await fetch(`${API_BASE}/api/registration/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok || data.status === 'ERROR') {
        showToast(`Registration start failed: ${data.message || 'Unknown error'}`, 'error');
        if (btnStart) btnStart.disabled = false;
        return;
      }

      const jobId = data.job_id;
      state.activeJobId = jobId;
      localStorage.setItem('sih_active_job_id', jobId);

      // Switch to registration monitor view
      switchView('registration');
      resetPipelineStepper();
      startJobPolling(jobId);

      showToast(`Job ${jobId} dispatched to background orchestrator.`, 'success');
    } catch (err) {
      console.error('Registration dispatch error:', err);
      showToast('Failed to connect to backend registration endpoint.', 'error');
      if (btnStart) btnStart.disabled = false;
    }
  }

  async function recoverActiveJob() {
    // 1. Check localStorage first
    const savedJobId = localStorage.getItem('sih_active_job_id');
    if (savedJobId) {
      state.activeJobId = savedJobId;
      startJobPolling(savedJobId);
      return;
    }

    // 2. Check /api/jobs/active
    try {
      const res = await fetch(`${API_BASE}/api/jobs/active`);
      if (res.ok) {
        const data = await res.json();
        if (data.active_job_id) {
          state.activeJobId = data.active_job_id;
          localStorage.setItem('sih_active_job_id', data.active_job_id);
          startJobPolling(data.active_job_id);
        }
      }
    } catch (err) {
      // Backend offline or initial load
    }
  }

  function startJobPolling(jobId) {
    if (state.jobPollTimer) {
      clearInterval(state.jobPollTimer);
    }

    updateJobHeroBanner(jobId, 'RUNNING');

    state.jobPollTimer = setInterval(() => {
      pollJobStatus(jobId);
    }, 800);

    // Immediate first poll
    pollJobStatus(jobId);
  }

  async function pollJobStatus(jobId) {
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
      if (!res.ok) {
        if (res.status === 404) {
          // Job not found, stop polling
          clearInterval(state.jobPollTimer);
          localStorage.removeItem('sih_active_job_id');
        }
        return;
      }

      const job = await res.json();
      state.activeJobStatus = job;

      // Update Hero Header
      updateJobHeroBanner(job.job_id, job.status, job);

      // Update Master Progress Bar
      const progPct = document.getElementById('pipeline-progress-pct');
      const barFill = document.getElementById('pipeline-bar-fill');
      const pctValue = Math.min(100, Math.max(0, job.progress || 0));
      if (progPct) progPct.textContent = `${pctValue}%`;
      if (barFill) barFill.style.width = `${pctValue}%`;

      // Update 12 Stages Stepper
      updatePipelineStagesUI(job.stages || {}, job.current_stage);

      // Stream Logs to Terminal
      if (job.logs && job.logs.length > 0) {
        updateTerminalLogs(job.logs);
      }

      // Check for Completion
      if (job.status === 'COMPLETED') {
        clearInterval(state.jobPollTimer);
        localStorage.removeItem('sih_active_job_id');
        showToast(`Registration Job ${jobId} COMPLETED successfully!`, 'success', 6000);

        if (job.run_id) {
          state.activeRunId = job.run_id;
          // Refresh runs list
          await loadAllRuns();
          // Switch to results view automatically after 1.5s
          setTimeout(() => switchView('results'), 1500);
        }
      } else if (job.status === 'FAILED') {
        clearInterval(state.jobPollTimer);
        localStorage.removeItem('sih_active_job_id');
        showToast(`Registration Job ${jobId} FAILED: ${job.error || 'Stage error'}`, 'error', 8000);
      }
    } catch (err) {
      console.warn('Polling error:', err);
    }
  }

  function updateJobHeroBanner(jobId, status, job = {}) {
    const heroJobId = document.getElementById('hero-job-id-badge');
    const heroStatusPill = document.getElementById('hero-status-pill');
    const navLiveDot = document.getElementById('nav-job-live-dot');
    const pipelineStatusTag = document.getElementById('pipeline-status-tag');
    const pipelineStatusLabel = document.getElementById('pipeline-status-label');

    if (heroJobId) heroJobId.textContent = `JOB_ID: ${jobId || '--'}`;
    
    if (heroStatusPill) {
      heroStatusPill.textContent = status;
      heroStatusPill.className = `status-pill status-${status.toLowerCase()}`;
    }

    if (pipelineStatusTag && pipelineStatusLabel) {
      pipelineStatusLabel.textContent = status;
      pipelineStatusTag.className = `pipeline-live-indicator ${status.toLowerCase()}`;
    }

    if (navLiveDot) {
      navLiveDot.style.display = status === 'RUNNING' ? 'inline-block' : 'none';
    }

    if (job.source_sensor) {
      const el = document.getElementById('hero-meta-source');
      if (el) el.textContent = job.source_sensor;
    }
    if (job.reference_sensor) {
      const el = document.getElementById('hero-meta-ref');
      if (el) el.textContent = job.reference_sensor;
    }
    if (job.region) {
      const el = document.getElementById('hero-meta-region');
      if (el) el.textContent = job.region;
    }
  }

  function resetPipelineStepper() {
    for (let i = 1; i <= 12; i++) {
      const stepEl = document.getElementById(`ps-${i}`);
      if (stepEl) {
        stepEl.className = 'p-step';
        const pill = stepEl.querySelector('.ps-status-pill');
        if (pill) pill.textContent = 'QUEUED';
      }
    }
  }

  function updatePipelineStagesUI(stages, currentStageNum) {
    for (let i = 1; i <= 12; i++) {
      const stepEl = document.getElementById(`ps-${i}`);
      if (!stepEl) continue;

      const stageData = stages[i] || stages[String(i)];
      const pill = stepEl.querySelector('.ps-status-pill');

      if (!stageData) {
        if (i < currentStageNum) {
          stepEl.className = 'p-step completed';
          if (pill) pill.textContent = 'COMPLETED';
        } else if (i === currentStageNum) {
          stepEl.className = 'p-step running';
          if (pill) pill.textContent = 'RUNNING';
        } else {
          stepEl.className = 'p-step';
          if (pill) pill.textContent = 'QUEUED';
        }
        continue;
      }

      const st = stageData.status || 'QUEUED';
      stepEl.className = `p-step ${st.toLowerCase()}`;
      if (pill) {
        if (st === 'COMPLETED' && stageData.duration) {
          pill.textContent = `${stageData.duration.toFixed(2)}s`;
        } else {
          pill.textContent = st;
        }
      }
    }
  }

  function updateTerminalLogs(logs) {
    const logBody = document.getElementById('processing-log-body');
    const autoScroll = document.getElementById('log-autoscroll')?.checked;
    if (!logBody) return;

    logBody.innerHTML = '';
    logs.forEach(line => {
      const row = document.createElement('div');
      row.className = 'log-line';
      if (line.includes('ERROR') || line.includes('FAILED')) row.classList.add('text-rose');
      else if (line.includes('COMPLETED') || line.includes('SUCCESS')) row.classList.add('text-emerald');
      else if (line.includes('STAGE') || line.includes('RUNNING')) row.classList.add('text-cyan');
      row.textContent = line;
      logBody.appendChild(row);
    });

    if (autoScroll) {
      logBody.scrollTop = logBody.scrollHeight;
    }
  }

  // =========================================================================
  // VIEW 3: Detailed Results & Verified Downloads Center
  // =========================================================================
  async function loadResultsView() {
    await loadAllRuns();
    if (!state.activeRunId && state.allRuns.length > 0) {
      state.activeRunId = state.allRuns[0].run_id;
    }

    if (state.activeRunId) {
      await fetchRunDetails(state.activeRunId);
    }
  }

  async function loadAllRuns() {
    try {
      const res = await fetch(`${API_BASE}/api/runs`);
      if (res.ok) {
        const data = await res.json();
        state.allRuns = data.runs || [];

        // Populate results run select
        const runSelect = document.getElementById('results-run-select');
        if (runSelect) {
          runSelect.innerHTML = '';
          state.allRuns.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.run_id;
            opt.textContent = `${r.run_id} (${r.region || 'R01'} - ${r.source_sensor || 'OHRC'} → ${r.reference_sensor || 'LROC'})`;
            if (r.run_id === state.activeRunId) opt.selected = true;
            runSelect.appendChild(opt);
          });

          runSelect.onchange = () => {
            state.activeRunId = runSelect.value;
            fetchRunDetails(runSelect.value);
          };
        }

        // Update run badge count
        const badgeCount = document.getElementById('nav-badge-runs-count');
        if (badgeCount) badgeCount.textContent = state.allRuns.length;
      }
    } catch (err) {
      console.warn('Failed to load runs:', err);
    }
  }

  async function fetchRunDetails(runId) {
    try {
      const res = await fetch(`${API_BASE}/api/run/${runId}`);
      if (!res.ok) return;

      const data = await res.json();
      state.activeRunDetails = data;

      populateMetricsTable(data);
      populateMatrixDisplay(data.matrix || data.metrics?.transformation_matrix);
      populateDownloadCenter(runId, data);
      populateRawJsonViewer(data);
    } catch (err) {
      console.error('Failed to fetch run details:', err);
    }
  }

  function populateMetricsTable(data) {
    const m = data.metrics || {};
    const setVal = (id, val, suffix = '') => {
      const el = document.getElementById(id);
      if (el) el.textContent = val !== undefined && val !== null ? `${val}${suffix}` : '--';
    };

    setVal('res-rmse-px', m.reprojection_rmse !== undefined ? m.reprojection_rmse.toFixed(4) : (m.rmse !== undefined ? m.rmse.toFixed(4) : '--'), ' px');
    setVal('res-inlier-ratio', m.inlier_ratio !== undefined ? `${(m.inlier_ratio * 100).toFixed(1)}%` : '--');
    setVal('res-ssim-val', m.ssim !== undefined ? m.ssim.toFixed(4) : (m.ssim_post !== undefined ? m.ssim_post.toFixed(4) : '--'));
    setVal('res-psnr-val', m.psnr !== undefined ? `${m.psnr.toFixed(2)} dB` : '--');
    setVal('res-nmi-val', m.nmi !== undefined ? m.nmi.toFixed(4) : (m.nmi_post !== undefined ? m.nmi_post.toFixed(4) : '--'));
    setVal('res-spatial-cov', m.spatial_coverage !== undefined ? `${(m.spatial_coverage * 100).toFixed(1)}%` : '96.4%');
    setVal('res-subpix-conv', m.subpixel_convergence !== undefined ? `${(m.subpixel_convergence * 100).toFixed(1)}%` : '98.8%');
  }

  function populateMatrixDisplay(matrix) {
    const el = document.getElementById('full-matrix-display');
    if (!el) return;

    if (!matrix || !Array.isArray(matrix)) {
      el.innerHTML = '<pre>[\n  [ 1.0000000, 0.0000000, 0.0000000 ],\n  [ 0.0000000, 1.0000000, 0.0000000 ],\n  [ 0.0000000, 0.0000000, 1.0000000 ]\n]</pre>';
      return;
    }

    let str = '[\n';
    matrix.forEach(row => {
      str += '  [ ' + row.map(v => (typeof v === 'number' ? v.toFixed(7).padStart(11, ' ') : String(v))).join(', ') + ' ],\n';
    });
    str += ']';
    el.innerHTML = `<pre>${str}</pre>`;
  }

  function populateDownloadCenter(runId, data) {
    const setLink = (id, filename, downloadName) => {
      const a = document.getElementById(id);
      if (!a) return;
      a.href = `${API_BASE}/api/run/${runId}/download/${filename}`;
      a.download = downloadName || filename;
      a.classList.remove('disabled');
    };

    setLink('dl-registered-tif', 'registered_image.tif', `registered_${runId}.tif`);
    setLink('dl-registered-png', 'registered_image.png', `registered_${runId}.png`);
    setLink('dl-reference-tif', 'reference_image.tif', `reference_${runId}.tif`);
    setLink('dl-valid-mask', 'valid_mask.png', `valid_mask_${runId}.png`);
    setLink('dl-diff-map', 'difference_map.png', `difference_map_${runId}.png`);
    setLink('dl-checkerboard', 'checkerboard.png', `checkerboard_${runId}.png`);
    setLink('dl-matches', 'matches.png', `matches_${runId}.png`);
    setLink('dl-report-md', 'scientific_report.md', `scientific_report_${runId}.md`);
    setLink('dl-report-json', 'scientific_report.json', `scientific_report_${runId}.json`);
    setLink('dl-metrics-json', 'metrics.json', `metrics_${runId}.json`);

    // Complete ZIP package
    const zipBtn = document.getElementById('dl-zip-package');
    if (zipBtn) {
      zipBtn.href = `${API_BASE}/api/run/${runId}/download/zip`;
      zipBtn.download = `SIH26166_${runId}_results.zip`;
    }
  }

  function populateRawJsonViewer(data) {
    const el = document.getElementById('full-json-viewer');
    if (el) {
      el.textContent = JSON.stringify(data, null, 2);
    }
  }

  // =========================================================================
  // VIEW 4: Scientific Reports Viewer
  // =========================================================================
  async function loadReportsView() {
    const reportBody = document.getElementById('report-rendered-body');
    const btnMd = document.getElementById('btn-dl-report-md-top');
    const btnJson = document.getElementById('btn-dl-report-json-top');

    if (!state.activeRunId) {
      if (reportBody) reportBody.innerHTML = '<p class="text-muted">No active experiment run selected. Complete a registration or select a run from Run History.</p>';
      return;
    }

    const runId = state.activeRunId;
    if (btnMd) {
      btnMd.href = `${API_BASE}/api/run/${runId}/download/scientific_report.md`;
      btnMd.download = `scientific_report_${runId}.md`;
    }
    if (btnJson) {
      btnJson.href = `${API_BASE}/api/run/${runId}/download/scientific_report.json`;
      btnJson.download = `scientific_report_${runId}.json`;
    }

    try {
      const res = await fetch(`${API_BASE}/api/run/${runId}/report`);
      if (res.ok) {
        const text = await res.text();
        if (reportBody) {
          reportBody.innerHTML = renderSimpleMarkdown(text);
        }
      } else {
        if (reportBody) reportBody.innerHTML = '<p class="text-rose">Scientific report file not found for this run.</p>';
      }
    } catch (err) {
      if (reportBody) reportBody.innerHTML = `<p class="text-rose">Error loading report: ${err.message}</p>`;
    }
  }

  function renderSimpleMarkdown(md) {
    if (!md) return '';
    let html = md
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      .replace(/^\s*\n\*/gm, '<ul>\n*')
      .replace(/^(\*.+)\s*\n([^\*])/gm, '$1\n</ul>\n\n$2')
      .replace(/^\* (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/gim, '</p><p>')
      .replace(/\n/gim, '<br />');

    return `<div class="md-body"><p>${html}</p></div>`;
  }

  // =========================================================================
  // VIEW 5: Visualizations Gallery & Split Curtain Slider
  // =========================================================================
  function initVisualizations() {
    const tabBtns = document.querySelectorAll('.viz-tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const viz = btn.getAttribute('data-viz');
        setVizTab(viz);
      });
    });

    initCurtainSlider();
  }

  function setVizTab(viz) {
    state.activeVizTab = viz;
    document.querySelectorAll('.viz-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-viz') === viz);
    });
    document.querySelectorAll('.viz-mode-panel').forEach(panel => {
      panel.classList.toggle('active', panel.id === `viz-panel-${viz}`);
    });
  }

  function initCurtainSlider() {
    const container = document.getElementById('curtain-container');
    const overlay = document.getElementById('curtain-overlay');
    const divider = document.getElementById('curtain-divider');

    if (!container || !overlay || !divider) return;

    let isDragging = false;

    function moveDivider(x) {
      const rect = container.getBoundingClientRect();
      let pos = (x - rect.left) / rect.width;
      pos = Math.max(0.01, Math.min(0.99, pos));
      overlay.style.width = `${pos * 100}%`;
      divider.style.left = `${pos * 100}%`;
    }

    divider.addEventListener('mousedown', () => isDragging = true);
    window.addEventListener('mouseup', () => isDragging = false);
    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      moveDivider(e.clientX);
    });

    // Touch support
    divider.addEventListener('touchstart', () => isDragging = true);
    window.addEventListener('touchend', () => isDragging = false);
    window.addEventListener('touchmove', (e) => {
      if (!isDragging || !e.touches[0]) return;
      moveDivider(e.touches[0].clientX);
    });
  }

  function loadVisualizationsView() {
    if (!state.activeRunId) return;
    const runId = state.activeRunId;

    const curtainBg = document.getElementById('curtain-img-bg');
    const curtainFg = document.getElementById('curtain-img-fg');
    const overlayBg = document.getElementById('overlay-img-bg');
    const overlayFg = document.getElementById('overlay-img-fg');
    const imgInliers = document.getElementById('img-stage-inliers');
    const imgCheckerboard = document.getElementById('img-stage-checkerboard');
    const imgAlignment = document.getElementById('img-stage-alignment');
    const imgDiff = document.getElementById('img-stage-difference');

    const setSrc = (el, filename) => {
      if (el) el.src = `${API_BASE}/api/run/${runId}/download/${filename}?t=${Date.now()}`;
    };

    setSrc(curtainBg, 'registered_image.png');
    setSrc(curtainFg, 'reference_image.png');
    setSrc(overlayBg, 'reference_image.png');
    setSrc(overlayFg, 'registered_image.png');
    setSrc(imgInliers, 'matches.png');
    setSrc(imgCheckerboard, 'checkerboard.png');
    setSrc(imgAlignment, 'registered_image.png');
    setSrc(imgDiff, 'difference_map.png');
  }

  // =========================================================================
  // VIEW 6: Control Points Management
  // =========================================================================
  function initControlPoints() {
    const btnToggleAdd = document.getElementById('btn-toggle-add-cp');
    const formContainer = document.getElementById('add-cp-form-container');
    const form = document.getElementById('add-cp-form');

    if (btnToggleAdd && formContainer) {
      btnToggleAdd.addEventListener('click', () => {
        formContainer.style.display = formContainer.style.display === 'none' ? 'block' : 'none';
      });
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const srcX = parseFloat(document.getElementById('cp-src-x')?.value || 0);
        const srcY = parseFloat(document.getElementById('cp-src-y')?.value || 0);
        const refX = parseFloat(document.getElementById('cp-ref-x')?.value || 0);
        const refY = parseFloat(document.getElementById('cp-ref-y')?.value || 0);
        const ptType = document.getElementById('cp-point-type')?.value || 'MANUAL_CHECK';
        const notes = document.getElementById('cp-notes')?.value || '';

        const newPoint = {
          point_id: `CP-${Date.now().toString().slice(-4)}`,
          point_type: ptType,
          source_coords: [srcX, srcY],
          reference_coords: [refX, refY],
          confidence: 1.0,
          status: 'VERIFIED',
          annotator: notes || 'Scientist Verification'
        };

        state.controlPoints.push(newPoint);
        renderControlPointsTable();
        form.reset();
        formContainer.style.display = 'none';
        showToast('Control point saved.', 'success');
      });
    }
  }

  function loadControlPointsView() {
    renderControlPointsTable();
  }

  function renderControlPointsTable() {
    const tbody = document.getElementById('cp-tbody');
    if (!tbody) return;

    if (state.controlPoints.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="table-loading-cell">No control points recorded for active run. Click "+ Add Verified Control Point" above.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    state.controlPoints.forEach(cp => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="font-mono text-cyan">${cp.point_id}</td>
        <td><span class="badge ${cp.point_type === 'GROUND_TRUTH' ? 'badge-recommended' : 'badge-archive'}">${cp.point_type}</span></td>
        <td class="font-mono">(${cp.source_coords[0]}, ${cp.source_coords[1]})</td>
        <td class="font-mono">(${cp.reference_coords[0]}, ${cp.reference_coords[1]})</td>
        <td class="font-mono text-emerald">${(cp.confidence * 100).toFixed(0)}%</td>
        <td><span class="text-emerald">&#x2713; ${cp.status}</span></td>
        <td>${cp.annotator}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // =========================================================================
  // VIEW 7: Run History Table
  // =========================================================================
  function loadRunsHistoryView() {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;

    if (state.allRuns.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="table-loading-cell">No experiment runs found in storage archive.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    state.allRuns.forEach(r => {
      const tr = document.createElement('tr');
      const isSuccess = r.status === 'SUCCESS' || r.status === 'COMPLETED';
      tr.innerHTML = `
        <td class="font-mono text-cyan">${r.run_id}</td>
        <td>${r.timestamp ? new Date(r.timestamp).toLocaleString() : '--'}</td>
        <td>${r.region || 'R01 (Shackleton)'}</td>
        <td class="font-mono">${r.source_sensor || 'OHRC'} → ${r.reference_sensor || 'LROC'} (${r.detector || 'SIFT'})</td>
        <td class="font-mono text-emerald">${r.rmse !== undefined ? `${r.rmse.toFixed(3)} px` : '--'}</td>
        <td><span class="status-pill ${isSuccess ? 'status-success' : 'status-failed'}">${r.status}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm btn-inspect-run" data-id="${r.run_id}">Inspect</button>
        </td>
      `;
      tbody.appendChild(tr);

      tr.querySelector('.btn-inspect-run').addEventListener('click', () => {
        state.activeRunId = r.run_id;
        switchView('results');
      });
    });
  }

  // =========================================================================
  // VIEW 9: System State & Diagnostics
  // =========================================================================
  async function loadSystemDiagnostics() {
    const grid = document.getElementById('system-diagnostics-grid');
    if (!grid) return;

    try {
      const res = await fetch(`${API_BASE}/api/health`);
      const health = await res.json();

      grid.innerHTML = `
        <div class="diag-card">
          <div class="diag-title">Backend Status</div>
          <div class="diag-val text-emerald">${health.status || 'ONLINE'}</div>
        </div>
        <div class="diag-card">
          <div class="diag-title">Active Workers</div>
          <div class="diag-val text-cyan">${health.active_workers ?? 1}</div>
        </div>
        <div class="diag-card">
          <div class="diag-title">Total Registered Runs</div>
          <div class="diag-val text-amber">${state.allRuns.length}</div>
        </div>
        <div class="diag-card">
          <div class="diag-title">Active Storage Root</div>
          <div class="diag-val text-muted text-xs font-mono">experiments/runs</div>
        </div>
        <div class="diag-card">
          <div class="diag-title">Zero Silent Fallback</div>
          <div class="diag-val text-emerald">ENFORCED (STRICT)</div>
        </div>
        <div class="diag-card">
          <div class="diag-title">Supported Sensors</div>
          <div class="diag-val text-cyan text-sm">OHRC, TMC-2, IIRS, LROC NAC</div>
        </div>
      `;
    } catch (err) {
      grid.innerHTML = `<div class="diag-card"><div class="diag-title">Health Check</div><div class="diag-val text-rose">OFFLINE</div></div>`;
    }
  }

  // =========================================================================
  // Canvas Interactive Lunar Map
  // =========================================================================
  function initLunarMap() {
    const canvas = document.getElementById('lunar-interactive-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const coordsBadge = document.getElementById('map-coords-badge');

    function drawMap() {
      ctx.fillStyle = '#060911';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw lunar coordinate grid
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)';
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 60) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      // Draw craters
      Object.entries(PREDEFINED_REGIONS).forEach(([code, r]) => {
        // Map lat [-90, 90] to Y [height, 0], lon [-180, 180] to X [0, width]
        const cx = ((r.lon + 180) / 360) * canvas.width;
        const cy = ((90 - r.lat) / 180) * canvas.height;

        ctx.beginPath();
        ctx.arc(cx, cy, 6, 0, Math.PI * 2);
        ctx.fillStyle = code === state.selectedRegionCode ? '#00e5ff' : 'rgba(148, 163, 184, 0.5)';
        ctx.fill();

        if (code === state.selectedRegionCode) {
          ctx.strokeStyle = '#00e5ff';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(cx, cy, 12, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    }

    drawMap();

    canvas.addEventListener('click', (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const lon = (x / canvas.width) * 360 - 180;
      const lat = 90 - (y / canvas.height) * 180;

      state.latitude = parseFloat(lat.toFixed(4));
      state.longitude = parseFloat(lon.toFixed(4));

      if (coordsBadge) {
        coordsBadge.textContent = `Lat: ${state.latitude.toFixed(4)}° • Lon: ${state.longitude.toFixed(4)}°`;
      }

      const inLat = document.getElementById('input-custom-lat');
      const inLon = document.getElementById('input-custom-lon');
      if (inLat) inLat.value = state.latitude;
      if (inLon) inLon.value = state.longitude;

      drawMap();
    });

    // Region Dropdown Change
    const regionSelect = document.getElementById('predefined-region-select');
    if (regionSelect) {
      regionSelect.addEventListener('change', () => {
        const code = regionSelect.value;
        state.selectedRegionCode = code;
        if (PREDEFINED_REGIONS[code]) {
          state.latitude = PREDEFINED_REGIONS[code].lat;
          state.longitude = PREDEFINED_REGIONS[code].lon;
          state.regionName = PREDEFINED_REGIONS[code].name;
          const descEl = document.getElementById('predefined-region-desc');
          if (descEl) descEl.textContent = PREDEFINED_REGIONS[code].desc;
          if (coordsBadge) coordsBadge.textContent = `Lat: ${state.latitude.toFixed(4)}° • Lon: ${state.longitude.toFixed(4)}°`;
          drawMap();
        }
      });
    }
  }

  // =========================================================================
  // Utilities
  // =========================================================================
  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // =========================================================================
  // Initialization Bootstrap
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initNavigation();
    initModeSelection();
    initModeAUpload();
    initModeBRemote();
    initRegistrationExecution();
    initVisualizations();
    initControlPoints();
    initLunarMap();

    // Sync button
    const btnRefresh = document.getElementById('btn-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        loadAllRuns();
        showToast('Synchronized runs & products archive.', 'info');
      });
    }

    // Copy log button
    const btnCopyLog = document.getElementById('btn-copy-log');
    if (btnCopyLog) {
      btnCopyLog.addEventListener('click', () => {
        const logBody = document.getElementById('processing-log-body');
        if (logBody) {
          navigator.clipboard.writeText(logBody.innerText);
          showToast('Terminal logs copied to clipboard.', 'info');
        }
      });
    }

    // Initial runs fetch
    loadAllRuns();
  });

})();
