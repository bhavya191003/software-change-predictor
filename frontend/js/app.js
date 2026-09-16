// ─────────────────────────────────────────────────────────────────────
// Main Application — Software Change Predictor
// Manages state, DOM, events, and orchestrates API + Charts.
// ─────────────────────────────────────────────────────────────────────

import { checkHealth, analyzeRepository, exportCSV } from './api.js';
import {
  initializeCharts, destroyAllCharts, renderRiskBarChart,
  renderRadarChart, renderDoughnutChart, renderVelocityLineChart,
  renderBubbleChart, renderParetoChart
} from './charts.js';

// ── Helpers ─────────────────────────────────────────────────────────

/** Derive short filename from full path */
function deriveFilename(filePath) {
  if (!filePath) return 'unknown';
  return filePath.split('/').pop();
}

/**
 * Normalize API response data:
 *  - Add `filename` (basename of file_path)
 *  - Add `risk_score_pct` (0–100 scale for display)
 */
function normalizeData(items) {
  return items.map(d => ({
    ...d,
    filename: deriveFilename(d.file_path),
    risk_score_pct: parseFloat((d.risk_score * 100).toFixed(1))
  }));
}

/**
 * Classify a 0–1 risk score into a category.
 * Matches backend thresholds in config.py.
 */
function classifyRisk(score) {
  if (score >= 0.8) return 'Critical';
  if (score >= 0.6) return 'High';
  if (score >= 0.3) return 'Medium';
  return 'Low';
}

// ── State ───────────────────────────────────────────────────────────

const state = {
  data: [],        // normalized FileRiskMetric[]
  summary: {},     // AnalysisSummary
  predictions: [], // PredictionResult[]
  loading: false,
  activeTab: 'overview',
  sortCol: 'risk_score',
  sortAsc: false,
  searchQuery: ''
};

// ── DOM Cache ───────────────────────────────────────────────────────

const dom = {};

function cacheDOM() {
  dom.homeView        = document.getElementById('homeView');
  dom.backBtn         = document.getElementById('backBtn');
  dom.urlInput        = document.getElementById('repoUrl');
  dom.analyzeBtn      = document.getElementById('analyzeBtn');
  dom.statusDot       = document.getElementById('statusDot');
  dom.skeleton        = document.getElementById('loadingSkeleton');
  dom.results         = document.getElementById('resultsContainer');
  dom.toastContainer  = document.getElementById('toastContainer');
  dom.searchInput     = document.getElementById('searchInput');
  dom.tableBody       = document.getElementById('tableBody');
  dom.tabBtns         = document.querySelectorAll('.tab-btn');
  dom.tabContents     = document.querySelectorAll('.tab-content');
  dom.exportBtn       = document.getElementById('exportBtn');

  dom.valFiles    = document.getElementById('valFiles');
  dom.valHighRisk = document.getElementById('valHighRisk');
  dom.valEntropy  = document.getElementById('valEntropy');
  dom.valMaxRisk  = document.getElementById('valMaxRisk');
}

// ── Event Binding ───────────────────────────────────────────────────

function bindEvents() {
  if (dom.backBtn) {
    dom.backBtn.addEventListener('click', (e) => {
      e.preventDefault();
      dom.results.classList.remove('active');
      dom.homeView.style.display = 'block';
    });
  }
  dom.analyzeBtn.addEventListener('click', handleAnalyze);
  dom.urlInput.addEventListener('keypress', e => { if (e.key === 'Enter') handleAnalyze(); });
  dom.searchInput.addEventListener('input', e => handleSearch(e.target.value));
  dom.exportBtn.addEventListener('click', handleExport);

  dom.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => handleTabChange(btn.dataset.tab));
  });

  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => handleSort(th.dataset.sort));
  });
}

// ── Initialization ──────────────────────────────────────────────────

async function initApp() {
  cacheDOM();
  bindEvents();
  initializeCharts();

  // Check backend connectivity
  try {
    const health = await checkHealth();
    if (health && health.status === 'healthy') {
      dom.statusDot.classList.add('connected');
    }
  } catch {
    dom.statusDot.classList.remove('connected');
    console.warn('Backend API is not reachable. Start the server with: python -m uvicorn backend.api:app --port 8000');
  }
}

document.addEventListener('DOMContentLoaded', initApp);

// ── Core Analysis Flow ──────────────────────────────────────────────

async function handleAnalyze() {
  const url = dom.urlInput.value.trim();
  if (!url) {
    showToast('Please enter a repository URL', 'error');
    return;
  }

  showLoading();
  dom.results.classList.remove('active');

  try {
    const response = await analyzeRepository(url);

    if (response && response.status === 'success') {
      state.data        = normalizeData(response.data || []);
      state.summary     = response.summary || {};
      state.predictions = response.predictions || [];

      renderAll();
      if (dom.homeView) dom.homeView.style.display = 'none';
      dom.results.classList.add('active');
      window.scrollTo(0, 0);
      showToast(`Analysis complete! ${state.data.length} files analyzed in ${(state.summary.analysis_duration_seconds || 0).toFixed(1)}s`, 'success');
    } else {
      showToast('Analysis returned no data. Check the repository URL.', 'error');
    }
  } catch (error) {
    console.error('Analysis error:', error);
    showToast(error.message || 'Analysis failed', 'error');
  } finally {
    hideLoading();
  }
}

// ── Rendering ───────────────────────────────────────────────────────

function renderAll() {
  renderSummaryCards(state.summary);
  renderFileTable();
  renderCharts();
  renderPredictionsPanel();
}

function renderSummaryCards(summary) {
  if (!summary) return;
  animateCountUp(dom.valFiles,    summary.total_files || 0, 800);
  animateCountUp(dom.valHighRisk, summary.high_risk_count || 0, 800);
  animateCountUp(dom.valEntropy,  summary.avg_entropy || 0, 800, 2);
  animateCountUp(dom.valMaxRisk,  parseFloat(((summary.max_risk_score || 0) * 100).toFixed(1)), 800, 1);
}

function renderCharts() {
  if (!state.data.length) return;
  destroyAllCharts();

  // Small delay to ensure DOM is visible before chart render
  requestAnimationFrame(() => {
    renderRiskBarChart(state.data);
    renderDoughnutChart(state.data);
    renderRadarChart(state.data);
    renderParetoChart(state.data);
    renderVelocityLineChart(state.data);
    renderBubbleChart(state.data);
  });
}

function renderFileTable() {
  const query = state.searchQuery.toLowerCase();
  let filtered = state.data.filter(d =>
    d.filename.toLowerCase().includes(query) ||
    d.file_path.toLowerCase().includes(query)
  );

  filtered.sort((a, b) => {
    let valA = a[state.sortCol];
    let valB = b[state.sortCol];
    if (valA === undefined) valA = '';
    if (valB === undefined) valB = '';
    if (typeof valA === 'string') {
      return state.sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortAsc ? valA - valB : valB - valA;
  });

  dom.tableBody.innerHTML = filtered.map(d => {
    const riskCat = d.risk_category || classifyRisk(d.risk_score);
    return `
      <tr>
        <td class="file-name" title="${d.file_path}">${d.file_path}</td>
        <td>${d.total_churn}</td>
        <td>${d.entropy.toFixed(2)}</td>
        <td>${d.author_count}</td>
        <td>
          <span class="badge ${riskCat.toLowerCase()}">${riskCat} (${d.risk_score_pct}%)</span>
        </td>
      </tr>
    `;
  }).join('');
}

function renderPredictionsPanel() {
  const panel = document.getElementById('predictionsTab');
  if (!panel) return;

  if (!state.predictions || !state.predictions.length) {
    panel.innerHTML = '<p style="color: var(--text-muted)">No predictions available. Run an analysis first.</p>';
    return;
  }

  const trendIcon = (trend) => {
    if (trend === 'Increasing') return '<span style="color: var(--color-critical)">▲ Increasing</span>';
    if (trend === 'Decreasing') return '<span style="color: var(--color-low)">▼ Decreasing</span>';
    return '<span style="color: var(--color-medium)">● Stable</span>';
  };

  const sorted = [...state.predictions].sort((a, b) => b.current_risk - a.current_risk);
  const top20 = sorted.slice(0, 20);

  panel.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Current Risk</th>
          <th>Predicted Risk</th>
          <th>Trend</th>
          <th>ML Confidence</th>
        </tr>
      </thead>
      <tbody>
        ${top20.map(p => {
          const riskCat = classifyRisk(p.current_risk);
          const predPct = (p.predicted_risk * 100).toFixed(0);
          const curPct = (p.current_risk * 100).toFixed(1);
          const conf = (p.confidence * 100).toFixed(0);
          return `<tr>
            <td class="file-name">${deriveFilename(p.file_path)}</td>
            <td><span class="badge ${riskCat.toLowerCase()}">${curPct}%</span></td>
            <td>${predPct}%</td>
            <td>${trendIcon(p.trend)}</td>
            <td>${conf}%</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  `;
}

// ── Interactions ─────────────────────────────────────────────────────

function handleSort(column) {
  if (state.sortCol === column) {
    state.sortAsc = !state.sortAsc;
  } else {
    state.sortCol = column;
    state.sortAsc = false;
  }
  renderFileTable();
}

function handleSearch(query) {
  state.searchQuery = query;
  renderFileTable();
}

function handleTabChange(tabId) {
  state.activeTab = tabId;
  dom.tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  dom.tabContents.forEach(c => c.classList.toggle('active', c.id === tabId));

  // Re-render charts when switching to their tab (ensures proper sizing)
  if (['overview', 'riskAnalysis', 'timeline'].includes(tabId) && state.data.length) {
    requestAnimationFrame(() => renderCharts());
  }
}

async function handleExport() {
  const url = dom.urlInput.value.trim();
  if (!url) {
    showToast('Enter a repository URL first', 'error');
    return;
  }
  try {
    showToast('Generating CSV... this may take a moment.', 'success');
    await exportCSV(url);
    showToast('CSV exported successfully!', 'success');
  } catch (e) {
    showToast('Export failed: ' + (e.message || 'Unknown error'), 'error');
  }
}

// ── UI Utilities ────────────────────────────────────────────────────

function showLoading() {
  state.loading = true;
  dom.skeleton.classList.add('active');
  dom.analyzeBtn.disabled = true;
  dom.analyzeBtn.innerText = 'Analyzing...';
}

function hideLoading() {
  state.loading = false;
  dom.skeleton.classList.remove('active');
  dom.analyzeBtn.disabled = false;
  dom.analyzeBtn.innerText = 'Analyze';
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = message;
  dom.toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

/**
 * Animate a number counting up from 0 to target.
 * @param {HTMLElement} element  - DOM element to update
 * @param {number} target       - Target number
 * @param {number} duration     - Animation duration in ms
 * @param {number} decimals     - Decimal places (0 = integer)
 */
function animateCountUp(element, target, duration = 800, decimals = 0) {
  if (!element) return;
  if (target === 0) {
    element.innerText = decimals > 0 ? '0.' + '0'.repeat(decimals) : '0';
    return;
  }

  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = eased * target;

    element.innerText = decimals > 0 ? current.toFixed(decimals) : Math.floor(current).toString();

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.innerText = decimals > 0 ? target.toFixed(decimals) : Math.floor(target).toString();
    }
  }

  requestAnimationFrame(update);
}
