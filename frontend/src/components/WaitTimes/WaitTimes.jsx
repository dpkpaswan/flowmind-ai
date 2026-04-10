/**
 * FlowMind AI — Wait Times Component
 * Filterable facility wait time cards with predictions and best-pick recommendations.
 */

import React, { useState, useEffect } from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchWaitTimes, fetchBestAlternative } from '../../services/api';
import { POLL_INTERVAL, FACILITY_ICONS, FACILITY_LABELS } from '../../utils/constants';
import './WaitTimes.css';

const FILTER_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'food_stall', label: '\uD83C\uDF54 Food Stalls' },
  { key: 'restroom', label: '\uD83D\uDEBB Restrooms' },
  { key: 'gate', label: '\uD83D\uDEAA Gates' },
];

function waitColor(minutes) {
  if (minutes >= 20) return '#ef4444';
  if (minutes >= 10) return '#f59e0b';
  if (minutes >= 5) return '#0ea5e9';
  return '#10b981';
}

export default function WaitTimes() {
  const { data, loading, error } = usePolling(fetchWaitTimes, POLL_INTERVAL);
  const [filter, setFilter] = useState('all');
  const [bestPick, setBestPick] = useState(null);

  // Fetch best alternative when filter changes
  useEffect(() => {
    if (filter !== 'all') {
      fetchBestAlternative(filter).then(setBestPick).catch(() => setBestPick(null));
    } else {
      setBestPick(null);
    }
  }, [filter, data]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Loading wait times...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  const facilities = data?.facilities || [];
  const filtered = filter === 'all'
    ? facilities
    : facilities.filter(f => f.facility_type === filter);

  return (
    <div className="wait-times-page">
      {/* Filter Tabs */}
      <div className="filter-tabs">
        {FILTER_OPTIONS.map(opt => (
          <button
            key={opt.key}
            className={`filter-tab ${filter === opt.key ? 'active' : ''}`}
            onClick={() => setFilter(opt.key)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Best Pick Banner */}
      {bestPick?.recommended && (
        <div className="glass-card best-pick-banner animate-fade-in">
          <span className="best-pick-icon">{FACILITY_ICONS[filter] || '\u2B50'}</span>
          <div className="best-pick-text">
            <strong>Best Pick: {bestPick.recommended.name}</strong>
            <span>{bestPick.reason}</span>
          </div>
        </div>
      )}

      {/* Facility Grid */}
      <div className="facility-grid stagger-children">
        {filtered.map(facility => (
          <FacilityCard key={facility.facility_id} facility={facility} />
        ))}
      </div>
    </div>
  );
}

function FacilityCard({ facility }) {
  const {
    name,
    facility_type,
    zone_id,
    current_wait_minutes,
    predicted_wait_minutes,
    queue_length,
    is_open,
  } = facility;

  const color = waitColor(current_wait_minutes);
  const maxWait = 30; // max for bar scaling
  const barPct = Math.min((current_wait_minutes / maxWait) * 100, 100);

  const diff = predicted_wait_minutes - current_wait_minutes;
  const trendClass = diff > 0.5 ? 'up' : diff < -0.5 ? 'down' : 'same';
  const trendLabel =
    trendClass === 'up'
      ? `\u2191 ${predicted_wait_minutes.toFixed(0)}m`
      : trendClass === 'down'
        ? `\u2193 ${predicted_wait_minutes.toFixed(0)}m`
        : `\u2192 ${predicted_wait_minutes.toFixed(0)}m`;

  const zoneName = zone_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className={`glass-card facility-card ${!is_open ? 'closed' : ''}`}>
      {!is_open && <span className="closed-label">Closed</span>}

      <div className="facility-card-header">
        <div className="facility-info">
          <div className={`facility-icon ${facility_type}`}>
            {FACILITY_ICONS[facility_type]}
          </div>
          <div>
            <div className="facility-name">{name}</div>
            <div className="facility-location">{zoneName}</div>
          </div>
        </div>
        <div className="facility-wait-badge" style={{ color }}>
          {current_wait_minutes.toFixed(0)}
          <small>min</small>
        </div>
      </div>

      <div className="wait-bar-row">
        <div className="wait-bar-labels">
          <span>Wait Time</span>
          <span>{current_wait_minutes.toFixed(1)} min</span>
        </div>
        <div className="wait-bar-track">
          <div
            className="wait-bar-fill"
            style={{ width: `${barPct}%`, background: color }}
          />
        </div>
      </div>

      <div className="facility-meta">
        <div className="queue-info">
          <span className="queue-dot" style={{ background: color }} />
          {queue_length} in queue
        </div>
        <span className={`predicted-tag ${trendClass}`}>
          {trendLabel}
        </span>
      </div>
    </div>
  );
}
