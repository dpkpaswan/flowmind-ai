/**
 * FlowMind AI — Dashboard Component
 * Main overview with stats cards and zone density grid.
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
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Loading stadium data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">Failed to load data: {error}</div>
      </div>
    );
  }

  if (!crowd) return null;

  const zones = crowd.zones || [];
  const sortedZones = [...zones].sort((a, b) => b.current_density - a.current_density);
  const busiest = sortedZones[0];
  const quietest = sortedZones[sortedZones.length - 1];

  // Calculate average wait times by type
  const facilities = waitData?.facilities || [];
  const avgWait = (type) => {
    const matching = facilities.filter(f => f.facility_type === type);
    if (matching.length === 0) return 0;
    return (matching.reduce((sum, f) => sum + f.current_wait_minutes, 0) / matching.length).toFixed(1);
  };

  return (
    <div className="animate-fade-in">
      {/* Stats Row */}
      <div className="stats-row stagger-children">
        <div className="glass-card stat-card accent-indigo">
          <div className="stat-label">Total Attendance</div>
          <div className="stat-value">{crowd.current_attendance?.toLocaleString()}</div>
          <div className="stat-sub">
            of {crowd.total_capacity?.toLocaleString()} capacity
          </div>
        </div>

        <div className="glass-card stat-card accent-cyan">
          <div className="stat-label">Overall Density</div>
          <div className="stat-value">{(crowd.overall_density * 100).toFixed(0)}%</div>
          <div className="stat-sub">
            {crowd.overall_density > 0.7 ? (
              <span className="trend-up">&#9650; High load</span>
            ) : (
              <span className="trend-down">&#9660; Normal</span>
            )}
          </div>
        </div>

        <div className="glass-card stat-card accent-emerald">
          <div className="stat-label">Avg Food Wait</div>
          <div className="stat-value">{avgWait('food_stall')}m</div>
          <div className="stat-sub">across {facilities.filter(f => f.facility_type === 'food_stall').length} stalls</div>
        </div>

        <div className="glass-card stat-card accent-amber">
          <div className="stat-label">Active Alerts</div>
          <div className="stat-value">{alertsData?.count || 0}</div>
          <div className="stat-sub">
            {(alertsData?.alerts || []).filter(a => a.severity === 'critical').length} critical
          </div>
        </div>
      </div>

      {/* Zone Grid */}
      <div className="section-header">
        <div className="section-title">Zone Overview</div>
        <span className="section-badge">{zones.length} zones</span>
      </div>

      <div className="zone-grid stagger-children">
        {sortedZones.map((zone) => (
          <ZoneCard key={zone.zone_id} zone={zone} />
        ))}
      </div>

      {/* Quick Summary */}
      <div className="section-header">
        <div className="section-title">Quick Insights</div>
      </div>
      <div className="stats-row stagger-children">
        <div className="glass-card stat-card accent-cyan">
          <div className="stat-label">Busiest Zone</div>
          <div className="stat-value" style={{ fontSize: '20px' }}>{busiest?.name}</div>
          <div className="stat-sub">{(busiest?.current_density * 100).toFixed(0)}% capacity</div>
        </div>
        <div className="glass-card stat-card accent-emerald">
          <div className="stat-label">Quietest Zone</div>
          <div className="stat-value" style={{ fontSize: '20px' }}>{quietest?.name}</div>
          <div className="stat-sub">{(quietest?.current_density * 100).toFixed(0)}% capacity</div>
        </div>
        <div className="glass-card stat-card accent-indigo">
          <div className="stat-label">Avg Restroom Wait</div>
          <div className="stat-value">{avgWait('restroom')}m</div>
          <div className="stat-sub">across {facilities.filter(f => f.facility_type === 'restroom').length} restrooms</div>
        </div>
        <div className="glass-card stat-card accent-amber">
          <div className="stat-label">Avg Gate Wait</div>
          <div className="stat-value">{avgWait('gate')}m</div>
          <div className="stat-sub">across {facilities.filter(f => f.facility_type === 'gate').length} gates</div>
        </div>
      </div>
    </div>
  );
}

/** Individual Zone Card */
function ZoneCard({ zone }) {
  const densityPct = (zone.current_density * 100).toFixed(0);
  const predictedPct = (zone.predicted_density * 100).toFixed(0);
  const trend = zone.predicted_density > zone.current_density ? 'up' : 'down';

  return (
    <div className="glass-card zone-card">
      <div className="zone-card-header">
        <span className="zone-name">{zone.name}</span>
        <span className={`zone-status-badge ${zone.status}`}>
          {STATUS_LABELS[zone.status]}
        </span>
      </div>

      <div className="density-bar-container">
        <div className="density-bar-labels">
          <span className="density-current">{densityPct}% filled</span>
          <span className="density-predicted">
            {trend === 'up' ? '\u2191' : '\u2193'} {predictedPct}% in {zone.prediction_minutes}m
          </span>
        </div>
        <div className="density-bar-track">
          <div
            className={`density-bar-fill ${zone.status}`}
            style={{ width: `${densityPct}%` }}
          />
          <div
            className="density-bar-predicted"
            style={{ left: `${Math.min(predictedPct, 100)}%` }}
          />
        </div>
      </div>

      <div className="zone-meta">
        <span>{zone.current_count?.toLocaleString()} people</span>
        <span>Cap: {zone.capacity?.toLocaleString()}</span>
      </div>
    </div>
  );
}
