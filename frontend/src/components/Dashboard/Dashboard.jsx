/**
 * FlowMind AI — Dashboard Component
 * WCAG 2.1 AA: sections with headings, aria-live on dynamic data, aria-label on stat cards.
 */

import React from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchCrowdData, fetchAlerts, fetchWaitTimes } from '../../services/api';
import { POLL_INTERVAL, STATUS_LABELS } from '../../utils/constants';
import './Dashboard.css';

export default function Dashboard() {
  const { data: crowd, loading, error } = usePolling(fetchCrowdData, POLL_INTERVAL);
  const { data: alertsData } = usePolling(fetchAlerts, POLL_INTERVAL);
  const { data: waitData } = usePolling(fetchWaitTimes, POLL_INTERVAL);

  if (loading) {
    return (
      <div className="loading-container" role="status" aria-label="Loading stadium data">
        <div className="loading-spinner" aria-hidden="true" />
        <div className="loading-text">Loading stadium data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container" role="alert">
        <div className="error-message">Failed to load data: {error}</div>
      </div>
    );
  }

  if (!crowd) return null;

  const zones = crowd.zones || [];
  const sortedZones = [...zones].sort((a, b) => b.current_density - a.current_density);
  const busiest = sortedZones[0];
  const quietest = sortedZones[sortedZones.length - 1];

  const facilities = waitData?.facilities || [];
  const avgWait = (type) => {
    const matching = facilities.filter(f => f.facility_type === type);
    if (matching.length === 0) return 0;
    return (matching.reduce((sum, f) => sum + f.current_wait_minutes, 0) / matching.length).toFixed(1);
  };

  const criticalAlerts = (alertsData?.alerts || []).filter(a => a.severity === 'critical').length;

  return (
    <div className="animate-fade-in">
      {/* Stats Row */}
      <section aria-label="Key statistics">
        <div className="stats-row stagger-children" aria-live="polite" aria-atomic="false">
          <article className="glass-card stat-card accent-indigo" aria-label={`Total attendance: ${crowd.current_attendance?.toLocaleString()} of ${crowd.total_capacity?.toLocaleString()} capacity`}>
            <div className="stat-label">Total Attendance</div>
            <div className="stat-value" aria-hidden="true">{crowd.current_attendance?.toLocaleString()}</div>
            <div className="stat-sub" aria-hidden="true">of {crowd.total_capacity?.toLocaleString()} capacity</div>
          </article>

          <article className="glass-card stat-card accent-cyan" aria-label={`Overall density: ${(crowd.overall_density * 100).toFixed(0)}%`}>
            <div className="stat-label">Overall Density</div>
            <div className="stat-value" aria-hidden="true">{(crowd.overall_density * 100).toFixed(0)}%</div>
            <div className="stat-sub" aria-hidden="true">
              {crowd.overall_density > 0.7 ? (
                <span className="trend-up">&#9650; High load</span>
              ) : (
                <span className="trend-down">&#9660; Normal</span>
              )}
            </div>
          </article>

          <article className="glass-card stat-card accent-emerald" aria-label={`Average food wait: ${avgWait('food_stall')} minutes`}>
            <div className="stat-label">Avg Food Wait</div>
            <div className="stat-value" aria-hidden="true">{avgWait('food_stall')}m</div>
            <div className="stat-sub" aria-hidden="true">across {facilities.filter(f => f.facility_type === 'food_stall').length} stalls</div>
          </article>

          <article className="glass-card stat-card accent-amber" aria-label={`Active alerts: ${alertsData?.count || 0} total, ${criticalAlerts} critical`}>
            <div className="stat-label">Active Alerts</div>
            <div className="stat-value" aria-hidden="true">{alertsData?.count || 0}</div>
            <div className="stat-sub" aria-hidden="true">{criticalAlerts} critical</div>
          </article>
        </div>
      </section>

      {/* Zone Grid */}
      <section aria-label="Zone overview">
        <div className="section-header">
          <h2 className="section-title">Zone Overview</h2>
          <span className="section-badge" aria-label={`${zones.length} zones`}>{zones.length} zones</span>
        </div>

        <div className="zone-grid stagger-children" aria-live="polite" aria-atomic="false">
          {sortedZones.map((zone) => (
            <ZoneCard key={zone.zone_id} zone={zone} />
          ))}
        </div>
      </section>

      {/* Quick Summary */}
      <section aria-label="Quick insights">
        <div className="section-header">
          <h2 className="section-title">Quick Insights</h2>
        </div>
        <div className="stats-row stagger-children" aria-live="polite" aria-atomic="false">
          <article className="glass-card stat-card accent-cyan" aria-label={`Busiest zone: ${busiest?.name} at ${(busiest?.current_density * 100).toFixed(0)}% capacity`}>
            <div className="stat-label">Busiest Zone</div>
            <div className="stat-value" style={{ fontSize: '20px' }} aria-hidden="true">{busiest?.name}</div>
            <div className="stat-sub" aria-hidden="true">{(busiest?.current_density * 100).toFixed(0)}% capacity</div>
          </article>
          <article className="glass-card stat-card accent-emerald" aria-label={`Quietest zone: ${quietest?.name} at ${(quietest?.current_density * 100).toFixed(0)}% capacity`}>
            <div className="stat-label">Quietest Zone</div>
            <div className="stat-value" style={{ fontSize: '20px' }} aria-hidden="true">{quietest?.name}</div>
            <div className="stat-sub" aria-hidden="true">{(quietest?.current_density * 100).toFixed(0)}% capacity</div>
          </article>
          <article className="glass-card stat-card accent-indigo" aria-label={`Average restroom wait: ${avgWait('restroom')} minutes`}>
            <div className="stat-label">Avg Restroom Wait</div>
            <div className="stat-value" aria-hidden="true">{avgWait('restroom')}m</div>
            <div className="stat-sub" aria-hidden="true">across {facilities.filter(f => f.facility_type === 'restroom').length} restrooms</div>
          </article>
          <article className="glass-card stat-card accent-amber" aria-label={`Average gate wait: ${avgWait('gate')} minutes`}>
            <div className="stat-label">Avg Gate Wait</div>
            <div className="stat-value" aria-hidden="true">{avgWait('gate')}m</div>
            <div className="stat-sub" aria-hidden="true">across {facilities.filter(f => f.facility_type === 'gate').length} gates</div>
          </article>
        </div>
      </section>
    </div>
  );
}

/** Individual Zone Card */
function ZoneCard({ zone }) {
  const densityPct = (zone.current_density * 100).toFixed(0);
  const predictedPct = (zone.predicted_density * 100).toFixed(0);
  const trend = zone.predicted_density > zone.current_density ? 'up' : 'down';
  const trendLabel = trend === 'up' ? 'increasing' : 'decreasing';
  const statusText = STATUS_LABELS[zone.status] || zone.status;

  return (
    <article
      className="glass-card zone-card"
      tabIndex={0}
      aria-label={`${zone.name}: ${densityPct}% full, status ${statusText}, predicted ${predictedPct}% in ${zone.prediction_minutes} minutes`}
    >
      <div className="zone-card-header">
        <span className="zone-name">{zone.name}</span>
        <span className={`zone-status-badge ${zone.status}`} aria-label={`Status: ${statusText}`}>
          {statusText}
        </span>
      </div>

      <div className="density-bar-container">
        <div className="density-bar-labels">
          <span className="density-current">{densityPct}% filled</span>
          <span className="density-predicted" aria-label={`Predicted ${predictedPct}% in ${zone.prediction_minutes} minutes, ${trendLabel}`}>
            {trend === 'up' ? '↑' : '↓'} {predictedPct}% in {zone.prediction_minutes}m
          </span>
        </div>
        <div
          className="density-bar-track"
          role="progressbar"
          aria-valuenow={Number(densityPct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${zone.name} density: ${densityPct}%`}
        >
          <div
            className={`density-bar-fill ${zone.status}`}
            style={{ width: `${densityPct}%` }}
          />
          <div
            className="density-bar-predicted"
            style={{ left: `${Math.min(Number(predictedPct), 100)}%` }}
            aria-hidden="true"
          />
        </div>
      </div>

      <div className="zone-meta" aria-hidden="true">
        <span>{zone.current_count?.toLocaleString()} people</span>
        <span>Cap: {zone.capacity?.toLocaleString()}</span>
      </div>
    </article>
  );
}
