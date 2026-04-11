/**
 * FlowMind AI — Wait Times Component
 * WCAG 2.1 AA: filter tabs with role="tablist", progressbar on wait bars,
 * aria-live on best pick, full aria-label on facility cards.
 */

import React, { useState, useEffect } from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchWaitTimes, fetchBestAlternative } from '../../services/api';
import { POLL_INTERVAL, FACILITY_ICONS, FACILITY_LABELS } from '../../utils/constants';
import './WaitTimes.css';

const FILTER_OPTIONS = [
  { key: 'all',        label: 'All' },
  { key: 'food_stall', label: 'Food Stalls' },
  { key: 'restroom',   label: 'Restrooms' },
  { key: 'gate',       label: 'Gates' },
];

function waitColor(minutes) {
  if (minutes >= 20) return '#ef4444';
  if (minutes >= 10) return '#f59e0b';
  if (minutes >= 5)  return '#0ea5e9';
  return '#10b981';
}

function waitLabel(minutes) {
  if (minutes >= 20) return 'long';
  if (minutes >= 10) return 'moderate';
  if (minutes >= 5)  return 'short';
  return 'minimal';
}

export default function WaitTimes() {
  const { data, loading, error } = usePolling(fetchWaitTimes, POLL_INTERVAL);
  const [filter, setFilter] = useState('all');
  const [bestPick, setBestPick] = useState(null);

  useEffect(() => {
    if (filter !== 'all') {
      fetchBestAlternative(filter).then(setBestPick).catch(() => setBestPick(null));
    } else {
      setBestPick(null);
    }
  }, [filter, data]);

  if (loading) {
    return (
      <div className="loading-container" role="status" aria-label="Loading wait times">
        <div className="loading-spinner" aria-hidden="true" />
        <div className="loading-text">Loading wait times...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container" role="alert">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  const facilities = data?.facilities || [];
  const filtered = filter === 'all'
    ? facilities
    : facilities.filter(f => f.facility_type === filter);

  const activeFilterLabel = FILTER_OPTIONS.find(o => o.key === filter)?.label || 'All';

  return (
    <section className="wait-times-page" aria-label="Wait times">
      {/* Filter Tabs */}
      <div
        className="filter-tabs"
        role="tablist"
        aria-label="Filter facilities by type"
      >
        {FILTER_OPTIONS.map(opt => (
          <button
            key={opt.key}
            role="tab"
            className={`filter-tab ${filter === opt.key ? 'active' : ''}`}
            onClick={() => setFilter(opt.key)}
            aria-selected={filter === opt.key}
            aria-controls="facility-grid"
            id={`tab-${opt.key}`}
            onKeyDown={(e) => {
              const idx = FILTER_OPTIONS.findIndex(o => o.key === opt.key);
              if (e.key === 'ArrowRight') {
                const next = FILTER_OPTIONS[(idx + 1) % FILTER_OPTIONS.length];
                setFilter(next.key);
                document.getElementById(`tab-${next.key}`)?.focus();
              } else if (e.key === 'ArrowLeft') {
                const prev = FILTER_OPTIONS[(idx - 1 + FILTER_OPTIONS.length) % FILTER_OPTIONS.length];
                setFilter(prev.key);
                document.getElementById(`tab-${prev.key}`)?.focus();
              }
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Best Pick Banner */}
      <div aria-live="polite" aria-atomic="true">
        {bestPick?.recommended && (
          <div className="glass-card best-pick-banner animate-fade-in" role="status">
            <span className="best-pick-icon" aria-hidden="true">
              {FACILITY_ICONS[filter] || '⭐'}
            </span>
            <div className="best-pick-text">
              <strong>Best Pick: {bestPick.recommended.name}</strong>
              <span>{bestPick.reason}</span>
            </div>
          </div>
        )}
      </div>

      {/* Facility Grid */}
      <div
        id="facility-grid"
        className="facility-grid stagger-children"
        role="tabpanel"
        aria-labelledby={`tab-${filter}`}
        aria-label={`${activeFilterLabel} facilities`}
        aria-live="polite"
        aria-atomic="false"
      >
        {filtered.map(facility => (
          <FacilityCard key={facility.facility_id} facility={facility} />
        ))}
      </div>
    </section>
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
  const maxWait = 30;
  const barPct = Math.min((current_wait_minutes / maxWait) * 100, 100);

  const diff = predicted_wait_minutes - current_wait_minutes;
  const trendClass = diff > 0.5 ? 'up' : diff < -0.5 ? 'down' : 'same';
  const trendArrow = trendClass === 'up' ? '↑' : trendClass === 'down' ? '↓' : '→';
  const trendLabel = trendClass === 'up'
    ? `increasing to ${predicted_wait_minutes.toFixed(0)} minutes`
    : trendClass === 'down'
      ? `decreasing to ${predicted_wait_minutes.toFixed(0)} minutes`
      : `stable at ${predicted_wait_minutes.toFixed(0)} minutes`;

  const zoneName = zone_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const facilityTypeLabel = FACILITY_LABELS?.[facility_type] || facility_type;
  const waitLvl = waitLabel(current_wait_minutes);

  return (
    <article
      className={`glass-card facility-card ${!is_open ? 'closed' : ''}`}
      tabIndex={0}
      aria-label={`${name}, ${facilityTypeLabel} in ${zoneName}. ${is_open ? `Wait: ${current_wait_minutes.toFixed(0)} minutes (${waitLvl}), ${queue_length} in queue, trend ${trendLabel}.` : 'Currently closed.'}`}
    >
      {!is_open && <span className="closed-label" aria-hidden="true">Closed</span>}

      <div className="facility-card-header">
        <div className="facility-info">
          <div className={`facility-icon ${facility_type}`} aria-hidden="true">
            {FACILITY_ICONS[facility_type]}
          </div>
          <div>
            <div className="facility-name">{name}</div>
            <div className="facility-location">{zoneName}</div>
          </div>
        </div>
        <div
          className="facility-wait-badge"
          style={{ color }}
          aria-hidden="true"
        >
          {current_wait_minutes.toFixed(0)}<small>min</small>
        </div>
      </div>

      <div className="wait-bar-row" aria-hidden="true">
        <div className="wait-bar-labels">
          <span>Wait Time</span>
          <span>{current_wait_minutes.toFixed(1)} min</span>
        </div>
        <div
          className="wait-bar-track"
          role="progressbar"
          aria-valuenow={Math.round(current_wait_minutes)}
          aria-valuemin={0}
          aria-valuemax={maxWait}
          aria-label={`Wait time: ${current_wait_minutes.toFixed(0)} of ${maxWait} minutes max`}
        >
          <div
            className="wait-bar-fill"
            style={{ width: `${barPct}%`, background: color }}
          />
        </div>
      </div>

      <div className="facility-meta" aria-hidden="true">
        <div className="queue-info">
          <span className="queue-dot" style={{ background: color }} />
          {queue_length} in queue
        </div>
        <span className={`predicted-tag ${trendClass}`}>
          {trendArrow} {predicted_wait_minutes.toFixed(0)}m
        </span>
      </div>
    </article>
  );
}
