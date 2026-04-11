/**
 * FlowMind AI — Sidebar Component
 * WCAG 2.1 AA: role="navigation", keyboard arrow-key nav, aria-current, aria-label on overlay.
 */

import React, { useRef } from 'react';

const NAV_ITEMS = [
  { id: 'dashboard',  icon: '⌂',   label: 'Dashboard'    },
  { id: 'heatmap',    icon: '🗺️',  label: 'Crowd Heatmap' },
  { id: 'wait-times', icon: '⏱️',  label: 'Wait Times'   },
  { id: 'alerts',     icon: '🔔',  label: 'Smart Alerts'  },
  { id: 'chat',       icon: '🤖',  label: 'AI Assistant'  },
  { id: 'emergency',  icon: '🚨',  label: 'Emergency'     },
];

export default function Sidebar({ activeTab, onTabChange, isOpen, onClose }) {
  const navRef = useRef(null);

  /** Arrow-key navigation between nav items */
  const handleKeyDown = (e, index) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = (index + 1) % NAV_ITEMS.length;
      navRef.current?.children[next]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const prev = (index - 1 + NAV_ITEMS.length) % NAV_ITEMS.length;
      navRef.current?.children[prev]?.focus();
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onTabChange(NAV_ITEMS[index].id);
      onClose();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`sidebar ${isOpen ? 'open' : ''}`}
        aria-label="Main navigation"
      >
        {/* Brand */}
        <div className="sidebar-brand" aria-hidden="true">
          <div className="sidebar-logo">F</div>
          <div className="sidebar-brand-text">
            <span role="heading" aria-level="2">FlowMind AI</span>
            <span>Stadium Intelligence</span>
          </div>
        </div>

        {/* Navigation */}
        <nav aria-label="Site sections">
          <span className="sidebar-nav-label" id="nav-label">Navigation</span>
          <ul
            ref={navRef}
            className="sidebar-nav"
            role="list"
            aria-labelledby="nav-label"
          >
            {NAV_ITEMS.map((item, index) => {
              const isActive = activeTab === item.id;
              return (
                <li key={item.id} role="listitem">
                  <button
                    className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => { onTabChange(item.id); onClose(); }}
                    onKeyDown={(e) => handleKeyDown(e, index)}
                    aria-current={isActive ? 'page' : undefined}
                    aria-label={item.label}
                    tabIndex={0}
                  >
                    <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-status" role="status" aria-live="polite" aria-label="System status: online">
            <span className="status-dot live" aria-hidden="true" />
            System Online
          </div>
        </div>
      </aside>
    </>
  );
}
