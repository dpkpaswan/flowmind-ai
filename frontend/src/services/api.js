/**
 * FlowMind AI — API Client
 * Centralized fetch wrapper for all backend endpoints.
 */

import { API_BASE } from '../utils/constants';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// ── Crowd Endpoints ───────────────────────────────────────────────────────

export async function fetchCrowdData() {
  return request('/api/crowd/current');
}

export async function fetchCrowdPredictions() {
  return request('/api/crowd/predict');
}

export async function fetchHeatmapData() {
  return request('/api/crowd/heatmap');
}

// ── Wait Time Endpoints ───────────────────────────────────────────────────

export async function fetchWaitTimes() {
  return request('/api/wait-times');
}

export async function fetchBestAlternative(facilityType) {
  return request(`/api/wait-times/best/${facilityType}`);
}

export async function fetchFacilityPrediction(facilityId) {
  return request(`/api/wait-times/${facilityId}/predict`);
}

// ── Alert Endpoints ───────────────────────────────────────────────────────

export async function fetchAlerts() {
  return request('/api/alerts');
}

// ── Chat Endpoint ─────────────────────────────────────────────────────────

export async function sendChatMessage(message, userLocation = null, language = 'en') {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      user_location: userLocation,
      language,
    }),
  });
}

export async function fetchChatLanguages() {
  return request('/api/chat/languages');
}

// ── Simulation Endpoints ──────────────────────────────────────────────────

export async function fetchSimulationStatus() {
  return request('/api/simulation/status');
}

export async function startSimulation(speed = 10) {
  return request('/api/simulation/start', {
    method: 'POST',
    body: JSON.stringify({ speed }),
  });
}

export async function stopSimulation() {
  return request('/api/simulation/stop', { method: 'POST' });
}

export async function setSimulationSpeed(speed) {
  return request('/api/simulation/speed', {
    method: 'POST',
    body: JSON.stringify({ speed }),
  });
}

// ── Emergency Endpoints ───────────────────────────────────────────────────

export async function triggerEvacuation() {
  return request('/api/emergency/evacuate', { method: 'POST' });
}

export async function cancelEvacuation() {
  return request('/api/emergency/cancel', { method: 'POST' });
}

export async function fetchEvacuationStatus() {
  return request('/api/emergency/status');
}
