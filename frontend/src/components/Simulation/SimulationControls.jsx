/**
 * FlowMind AI — Simulation Controls Component
 * WCAG 2.1 AA: aria-live on status badge, aria-label on buttons/select,
 * progressbar role on timeline, aria-live on match minute.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchSimulationStatus,
  startSimulation,
  stopSimulation,
  setSimulationSpeed,
} from '../../services/api';
import './SimulationControls.css';

const SPEED_OPTIONS = [
  { value: 5,  label: '5x' },
  { value: 10, label: '10x (Demo)' },
  { value: 20, label: '20x (Fast)' },
  { value: 30, label: '30x' },
  { value: 60, label: '60x (Ultra)' },
];

export default function SimulationControls() {
  const [status, setStatus] = useState(null);
  const [speed, setSpeed] = useState(10);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchSimulationStatus();
      setStatus(data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 1000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleStart = async () => {
    try { setStatus(await startSimulation(speed)); } catch { /* ignore */ }
  };

  const handleStop = async () => {
    try { setStatus(await stopSimulation()); } catch { /* ignore */ }
  };

  const handleSpeedChange = async (newSpeed) => {
    setSpeed(newSpeed);
    if (status?.running) {
      try { setStatus(await setSimulationSpeed(newSpeed)); } catch { /* ignore */ }
    }
  };

  if (!status) return null;

  const isRunning = status.running;
  const isCompleted = status.phase === 'completed';
  const badgeClass = isRunning ? 'running' : isCompleted ? 'completed' : 'idle';
  const badgeText  = isRunning ? 'LIVE'    : isCompleted ? 'COMPLETED' : 'STANDBY';
  const progressPct = status.progress_pct || 0;

  return (
    <section className="glass-card sim-panel" aria-label="Event simulation controls">
      {/* Header */}
      <div className="sim-header">
        <div className="sim-title">
          <h2>🎬 Event Simulation</h2>
          <span
            className={`sim-live-badge ${badgeClass}`}
            role="status"
            aria-live="polite"
            aria-label={`Simulation status: ${badgeText}`}
          >
            {badgeText}
          </span>
        </div>

        <div className="sim-controls" role="group" aria-label="Simulation speed and playback">
          <label htmlFor="sim-speed" className="visually-hidden">Simulation speed</label>
          <select
            id="sim-speed"
            className="sim-speed-select"
            value={speed}
            onChange={(e) => handleSpeedChange(Number(e.target.value))}
            aria-label={`Simulation speed: currently ${speed}x`}
          >
            {SPEED_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {!isRunning ? (
            <button
              className="sim-btn play"
              onClick={handleStart}
              aria-label="Start event simulation"
            >
              ▶ Play Event
            </button>
          ) : (
            <button
              className="sim-btn stop"
              onClick={handleStop}
              aria-label="Stop event simulation"
            >
              ■ Stop
            </button>
          )}
        </div>
      </div>

      {/* Timeline Progress */}
      <div className="sim-timeline">
        <div
          className="sim-progress-bar"
          role="progressbar"
          aria-valuenow={Math.round(progressPct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Event progress: ${Math.round(progressPct)}%`}
        >
          <div
            className="sim-progress-fill"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        <div className="sim-phases" aria-hidden="true">
          {(status.phases || []).map((phase) => (
            <div
              key={phase.phase}
              className={`sim-phase-marker ${status.phase === phase.phase ? 'active' : ''}`}
            >
              <span className="phase-label">{phase.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Info Row */}
      <div
        className="sim-info"
        aria-live="polite"
        aria-atomic="true"
        aria-label={`Match minute ${status.event_minute} of ${status.total_minutes}. Phase: ${status.phase_label}. ${isRunning ? `Speed: ${status.speed}x` : ''}`}
      >
        <div className="sim-info-item" aria-hidden="true">
          Match Minute:
          <span className="sim-minute">{status.event_minute}'{' '}</span>
          / {status.total_minutes}'
        </div>
        <span className="sim-phase-name" aria-hidden="true">{status.phase_label}</span>
        <span className="sim-description" aria-hidden="true">{status.phase_description}</span>
        {isRunning && (
          <div className="sim-info-item" aria-hidden="true">
            Speed: <strong>{status.speed}x</strong>
          </div>
        )}
      </div>
    </section>
  );
}
