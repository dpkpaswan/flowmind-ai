/**
 * FlowMind AI — Google Maps Heatmap Component
 * Renders a Google Map with a HeatmapLayer overlay using
 * the Google Maps JavaScript API (loaded via index.html).
 * No additional npm packages needed.
 */

import React, { useRef, useEffect, useCallback } from 'react';

// Stadium center coordinates (Mumbai — MetaStadium Arena)
const STADIUM_CENTER = { lat: 19.0750, lng: 72.8777 };
const DEFAULT_ZOOM = 16;

// Custom dark map style to match FlowMind's aesthetic
const MAP_STYLES = [
  { elementType: 'geometry', stylers: [{ color: '#0a0e1a' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0a0e1a' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#6b7280' }] },
  { featureType: 'administrative', elementType: 'geometry', stylers: [{ color: '#1a1f36' }] },
  { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#111827' }] },
  { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#4b5563' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#1a1f36' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#111827' }] },
  { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#4b5563' }] },
  { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#111827' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0f172a' }] },
  { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#374151' }] },
];

// Heatmap gradient: transparent → green → amber → orange → red
const HEATMAP_GRADIENT = [
  'rgba(0, 0, 0, 0)',
  'rgba(16, 185, 129, 0.6)',
  'rgba(16, 185, 129, 0.8)',
  'rgba(245, 158, 11, 0.7)',
  'rgba(249, 115, 22, 0.8)',
  'rgba(239, 68, 68, 0.85)',
  'rgba(239, 68, 68, 1)',
];

export default function GoogleMap({ points = [] }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const heatmapLayer = useRef(null);

  // Initialize map once the Google script is ready
  const initMap = useCallback(() => {
    if (!window.google?.maps || !mapRef.current || mapInstance.current) return;

    mapInstance.current = new window.google.maps.Map(mapRef.current, {
      center: STADIUM_CENTER,
      zoom: DEFAULT_ZOOM,
      styles: MAP_STYLES,
      disableDefaultUI: true,
      zoomControl: true,
      fullscreenControl: true,
      gestureHandling: 'greedy',
      backgroundColor: '#0a0e1a',
    });
  }, []);

  useEffect(() => {
    if (window.google?.maps) {
      initMap();
      return;
    }
    // Poll until the async Maps script finishes loading
    let attempts = 0;
    const interval = setInterval(() => {
      attempts++;
      if (window.google?.maps) {
        clearInterval(interval);
        initMap();
      }
      if (attempts > 50) clearInterval(interval);
    }, 100);
    return () => clearInterval(interval);
  }, [initMap]);

  // Update heatmap layer whenever points change
  useEffect(() => {
    if (!mapInstance.current || !window.google?.maps?.visualization || !points.length) return;

    const heatmapData = points.map((pt) => ({
      location: new window.google.maps.LatLng(pt.lat, pt.lng),
      weight: pt.weight,
    }));

    if (heatmapLayer.current) {
      heatmapLayer.current.setData(heatmapData);
    } else {
      heatmapLayer.current = new window.google.maps.visualization.HeatmapLayer({
        data: heatmapData,
        map: mapInstance.current,
        radius: 40,
        opacity: 0.8,
        gradient: HEATMAP_GRADIENT,
      });
    }
  }, [points]);

  return (
    <div
      ref={mapRef}
      className="google-map-container"
      style={{ width: '100%', height: '100%', minHeight: '460px' }}
    />
  );
}
