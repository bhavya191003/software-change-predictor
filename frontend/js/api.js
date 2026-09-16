// ─────────────────────────────────────────────────────────────────────
// API Client Module — Software Change Predictor
// Handles all communication with the FastAPI backend.
// ─────────────────────────────────────────────────────────────────────

// Auto-detect the API base URL from the current page origin.
// When served via FastAPI, the frontend and API share the same origin.
// Override by setting window.API_URL before this script loads.
const API_BASE_URL = window.location.origin;

function getApiBaseUrl() {
  return window.API_URL || API_BASE_URL;
}

function setApiBaseUrl(url) {
  window.API_URL = url;
}

/**
 * Check if the backend API is reachable.
 */
async function checkHealth() {
  const response = await fetch(`${getApiBaseUrl()}/health`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error('Health check failed');
  return await response.json();
}

/**
 * Send a repository URL to the backend for full analysis.
 * Timeout set to 5 minutes since mining large repos is slow.
 */
async function analyzeRepository(repoUrl) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min timeout

  try {
    const response = await fetch(`${getApiBaseUrl()}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: repoUrl }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Analysis request timed out (5 min). Try a smaller repository.');
    }
    throw error;
  }
}

/**
 * Trigger a CSV export download from the backend.
 */
async function exportCSV(repoUrl) {
  const response = await fetch(`${getApiBaseUrl()}/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: repoUrl })
  });
  
  if (!response.ok) throw new Error('Export failed');
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = `scp-analysis-${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export { checkHealth, analyzeRepository, exportCSV, getApiBaseUrl, setApiBaseUrl };
