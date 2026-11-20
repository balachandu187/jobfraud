import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import ScannerWorkspace from './components/ScannerWorkspace';
import ScanHistory from './components/ScanHistory';
import Architecture from './components/Architecture';
import LoginGate from './components/LoginGate';
import { ShieldAlert, RefreshCw, AlertCircle } from 'lucide-react';

export default function App({ googleClientId = '' }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [systemStatus, setSystemStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [currentScan, setCurrentScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);
  const [session, setSession] = useState(() => {
    try {
      const saved = localStorage.getItem('jobshield_session');
      return saved ? JSON.parse(saved) : null;
    } catch (error) {
      console.warn('Discarding invalid saved session:', error);
      return null;
    }
  });
  const [checkingSession, setCheckingSession] = useState(() => {
    try {
      const saved = localStorage.getItem('jobshield_session');
      return saved ? Boolean(JSON.parse(saved)) : false;
    } catch {
      return false;
    }
  });

  // Fetch telemetry and stats from FastAPI
  const fetchAllData = async () => {
    try {
      setBackendError(false);
      const [statusRes, statsRes, histRes] = await Promise.all([
        fetch('/api/status').catch(() => null),
        fetch('/api/stats').catch(() => null),
        fetch('/api/history').catch(() => null),
      ]);

      if (statusRes && statusRes.ok) {
        const sData = await statusRes.json();
        setSystemStatus(sData);
      } else {
        setBackendError(true);
      }

      if (statsRes && statsRes.ok) {
        const stData = await statsRes.json();
        setStats(stData);
      }

      if (histRes && histRes.ok) {
        const hData = await histRes.json();
        setHistory(hData);
      }
    } catch (err) {
      console.error('Data fetch error:', err);
      setBackendError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!session) {
      try {
        localStorage.removeItem('jobshield_session');
      } catch (error) {
        console.warn('Unable to remove invalid saved session:', error);
      }
      return;
    }

    fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${session.token}` },
    }).then(async (response) => {
      if (!response.ok) throw new Error('Expired session');
      fetchAllData();
    }).catch(() => {
      localStorage.removeItem('jobshield_session');
      setSession(null);
    }).finally(() => setCheckingSession(false));
  }, []);

  const handleScanComplete = (scanResult) => {
    setCurrentScan(scanResult);
    fetchAllData(); // Refresh history and stats after a scan
  };

  const handleSelectHistoricalScan = (scan) => {
    // Transform historical record to currentScan shape
    const formattedScan = {
      scan_id: scan.id,
      job_title: scan.job_title,
      company_name: scan.company_name,
      job_description: scan.job_text,
      ml_result: {
        prediction_label: scan.prediction,
        fraud_score_pct: Math.round(scan.risk_score),
        genuine_probability: Math.max(0, (100 - scan.risk_score) / 100)
      },
      rule_result: {
        warnings: scan.warnings || [],
        warning_count: scan.warning_count || 0,
        rule_score: scan.risk_score
      },
      risk_result: {
        risk_score: scan.risk_score,
        risk_level: scan.risk_level,
        verdict: scan.prediction,
        theme_color: scan.risk_level === 'Low Risk' ? '#10B981' : scan.risk_level === 'Medium Risk' ? '#F59E0B' : '#EF4444',
        warnings: scan.warnings || [],
        warning_count: scan.warning_count || 0,
        disclaimer: "Historical audit record retrieved from SQLite database."
      },
      safety_tips: scan.risk_level === 'Low Risk' 
        ? ["Verify employer identity on verified company domain."] 
        : ["Never wire funds, pay deposits, or share OTPs for employment offers."],
      ai_explanation: null
    };

    setCurrentScan(formattedScan);
    setActiveTab('scanner');
  };

  const handleAuthenticated = (authData) => {
    const nextSession = { token: authData.token, user: authData.user };
    localStorage.setItem('jobshield_session', JSON.stringify(nextSession));
    setSession(nextSession);
    setLoading(false);
    fetchAllData();
  };

  const handleSignOut = () => {
    try {
      localStorage.removeItem('jobshield_session');
    } catch (error) {
      console.warn('Unable to remove saved session during sign out:', error);
    }

    setSession(null);
    setCurrentScan(null);
    setHistory([]);
    setStats(null);
    setSystemStatus(null);
    setActiveTab('dashboard');
  };

  if (checkingSession) {
    return <div className="min-h-screen bg-[#0B0F19] text-slate-400 flex items-center justify-center">Verifying session...</div>;
  }

  if (!session) {
    return (
      <LoginGate
        googleClientId={googleClientId}
        onAuthenticated={handleAuthenticated}
      />
    );
  }

  return (
    <div className="flex min-h-screen bg-[#0B0F19] text-[#F8FAFC]">
      {/* Sleek Enterprise Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        user={session.user}
        onSignOut={handleSignOut}
      />

      {/* Main Content Viewport */}
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-y-auto">
        {/* Top Floating Control Bar */}
        <header className="sticky top-0 z-30 bg-[#0B0F19]/80 backdrop-blur-md border-b border-white/[0.06] px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Location:
            </span>
            <span className="text-xs font-mono text-blue-400 font-semibold">
              // {activeTab.toUpperCase()}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {backendError && (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-mono">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>FastAPI Disconnected</span>
              </div>
            )}

            <button
              onClick={fetchAllData}
              title="Refresh telemetry"
              className="p-2 rounded-xl bg-slate-900 border border-white/[0.06] text-slate-400 hover:text-white hover:border-blue-500/30 transition-all cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </header>

        {/* Page Content Container */}
        <div className="p-8 max-w-7xl w-full mx-auto pb-16">
          {activeTab === 'dashboard' && (
            <Dashboard
              stats={stats}
              recentScans={history}
              onSelectScan={handleSelectHistoricalScan}
              onStartScan={() => setActiveTab('scanner')}
            />
          )}

          {activeTab === 'scanner' && (
            <ScannerWorkspace
              currentScan={currentScan}
              onScanComplete={handleScanComplete}
              systemStatus={systemStatus}
            />
          )}

          {activeTab === 'history' && (
            <ScanHistory
              scans={history}
              onRefresh={fetchAllData}
              onSelectScan={handleSelectHistoricalScan}
            />
          )}

          {activeTab === 'about' && (
            <Architecture />
          )}
        </div>
      </main>
    </div>
  );
}
