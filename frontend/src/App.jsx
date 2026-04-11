/**
 * FlowMind AI — Main Application
 * Routes between dashboard, heatmap, wait times, alerts, chat, simulation, and emergency views.
 */

import React, { useState, useCallback } from 'react';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import Dashboard from './components/Dashboard/Dashboard';
import CrowdHeatmap from './components/Heatmap/CrowdHeatmap';
import WaitTimes from './components/WaitTimes/WaitTimes';
import SmartAlerts from './components/Alerts/SmartAlerts';
import AIChat from './components/Chat/AIChat';
import EmergencyMode from './components/Emergency/EmergencyMode';
import SimulationControls from './components/Simulation/SimulationControls';
import './components/Layout/Layout.css';
import './App.css';

const TAB_TITLES = {
  dashboard: 'Dashboard',
  heatmap: 'Crowd Heatmap',
  'wait-times': 'Wait Times',
  alerts: 'Smart Alerts',
  chat: 'AI Assistant',
  emergency: 'Emergency Evacuation',
};

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    setRefreshKey(k => k + 1);
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':   return <Dashboard key={refreshKey} />;
      case 'heatmap':     return <CrowdHeatmap key={refreshKey} />;
      case 'wait-times':  return <WaitTimes key={refreshKey} />;
      case 'alerts':      return <SmartAlerts key={refreshKey} />;
      case 'chat':        return <AIChat />;
      case 'emergency':   return <EmergencyMode key={refreshKey} />;
      default:            return <Dashboard key={refreshKey} />;
    }
  };

  return (
    <div className="layout">
      {/* Skip navigation link — visible only on keyboard focus */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main-content" id="main-content" tabIndex={-1}>
        <Header
          title={TAB_TITLES[activeTab]}
          onMenuClick={() => setSidebarOpen(true)}
          onRefresh={handleRefresh}
        />
        <div className="page-content" role="region" aria-label={TAB_TITLES[activeTab]}>
          {/* Simulation Controls — visible on all tabs */}
          <SimulationControls />
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
