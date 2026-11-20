import React from 'react';
import { 
  ShieldCheck, 
  Radar, 
  History, 
  Cpu, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Activity,
  ChevronRight,
  UserRound
} from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  systemStatus,
  user
}) {
  const navItems = [
    { id: 'dashboard', label: 'Home Dashboard', icon: Activity, desc: 'Telemetry & Metrics' },
    { id: 'scanner', label: 'Job Scanner', icon: Radar, desc: 'Dual-Engine Detection', badge: 'Live' },
    { id: 'history', label: 'Scan Audit Logs', icon: History, desc: 'SQLite History' },
    { id: 'about', label: 'Pipeline Architecture', icon: Cpu, desc: 'TF-IDF & Heuristics' },
  ];

  const mlReady = systemStatus?.ml_ready ?? true;
  const ollamaOnline = systemStatus?.ollama_available ?? false;
  const displayName = user?.name || user?.full_name || user?.email?.split('@')[0] || 'JobShield Analyst';
  const displayEmail = user?.email || 'Email unavailable';
  const displayRole = user?.role || 'analyst';
  const authMethod = user?.auth_provider === 'google' ? 'Google account' : 'Email account';
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  return (
    <aside className="w-72 bg-[#0B0F19] border-r border-white/[0.08] flex flex-col justify-between shrink-0 h-screen sticky top-0 select-none">
      {/* Brand Header */}
      <div>
        <div className="p-6 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 border border-blue-400/30">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-white font-sans">
                  JobShield<span className="text-blue-500">AI</span>
                </h1>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 uppercase tracking-wider">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-tight">
                Recruitment Fraud Intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="px-4 py-6">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 px-3 mb-2 font-mono">
            Navigation
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left transition-all duration-200 group ${
                    isActive 
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10 font-semibold' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03] border border-transparent font-medium'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                    <div>
                      <div className="text-sm tracking-tight">{item.label}</div>
                      <div className="text-[11px] text-slate-500 font-normal">{item.desc}</div>
                    </div>
                  </div>
                  {item.badge ? (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">
                      {item.badge}
                    </span>
                  ) : (
                    <ChevronRight className={`w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity ${isActive ? 'opacity-100 text-blue-400' : 'text-slate-600'}`} />
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      <div>
        {/* Signed-in account details */}
        <section
          aria-label="Account profile"
          className="p-3 m-4 mb-2 rounded-xl bg-slate-900/60 border border-white/[0.06] backdrop-blur-md"
        >
          <div className="text-[10px] font-mono uppercase tracking-wider font-bold text-slate-400 mb-2">
            Signed-in Account
          </div>
          <div className="flex items-center gap-2.5 min-w-0">
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={`${displayName} profile`}
                referrerPolicy="no-referrer"
                className="w-9 h-9 rounded-full object-cover border border-white/10 shrink-0"
              />
            ) : (
              <div className="w-9 h-9 rounded-full bg-blue-500/15 border border-blue-500/25 text-blue-300 flex items-center justify-center shrink-0">
                {initials ? (
                  <span className="text-xs font-bold">{initials}</span>
                ) : (
                  <UserRound className="w-4 h-4" />
                )}
              </div>
            )}
            <div className="min-w-0">
              <div className="text-xs text-white font-semibold truncate" title={displayName}>
                {displayName}
              </div>
              <div className="text-[11px] text-slate-400 truncate" title={displayEmail}>
                {displayEmail}
              </div>
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between gap-2 text-[10px] font-mono">
            <span className="text-slate-500">{authMethod}</span>
            <span className="text-blue-300 uppercase">{displayRole}</span>
          </div>
        </section>

        {/* System Status telemetry card at bottom */}
        <div className="p-4 m-4 rounded-xl bg-slate-900/60 border border-white/[0.06] backdrop-blur-md">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-slate-400 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              System Engines
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Telemetry</span>
          </div>

          <div className="space-y-2.5">
            {/* ML Model Status */}
            <div className="flex items-center justify-between text-xs p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <div className="flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-slate-300 font-medium">ML Classifier</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[11px] font-mono text-emerald-400 font-semibold">Active</span>
              </div>
            </div>

            {/* Ollama LLM Status */}
            <div className="flex items-center justify-between text-xs p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-slate-300 font-medium">Local Ollama</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${ollamaOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className={`text-[11px] font-mono font-semibold ${ollamaOnline ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {ollamaOnline ? 'Online' : 'Fallback'}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <span>HOST: LOCALHOST</span>
            <span className="text-emerald-500 font-medium">PORT 8000</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
