/**
 * FlowMind AI — Sidebar Component
 */

import React from 'react';

const NAV_ITEMS = [
  { id: 'dashboard', icon: '\u2302', label: 'Dashboard' },
  { id: 'heatmap', icon: '\uD83D\uDDFA\uFE0F', label: 'Crowd Heatmap' },
  { id: 'wait-times', icon: '\u23F1\uFE0F', label: 'Wait Times' },
  { id: 'alerts', icon: '\uD83D\uDD14', label: 'Smart Alerts' },
  { id: 'chat', icon: '\uD83E\uDD16', label: 'AI Assistant' },
  { id: 'emergency', icon: '\uD83D\uDEA8', label: 'Emergency' },
];

export default function Sidebar({ activeTab, onTabChange, isOpen, onClose }) {
  return (
    <>
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
      />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-logo">F</div>
          <div className="sidebar-brand-text">
            <h1>FlowMind AI</h1>
            <span>Stadium Intelligence</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <span className="sidebar-nav-label">Navigation</span>
          {NAV_ITEMS.map((item) => (
            <div
              key={item.id}
              className={`sidebar-nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => {
                onTabChange(item.id);
                onClose();
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-status">
            <span className="status-dot live" />
            System Online
          </div>
        </div>
      </aside>
    </>
  );
}
