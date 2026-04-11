/**
 * FlowMind AI — Smart Alerts Component
 * WCAG 2.1 AA: role="feed" for alert list, aria-live for dynamic updates,
 * aria-label on severity icons, semantic article elements.
 */

import React from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchAlerts } from '../../services/api';
import { POLL_INTERVAL } from '../../utils/constants';
import './SmartAlerts.css';

const SEVERITY_ICONS = {
  critical: '⚠️',
  warning: '⚡',
  info: 'ℹ️',
};

const SEVERITY_LABELS = {
  critical: 'Critical',
  warning: 'Warning',
  info: 'Information',
};

export default function SmartAlerts() {
  const { data, loading, error } = usePolling(fetchAlerts, POLL_INTERVAL);

  if (loading) {
    return (
      <div className="loading-container" role="status" aria-label="Loading alerts">
        <div className="loading-spinner" aria-hidden="true" />
        <div className="loading-text">Loading alerts...</div>
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

  const alerts = data?.alerts || [];
  const criticalCount = alerts.filter(a => a.severity === 'critical').length;
  const warningCount = alerts.filter(a => a.severity === 'warning').length;
  const infoCount = alerts.filter(a => a.severity === 'info').length;

  return (
    <section className="alerts-page" aria-label="Smart Alerts">
      {/* Summary badges */}
      <div
        className="alerts-summary"
        role="status"
        aria-live="polite"
        aria-label={`${alerts.length} total alerts: ${criticalCount} critical, ${warningCount} warnings, ${infoCount} informational`}
      >
        <div className="alert-count-badge all">Total: {alerts.length}</div>
        {criticalCount > 0 && (
          <div className="alert-count-badge critical-count">Critical: {criticalCount}</div>
        )}
        {warningCount > 0 && (
          <div className="alert-count-badge warning-count">Warning: {warningCount}</div>
        )}
        {infoCount > 0 && (
          <div className="alert-count-badge info-count">Info: {infoCount}</div>
        )}
      </div>

      {/* Alert List */}
      {alerts.length === 0 ? (
        <div className="alerts-empty" role="status" aria-live="polite">
          <div className="alerts-empty-icon" aria-hidden="true">✅</div>
          <div className="alerts-empty-text">All Clear</div>
          <div className="alerts-empty-sub">No active alerts right now. Enjoy the event!</div>
        </div>
      ) : (
        <div
          className="alert-list stagger-children"
          role="feed"
          aria-label="Live alerts feed"
          aria-live="polite"
          aria-atomic="false"
          aria-relevant="additions removals"
        >
          {alerts.map((alert) => (
            <AlertCard key={alert.alert_id} alert={alert} />
          ))}
        </div>
      )}
    </section>
  );
}

function AlertCard({ alert }) {
  const timeStr = alert.timestamp
    ? new Date(alert.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    : '';

  const cleanTitle = alert.title.replace(/[\u{1F600}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{231A}-\u{23FF}]|[\u{FE00}-\u{FE0F}]|[\u{200D}]|[\u{20E3}]|[\u{1F900}-\u{1F9FF}]/gu, '').trim();

  const severityLabel = SEVERITY_LABELS[alert.severity] || alert.severity;

  return (
    <article
      className={`glass-card alert-card ${alert.severity}`}
      tabIndex={0}
      aria-label={`${severityLabel} alert: ${cleanTitle}. ${alert.message}. Action: ${alert.action}`}
    >
      <div className="alert-severity-icon" aria-label={`Severity: ${severityLabel}`} role="img">
        {SEVERITY_ICONS[alert.severity] || 'ℹ️'}
      </div>

      <div className="alert-content">
        <div className="alert-title">{cleanTitle}</div>
        <div className="alert-message">{alert.message}</div>
        <div className="alert-action">{alert.action}</div>
      </div>

      <div className="alert-meta" aria-hidden="true">
        {alert.zone_name && (
          <span className="alert-zone-tag">{alert.zone_name}</span>
        )}
        <time className="alert-time" dateTime={alert.timestamp}>{timeStr}</time>
        <span className="alert-expires">Expires in {alert.expires_in_minutes}m</span>
      </div>
    </article>
  );
}
