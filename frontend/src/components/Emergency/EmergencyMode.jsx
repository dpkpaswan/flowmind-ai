/**
 * FlowMind AI — Emergency Evacuation Component
 * One-click emergency trigger with AI-calculated exit routes per zone.
 */

import React, { useState, useCallback } from 'react';
import {
  triggerEvacuation,
  cancelEvacuation,
  fetchEvacuationStatus,
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
    } catch {
      // ignore
    }
  }, []);

  // No active plan — show trigger button
  if (!plan || !plan.active) {
    return (
      <div className="emergency-page">
        <div className="evac-trigger-section">
          <button
            className="evac-trigger-btn"
            onClick={handleTrigger}
            disabled={loading}
          >
            {'\u26A0\uFE0F'} {loading ? 'Calculating Routes...' : 'Trigger Emergency Evacuation'}
          </button>
          <p className="evac-trigger-desc">
            This will calculate optimal evacuation routes for every zone based on current
            crowd density, gate throughput capacity, and proximity. Use only in real emergencies
            or for simulation demos.
          </p>
        </div>
      </div>
    );
  }

  // Active plan — show full evacuation dashboard
  const maxPeople = Math.max(...(plan.gate_summary || []).map(g => g.assigned_people), 1);

  return (
    <div className="emergency-page">
      {/* Active Banner */}
      <div className="glass-card evac-active-banner">
        <div className="evac-banner-left">
          <span className="evac-banner-icon">{'\uD83D\uDEA8'}</span>
          <div className="evac-banner-text">
            <h3>EVACUATION IN PROGRESS</h3>
            <span>Plan ID: {plan.evacuation_id} | Triggered at {new Date(plan.triggered_at).toLocaleTimeString()}</span>
          </div>
        </div>
        <button className="evac-cancel-btn" onClick={handleCancel}>
          Cancel Evacuation
        </button>
      </div>

      {/* Stats */}
      <div className="evac-stats stagger-children">
        <div className="glass-card evac-stat">
          <div className="stat-value">{plan.total_people?.toLocaleString()}</div>
          <div className="stat-label">People to Evacuate</div>
        </div>
        <div className="glass-card evac-stat">
          <div className="stat-value">{plan.estimated_total_time_min}m</div>
          <div className="stat-label">Est. Total Time</div>
        </div>
        <div className="glass-card evac-stat">
          <div className="stat-value">{plan.gate_summary?.length}</div>
          <div className="stat-label">Active Gates</div>
        </div>
        <div className="glass-card evac-stat">
          <div className="stat-value">{plan.total_gate_throughput}/m</div>
          <div className="stat-label">Total Throughput</div>
        </div>
      </div>

      {/* Gate Load Summary */}
      <div className="evac-gate-summary">
        <h3>Gate Load Distribution</h3>
        {(plan.gate_summary || []).map((gate) => (
          <div key={gate.gate_id} className="evac-gate-bar">
            <span className="evac-gate-label">{gate.gate_name}</span>
            <div className="evac-gate-bar-track">
              <div
                className="evac-gate-bar-fill"
                style={{ width: `${(gate.assigned_people / maxPeople) * 100}%` }}
              />
            </div>
            <span className="evac-gate-people">
              {gate.assigned_people.toLocaleString()} people | {gate.estimated_clear_time_min}m
            </span>
          </div>
        ))}
      </div>

      {/* Zone Assignments */}
      <div className="section-header" style={{ marginBottom: '14px' }}>
        <div className="section-title">Zone Exit Assignments</div>
        <span className="section-badge">{plan.zone_plans?.length} zones</span>
      </div>

      <div className="evac-zone-grid stagger-children">
        {(plan.zone_plans || []).map((zone) => (
          <div key={zone.zone_id} className="glass-card evac-zone-card">
            <div className="evac-zone-info">
              <h4>{zone.zone_name}</h4>
              <span>{zone.current_count.toLocaleString()} people</span>
            </div>
            <div className="evac-zone-gate">
              <div className="evac-gate-name">
                {'\u2794'} {zone.assigned_gate_name}
              </div>
              <div className="evac-gate-time">{zone.estimated_evac_minutes}m est.</div>
            </div>
          </div>
        ))}
      </div>

      {/* General Instructions */}
      <div className="glass-card evac-instructions">
        <h3>General Instructions</h3>
        <ol>
          {(plan.general_instructions || []).map((instr, i) => (
            <li key={i}>{instr}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}
