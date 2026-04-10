/**
 * FlowMind AI — Header Component
 */

import React, { useState, useEffect } from 'react';

export default function Header({ title, onMenuClick, onRefresh }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="header">
      <div className="header-left">
        <button className="mobile-menu-btn" onClick={onMenuClick}>
          &#9776;
        </button>
        <div>
          <div className="header-title">{title}</div>
          <div className="header-subtitle">
            {time.toLocaleTimeString('en-US', { hour12: true })}
            {' \u2022 '}
            MetaStadium Arena
          </div>
        </div>
      </div>
      <div className="header-right">
        <div className="header-badge">
          <span className="status-dot live" />
          Live
        </div>
        <button className="header-refresh-btn" onClick={onRefresh}>
          &#x21BB; Refresh
        </button>
      </div>
    </header>
  );
}
