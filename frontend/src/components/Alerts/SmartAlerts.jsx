/**
 * FlowMind AI — Smart Alerts Component
 * Real-time alert feed with severity filtering and actionable recommendations.
 */

import React from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchAlerts } from '../../services/api';
import { POLL_INTERVAL } from '../../utils/constants';
import './SmartAlerts.css';

const SEVERITY_ICONS = {
  critical: '\u26A0\uFE0F',
  warning: '\u26A1',
  info: '\u2139\uFE0F',
};

export default function SmartAlerts() {
  const { data, loading, error } = usePolling(fetchAlerts, POLL_INTERVAL);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Loading alerts...</div>
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

  const alerts = data?.alerts || [];
  const criticalCount = alerts.filter(a => a.severity === 'critical').length;
  const warningCount = alerts.filter(a => a.severity === 'warning').length;
  const infoCount = alerts.filter(a => a.severity === 'info').length;

  return (
    <div className="alerts-page">
      {/* Summary badges */}
      <div className="alerts-summary">
        <div className="alert-count-badge all">
          Total: {alerts.length}
        </div>
        {criticalCount > 0 && (
          <div className="alert-count-badge critical-count">
            Critical: {criticalCount}
          </div>
        )}
        {warningCount > 0 && (
          <div className="alert-count-badge warning-count">
            Warning: {warningCount}
          </div>
        )}
        {infoCount > 0 && (
          <div className="alert-count-badge info-count">
            Info: {infoCount}
          </div>
        )}
      </div>

      {/* Alert List */}
      {alerts.length === 0 ? (
        <div className="alerts-empty">
          <div className="alerts-empty-icon">{'\u2705'}</div>
          <div className="alerts-empty-text">All Clear</div>
          <div className="alerts-empty-sub">No active alerts right now. Enjoy the event!</div>
        </div>
      ) : (
        <div className="alert-list stagger-children">
          {alerts.map((alert) => (
            <AlertCard key={alert.alert_id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}

function AlertCard({ alert }) {
  const timeStr = alert.timestamp
    ? new Date(alert.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    : '';

  // Clean emoji from title for display (they're already in the icon)
  const cleanTitle = alert.title.replace(/[\u{1F600}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{231A}-\u{23FF}]|[\u{FE00}-\u{FE0F}]|[\u{200D}]|[\u{20E3}]|[\u{1F900}-\u{1F9FF}]/gu, '').trim();

  return (
    <div className={`glass-card alert-card ${alert.severity}`}>
      <div className="alert-severity-icon">
        {SEVERITY_ICONS[alert.severity] || '\u2139\uFE0F'}
      </div>

      <div className="alert-content">
        <div className="alert-title">{cleanTitle}</div>
        <div className="alert-message">{alert.message}</div>
        <div className="alert-action">{alert.action}</div>
      </div>

      <div className="alert-meta">
        {alert.zone_name && (
          <span className="alert-zone-tag">{alert.zone_name}</span>
        )}
        <span className="alert-time">{timeStr}</span>
        <span className="alert-expires">Expires in {alert.expires_in_minutes}m</span>
      </div>
    </div>
  );
}
