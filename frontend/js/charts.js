// ─────────────────────────────────────────────────────────────────────
// Charts Module — Software Change Predictor
// All Chart.js chart configurations and rendering functions.
// IMPORTANT: We use [...data].sort() (spread copy) so we never
// mutate the shared state.data array.
// ─────────────────────────────────────────────────────────────────────

const chartInstances = {};

const colors = {
  critical: '#ff4757',
  high: '#ff8c42',
  medium: '#ffd93d',
  low: '#00d4aa',
  grid: 'rgba(255, 255, 255, 0.05)',
  text: '#8e8eb2'
};

export function initializeCharts() {
  Chart.defaults.color = colors.text;
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(25, 25, 60, 0.9)';
  Chart.defaults.plugins.tooltip.titleColor = '#fff';
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
}

export function destroyAllCharts() {
  Object.keys(chartInstances).forEach(key => {
    if (chartInstances[key]) {
      chartInstances[key].destroy();
      chartInstances[key] = null;
    }
  });
}

function getRiskColor(score) {
  if (score >= 0.8) return colors.critical;
  if (score >= 0.6) return colors.high;
  if (score >= 0.3) return colors.medium;
  return colors.low;
}

/** Shortens a filename for chart labels */
function shortName(d) {
  return d.filename || d.file_path.split('/').pop();
}

// ── 1. Risk Bar Chart (Top 10 files by risk) ────────────────────────
export function renderRiskBarChart(data) {
  const ctx = document.getElementById('riskBarChart');
  if (!ctx) return;
  if (chartInstances.riskBar) chartInstances.riskBar.destroy();

  const top10 = [...data].sort((a, b) => b.risk_score - a.risk_score).slice(0, 10);

  chartInstances.riskBar = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top10.map(d => shortName(d)),
      datasets: [{
        label: 'Risk Score (%)',
        data: top10.map(d => d.risk_score_pct),
        backgroundColor: top10.map(d => getRiskColor(d.risk_score)),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: colors.grid }, beginAtZero: true, max: 100 },
        x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } }
      }
    }
  });
}

// ── 2. Radar Chart (Multi-axis comparison of top 5) ─────────────────
export function renderRadarChart(data) {
  const ctx = document.getElementById('radarChart');
  if (!ctx) return;
  if (chartInstances.radar) chartInstances.radar.destroy();

  const top5 = [...data].sort((a, b) => b.risk_score - a.risk_score).slice(0, 5);
  
  // Normalize each axis to roughly 0-100 for visual comparison
  const maxChurn = Math.max(...data.map(d => d.total_churn), 1);
  const maxVelocity = Math.max(...data.map(d => d.velocity), 1);
  const maxEntropy = Math.max(...data.map(d => d.entropy), 1);
  const maxAuthors = Math.max(...data.map(d => d.author_count), 1);
  
  const palette = [colors.critical, colors.high, colors.medium, colors.low, '#4a90e2'];

  chartInstances.radar = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['Entropy', 'Churn', 'Bug Ratio', 'Velocity', 'Authors'],
      datasets: top5.map((d, i) => ({
        label: shortName(d),
        data: [
          (d.entropy / maxEntropy) * 100,
          (d.total_churn / maxChurn) * 100,
          d.bug_ratio * 100,
          (d.velocity / maxVelocity) * 100,
          (d.author_count / maxAuthors) * 100
        ],
        borderColor: palette[i],
        backgroundColor: `${palette[i]}22`,
        borderWidth: 2,
        pointBackgroundColor: palette[i]
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: colors.grid },
          grid: { color: colors.grid },
          pointLabels: { color: colors.text, font: { size: 12 } },
          ticks: { display: false },
          suggestedMin: 0,
          suggestedMax: 100
        }
      },
      plugins: {
        legend: { position: 'bottom', labels: { color: colors.text, boxWidth: 12 } }
      }
    }
  });
}

// ── 3. Doughnut Chart (Risk category distribution) ──────────────────
export function renderDoughnutChart(data) {
  const ctx = document.getElementById('doughnutChart');
  if (!ctx) return;
  if (chartInstances.doughnut) chartInstances.doughnut.destroy();

  const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  data.forEach(d => {
    const cat = d.risk_category || classifyRisk(d.risk_score);
    counts[cat] = (counts[cat] || 0) + 1;
  });

  chartInstances.doughnut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Critical', 'High', 'Medium', 'Low'],
      datasets: [{
        data: [counts.Critical, counts.High, counts.Medium, counts.Low],
        backgroundColor: [colors.critical, colors.high, colors.medium, colors.low],
        borderWidth: 0,
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { position: 'right', labels: { color: colors.text, padding: 16 } }
      }
    }
  });
}

// ── 4. Velocity Line Chart ──────────────────────────────────────────
export function renderVelocityLineChart(data) {
  const ctx = document.getElementById('velocityChart');
  if (!ctx) return;
  if (chartInstances.velocity) chartInstances.velocity.destroy();

  const top10 = [...data].sort((a, b) => b.velocity - a.velocity).slice(0, 10);

  chartInstances.velocity = new Chart(ctx, {
    type: 'line',
    data: {
      labels: top10.map(d => shortName(d)),
      datasets: [{
        label: 'Change Velocity (EMA)',
        data: top10.map(d => d.velocity),
        borderColor: '#4a90e2',
        backgroundColor: 'rgba(74, 144, 226, 0.15)',
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointBackgroundColor: '#fff',
        pointBorderColor: '#4a90e2',
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: colors.grid }, beginAtZero: true },
        x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } }
      }
    }
  });
}

// ── 5. Bubble Chart (Authors vs Churn, size = risk) ─────────────────
export function renderBubbleChart(data) {
  const ctx = document.getElementById('bubbleChart');
  if (!ctx) return;
  if (chartInstances.bubble) chartInstances.bubble.destroy();

  // Only show top 30 to avoid chart clutter
  const top30 = [...data].sort((a, b) => b.risk_score - a.risk_score).slice(0, 30);

  chartInstances.bubble = new Chart(ctx, {
    type: 'bubble',
    data: {
      datasets: [{
        label: 'Files',
        data: top30.map(d => ({
          x: d.author_count,
          y: d.total_churn,
          r: Math.max(4, d.risk_score_pct / 5)
        })),
        backgroundColor: top30.map(d => `${getRiskColor(d.risk_score)}88`),
        borderColor: top30.map(d => getRiskColor(d.risk_score)),
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: colors.grid }, title: { display: true, text: 'Author Count', color: colors.text } },
        y: { grid: { color: colors.grid }, title: { display: true, text: 'Total Churn (Lines Changed)', color: colors.text } }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              const d = top30[context.dataIndex];
              return d ? `${shortName(d)}: Risk ${d.risk_score_pct}%` : '';
            }
          }
        }
      }
    }
  });
}

// ── 6. Pareto Chart (Cumulative risk) ───────────────────────────────
export function renderParetoChart(data) {
  const ctx = document.getElementById('paretoChart');
  if (!ctx) return;
  if (chartInstances.pareto) chartInstances.pareto.destroy();

  const sorted = [...data].sort((a, b) => b.risk_score - a.risk_score);
  const totalRisk = sorted.reduce((sum, d) => sum + d.risk_score, 0);
  
  // Calculate cumulative percentage over ALL items, then slice for display
  let cumulative = 0;
  const withCumulative = sorted.map(d => {
    cumulative += d.risk_score;
    return { ...d, cumulativePct: totalRisk > 0 ? (cumulative / totalRisk) * 100 : 0 };
  });

  const top15 = withCumulative.slice(0, 15);

  chartInstances.pareto = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top15.map(d => shortName(d)),
      datasets: [
        {
          type: 'line',
          label: 'Cumulative %',
          data: top15.map(d => d.cumulativePct),
          borderColor: '#9013fe',
          backgroundColor: 'rgba(144, 19, 254, 0.1)',
          borderWidth: 2,
          yAxisID: 'y1',
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#9013fe'
        },
        {
          type: 'bar',
          label: 'Risk Score (%)',
          data: top15.map(d => d.risk_score_pct),
          backgroundColor: top15.map(d => `${getRiskColor(d.risk_score)}aa`),
          borderRadius: 3,
          yAxisID: 'y'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: colors.grid }, beginAtZero: true, max: 100, title: { display: true, text: 'Risk %', color: colors.text } },
        y1: { position: 'right', grid: { display: false }, beginAtZero: true, max: 100, title: { display: true, text: 'Cumulative %', color: colors.text } },
        x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } }
      },
      plugins: {
        legend: { position: 'bottom', labels: { color: colors.text } }
      }
    }
  });
}

/** Local helper matching the backend classification */
function classifyRisk(score) {
  if (score >= 0.8) return 'Critical';
  if (score >= 0.6) return 'High';
  if (score >= 0.3) return 'Medium';
  return 'Low';
}
