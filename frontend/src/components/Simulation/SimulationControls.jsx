/**
 * FlowMind AI — Simulation Controls Component
 * Play/pause/speed controls to fast-forward through a full match event.
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
  { value: 5, label: '5x' },
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
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 1000); // Poll every second for smooth updates
    return () => clearInterval(interval);
  }, [refresh]);

  const handleStart = async () => {
    try {
      const data = await startSimulation(speed);
      setStatus(data);
    } catch {
      // ignore
    }
  };

  const handleStop = async () => {
    try {
      const data = await stopSimulation();
      setStatus(data);
    } catch {
      // ignore
    }
  };

  const handleSpeedChange = async (newSpeed) => {
    setSpeed(newSpeed);
    if (status?.running) {
      try {
        const data = await setSimulationSpeed(newSpeed);
        setStatus(data);
      } catch {
        // ignore
      }
    }
  };

  if (!status) return null;

  const isRunning = status.running;
  const isCompleted = status.phase === 'completed';
  const badgeClass = isRunning ? 'running' : isCompleted ? 'completed' : 'idle';
  const badgeText = isRunning ? 'LIVE' : isCompleted ? 'COMPLETED' : 'STANDBY';

  return (
    <div className="glass-card sim-panel">
      {/* Header */}
      <div className="sim-header">
        <div className="sim-title">
          <h3>{'\uD83C\uDFAC'} Event Simulation</h3>
          <span className={`sim-live-badge ${badgeClass}`}>{badgeText}</span>
        </div>
        <div className="sim-controls">
          <select
            className="sim-speed-select"
            value={speed}
            onChange={(e) => handleSpeedChange(Number(e.target.value))}
          >
            {SPEED_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {!isRunning ? (
            <button className="sim-btn play" onClick={handleStart}>
              {'\u25B6'} Play Event
            </button>
          ) : (
            <button className="sim-btn stop" onClick={handleStop}>
              {'\u25A0'} Stop
            </button>
          )}
        </div>
      </div>

      {/* Timeline Progress */}
      <div className="sim-timeline">
        <div className="sim-progress-bar">
          <div
            className="sim-progress-fill"
            style={{ width: `${status.progress_pct || 0}%` }}
          />
        </div>
        <div className="sim-phases">
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
      <div className="sim-info">
        <div className="sim-info-item">
          Match Minute: <span className="sim-minute">{status.event_minute}'{' '}</span>
          / {status.total_minutes}'
        </div>
        <span className="sim-phase-name">{status.phase_label}</span>
        <span className="sim-description">{status.phase_description}</span>
        {isRunning && (
          <div className="sim-info-item">
            Speed: <strong>{status.speed}x</strong>
          </div>
        )}
      </div>
    </div>
  );
}
