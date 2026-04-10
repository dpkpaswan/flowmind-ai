/**
 * FlowMind AI — Crowd Heatmap Component
 * Visual stadium zone map with density visualization and predictions.
 */

import React, { useState } from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchCrowdData, fetchCrowdPredictions } from '../../services/api';
import { POLL_INTERVAL, STATUS_COLORS } from '../../utils/constants';
import './CrowdHeatmap.css';

// Map zone_id to grid zone position
const ZONE_POSITION = {
  north_stand: 'north',
  south_stand: 'south',
  east_stand: 'east',
  west_stand: 'west',
};

// Extra zones shown in side panel only
const EXTRA_ZONES = ['food_court_a', 'food_court_b', 'main_gate', 'vip_lounge'];

function densityColor(density) {
  if (density >= 0.9) return STATUS_COLORS.critical;
  if (density >= 0.75) return STATUS_COLORS.high;
  if (density >= 0.4) return STATUS_COLORS.moderate;
  return STATUS_COLORS.low;
}

export default function CrowdHeatmap() {
  const { data: crowd, loading, error } = usePolling(fetchCrowdData, POLL_INTERVAL);
  const { data: predData } = usePolling(fetchCrowdPredictions, POLL_INTERVAL);
  const [selectedZone, setSelectedZone] = useState(null);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Loading heatmap data...</div>
      </div>
    );
  }

  if (error || !crowd) {
    return (
      <div className="error-container">
        <div className="error-message">{error || 'No data available'}</div>
      </div>
    );
  }

  const zones = crowd.zones || [];
  const predictions = predData?.predictions || [];

  const mainZones = zones.filter(z => ZONE_POSITION[z.zone_id]);
  const extraZones = zones.filter(z => EXTRA_ZONES.includes(z.zone_id));

  // Find prediction for selected zone
  const selectedPrediction = selectedZone
    ? predictions.find(p => p.zone_id === selectedZone)
    : null;

  return (
    <div className="heatmap-container">
      {/* Stadium Visual Map */}
      <div className="glass-card stadium-map">
        <div className="stadium-map-header">
          <div className="stadium-map-title">Stadium Density Map</div>
          <div className="stadium-map-legend">
            <div className="legend-item">
              <div className="legend-dot" style={{ background: STATUS_COLORS.low }} />
              Low
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: STATUS_COLORS.moderate }} />
              Medium
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: STATUS_COLORS.high }} />
              High
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: STATUS_COLORS.critical }} />
              Critical
            </div>
          </div>
        </div>

        <div className="stadium-visual">
          {mainZones.map((zone) => {
            const color = densityColor(zone.current_density);
            const pos = ZONE_POSITION[zone.zone_id];
            return (
              <div
                key={zone.zone_id}
                className={`zone-block ${pos}`}
                style={{
                  background: `${color}18`,
                  borderColor: `${color}40`,
                  boxShadow: `inset 0 0 30px ${color}12`,
                }}
                onClick={() => setSelectedZone(zone.zone_id)}
              >
                <span className="zone-block-name">{zone.name}</span>
                <span className="zone-block-pct" style={{ color }}>
                  {(zone.current_density * 100).toFixed(0)}%
                </span>
                <span className="zone-block-count">
                  {zone.current_count?.toLocaleString()} people
                </span>
              </div>
            );
          })}

          <div className="field-center">PLAYING FIELD</div>
        </div>
      </div>

      {/* Side Panel */}
      <div className="heatmap-side-panel">
        {/* Extra Zones */}
        <div className="glass-card facility-zones-card">
          <h3>Other Zones</h3>
          {extraZones.map((zone) => (
            <div
              key={zone.zone_id}
              className="facility-zone-item"
              style={{ cursor: 'pointer' }}
              onClick={() => setSelectedZone(zone.zone_id)}
            >
              <div className="facility-zone-info">
                <span className="facility-zone-name">{zone.name}</span>
                <span className="facility-zone-count">
                  {zone.current_count?.toLocaleString()} / {zone.capacity?.toLocaleString()}
                </span>
              </div>
              <span
                className="facility-zone-density"
                style={{ color: densityColor(zone.current_density) }}
              >
                {(zone.current_density * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>

        {/* Prediction Panel */}
        <div className="glass-card prediction-card">
          <h3>
            {selectedPrediction
              ? `${selectedPrediction.name} Forecast`
              : 'Click a zone to see forecast'}
          </h3>
          {selectedPrediction ? (
            <>
              <div className="prediction-item">
                <span className="prediction-time">Now</span>
                <div className="prediction-bar-track">
                  <div
                    className="prediction-bar-fill"
                    style={{
                      width: `${selectedPrediction.current_density * 100}%`,
                      background: densityColor(selectedPrediction.current_density),
                    }}
                  />
                </div>
                <span
                  className="prediction-value"
                  style={{ color: densityColor(selectedPrediction.current_density) }}
                >
                  {(selectedPrediction.current_density * 100).toFixed(0)}%
                </span>
              </div>
              {(selectedPrediction.predictions || []).map((pred) => (
                <div key={pred.minutes_ahead} className="prediction-item">
                  <span className="prediction-time">+{pred.minutes_ahead}m</span>
                  <div className="prediction-bar-track">
                    <div
                      className="prediction-bar-fill"
                      style={{
                        width: `${pred.predicted_density * 100}%`,
                        background: densityColor(pred.predicted_density),
                      }}
                    />
                  </div>
                  <span
                    className="prediction-value"
                    style={{ color: densityColor(pred.predicted_density) }}
                  >
                    {(pred.predicted_density * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </>
          ) : (
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '12px 0' }}>
              Select any zone on the map or from the list to view its 5/10/15 minute density prediction.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
