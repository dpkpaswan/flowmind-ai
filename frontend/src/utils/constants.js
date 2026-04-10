/**
 * FlowMind AI — Application Constants
 */

export const API_BASE = 'http://localhost:8000';

export const POLL_INTERVAL = 15000; // 15 seconds

export const STATUS_COLORS = {
  low: '#10b981',
  moderate: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
};

export const STATUS_LABELS = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  critical: 'Critical',
};

export const SEVERITY_COLORS = {
  info: '#0ea5e9',
  warning: '#f59e0b',
  critical: '#ef4444',
};

export const FACILITY_ICONS = {
  food_stall: '\uD83C\uDF54',
  restroom: '\uD83D\uDEBB',
  gate: '\uD83D\uDEAA',
  merchandise: '\uD83D\uDED2',
};

export const FACILITY_LABELS = {
  food_stall: 'Food Stall',
  restroom: 'Restroom',
  gate: 'Gate',
  merchandise: 'Merchandise',
};
