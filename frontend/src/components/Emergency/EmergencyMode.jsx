/**
 * FlowMind AI — Emergency Evacuation Component
 * WCAG 2.1 AA: role="alert" on active banner, aria-live on stats,
 * aria-label on trigger/cancel buttons, progressbar on gate bars.
 */

import React, { useState, useCallback } from 'react';
import {
  triggerEvacuation,
  cancelEvacuation,
} from '../../services/api';
import './EmergencyMode.css';

export default function EmergencyMode() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTrigger = useCallback(async () => {
    if (!confirm('Are you sure you want to trigger an EMERGENCY EVACUATION?')) return;
    setLoading(true);
    try {
      const data = await triggerEvacuation();
      setPlan(data);
    } catch (err) {
      alert('Failed to trigger evacuation: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCancel = useCallback(async () => {
    try {
      await cancelEvacuation();
      setPlan(null);
    } catch { /* ignore */ }
  }, []);

  // No active plan — show trigger button
  if (!plan || !plan.active) {
    return (
      <section className="emergency-page" aria-label="Emergency evacuation controls">
        <div className="evac-trigger-section">
          <button
            className="evac-trigger-btn"
            onClick={handleTrigger}
            disabled={loading}
            aria-disabled={loading}
            aria-label={loading ? 'Calculating evacuation routes, please wait' : 'Trigger emergency evacuation'}
            aria-busy={loading}
          >
            ⚠️ {loading ? 'Calculating Routes...' : 'Trigger Emergency Evacuation'}
          </button>
          <p className="evac-trigger-desc">
            This will calculate optimal evacuation routes for every zone based on current
            crowd density, gate throughput capacity, and proximity. Use only in real emergencies
            or for simulation demos.
          </p>
        </div>
      </section>
    );
  }

  const maxPeople = Math.max(...(plan.gate_summary || []).map(g => g.assigned_people), 1);
  const triggeredTime = new Date(plan.triggered_at).toLocaleTimeString();

  return (
    <section className="emergency-page" aria-label="Active evacuation plan">
      {/* Active Banner */}
      <div
        className="glass-card evac-active-banner"
        role="alert"
        aria-live="assertive"
        aria-label={`Evacuation in progress. Plan ID: ${plan.evacuation_id}. Triggered at ${triggeredTime}`}
      >
        <div className="evac-banner-left">
          <span className="evac-banner-icon" aria-hidden="true">🚨</span>
          <div className="evac-banner-text">
            <h2>EVACUATION IN PROGRESS</h2>
            <span>
              Plan ID: {plan.evacuation_id} | Triggered at{' '}
              <time dateTime={plan.triggered_at}>{triggeredTime}</time>
            </span>
          </div>
        </div>
        <button
          className="evac-cancel-btn"
          onClick={handleCancel}
          aria-label="Cancel the current evacuation"
        >
          Cancel Evacuation
        </button>
      </div>

      {/* Stats */}
      <div
        className="evac-stats stagger-children"
        aria-live="polite"
        aria-label={`${plan.total_people?.toLocaleString()} people to evacuate, estimated ${plan.estimated_total_time_min} minutes total, ${plan.gate_summary?.length} active gates, throughput ${plan.total_gate_throughput} per minute`}
      >
        <article className="glass-card evac-stat" aria-hidden="true">
          <div className="stat-value">{plan.total_people?.toLocaleString()}</div>
          <div className="stat-label">People to Evacuate</div>
        </article>
        <article className="glass-card evac-stat" aria-hidden="true">
          <div className="stat-value">{plan.estimated_total_time_min}m</div>
          <div className="stat-label">Est. Total Time</div>
        </article>
        <article className="glass-card evac-stat" aria-hidden="true">
          <div className="stat-value">{plan.gate_summary?.length}</div>
          <div className="stat-label">Active Gates</div>
        </article>
        <article className="glass-card evac-stat" aria-hidden="true">
          <div className="stat-value">{plan.total_gate_throughput}/m</div>
          <div className="stat-label">Total Throughput</div>
        </article>
      </div>

      {/* Gate Load Summary */}
      <section aria-label="Gate load distribution">
        <h2 className="evac-gate-summary-header">Gate Load Distribution</h2>
        <div className="evac-gate-summary">
          {(plan.gate_summary || []).map((gate) => {
            const pct = Math.round((gate.assigned_people / maxPeople) * 100);
            return (
              <div
                key={gate.gate_id}
                className="evac-gate-bar"
                aria-label={`${gate.gate_name}: ${gate.assigned_people.toLocaleString()} people, estimated clear time ${gate.estimated_clear_time_min} minutes`}
              >
                <span className="evac-gate-label" aria-hidden="true">{gate.gate_name}</span>
                <div
                  className="evac-gate-bar-track"
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${gate.gate_name} load: ${pct}% of maximum`}
                >
                  <div className="evac-gate-bar-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="evac-gate-people" aria-hidden="true">
                  {gate.assigned_people.toLocaleString()} people | {gate.estimated_clear_time_min}m
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Zone Assignments */}
      <section aria-label="Zone exit assignments">
        <div className="section-header" style={{ marginBottom: '14px' }}>
          <h2 className="section-title">Zone Exit Assignments</h2>
          <span className="section-badge" aria-label={`${plan.zone_plans?.length} zones`}>
            {plan.zone_plans?.length} zones
          </span>
        </div>

        <div className="evac-zone-grid stagger-children">
          {(plan.zone_plans || []).map((zone) => (
            <article
              key={zone.zone_id}
              className="glass-card evac-zone-card"
              tabIndex={0}
              aria-label={`${zone.zone_name}: ${zone.current_count.toLocaleString()} people, exit via ${zone.assigned_gate_name}, estimated ${zone.estimated_evac_minutes} minutes`}
            >
              <div className="evac-zone-info">
                <h3>{zone.zone_name}</h3>
                <span aria-hidden="true">{zone.current_count.toLocaleString()} people</span>
              </div>
              <div className="evac-zone-gate" aria-hidden="true">
                <div className="evac-gate-name">➔ {zone.assigned_gate_name}</div>
                <div className="evac-gate-time">{zone.estimated_evac_minutes}m est.</div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* General Instructions */}
      <section aria-label="General evacuation instructions">
        <div className="glass-card evac-instructions">
          <h2>General Instructions</h2>
          <ol>
            {(plan.general_instructions || []).map((instr, i) => (
              <li key={i}>{instr}</li>
            ))}
          </ol>
        </div>
      </section>
    </section>
  );
}
