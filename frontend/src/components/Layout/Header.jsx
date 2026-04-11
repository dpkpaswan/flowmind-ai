/**
 * FlowMind AI — Header Component
 * WCAG 2.1 AA: semantic header, aria-labels on buttons, aria-live clock.
 */

import React, { useState, useEffect } from 'react';

export default function Header({ title, onMenuClick, onRefresh }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const timeStr = time.toLocaleTimeString('en-US', { hour12: true });

  return (
    <header className="header" role="banner">
      <div className="header-left">
        <button
          className="mobile-menu-btn"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
          aria-haspopup="true"
          aria-expanded={false}
        >
          &#9776;
        </button>
        <div>
          <h1 className="header-title">{title}</h1>
          <div className="header-subtitle" aria-live="off">
            <time dateTime={time.toISOString()} aria-label={`Current time: ${timeStr}`}>
              {timeStr}
            </time>
            {' \u2022 '}
            MetaStadium Arena
          </div>
        </div>
      </div>

      <div className="header-right">
        <div
          className="header-badge"
          role="status"
          aria-live="polite"
          aria-label="System status: Live"
        >
          <span className="status-dot live" aria-hidden="true" />
          Live
        </div>
        <button
          className="header-refresh-btn"
          onClick={onRefresh}
          aria-label="Refresh all dashboard data"
        >
          &#x21BB; Refresh
        </button>
      </div>
    </header>
  );
}
