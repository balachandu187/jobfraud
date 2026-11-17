import React from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  AlertOctagon, 
  Layers, 
  ArrowUpRight, 
  Radar, 
  Clock, 
  Sparkles,
  ChevronRight,
  TrendingUp,
  FileText
} from 'lucide-react';

export default function Dashboard({ stats, recentScans, onSelectScan, onStartScan }) {
  const total = stats?.total_scans || 0;
  const safeCount = stats?.low_risk_count || 0;
  const medCount = stats?.medium_risk_count || 0;
  const highCount = stats?.high_risk_count || 0;
  const avgScore = stats?.average_risk_score || 0;

  const safePct = total > 0 ? Math.round((safeCount / total) * 100) : 0;
  const medPct = total > 0 ? Math.round((medCount / total) * 100) : 0;
  const highPct = total > 0 ? Math.round((highCount / total) * 100) : 0;

  // Donut SVG math
  const size = 180;
  const stroke = 22;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  const safeOffset = 0;
  const safeDash = (safePct / 100) * circumference;
  
  const medOffset = -safeDash;
  const medDash = (medPct / 100) * circumference;

  const highOffset = -(safeDash + medDash);
  const highDash = (highPct / 100) * circumference;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Welcome & KPI Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-2 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            Recruitment Threat Intelligence
          </div>
          <h2 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
            Security Telemetry Dashboard
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Aggregated audit telemetry, scam probability metrics, and real-time detection intelligence.
          </p>
        </div>

        <button
          onClick={onStartScan}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-blue-500/20 border border-blue-400/30 transition-all duration-200 hover:shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98] self-start md:self-auto cursor-pointer"
        >
          <Radar className="w-4 h-4" />
          <span>Launch Job Scanner</span>
        </button>
      </div>

      {/* KPI Cards Row (4 Metric Cards with Glassmorphism) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Scanned */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider font-mono">Total Advertisements</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-white font-mono">{total}</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-white/[0.06]">
              All Records
            </span>
          </div>
          <div className="mt-3 text-xs text-slate-500 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
            <span>Avg Risk Score: <strong className="text-slate-300 font-mono">{avgScore}/100</strong></span>
          </div>
        </div>

        {/* Low Risk / Clean */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider font-mono text-emerald-400">Safe / Genuine</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-emerald-400 font-mono">{safeCount}</span>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-mono">
              {safePct}%
            </span>
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Corporate credential verified
          </div>
        </div>

        {/* Medium Risk / Suspicious */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider font-mono text-amber-400">Suspicious Flagged</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-amber-400 font-mono">{medCount}</span>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono">
              {medPct}%
            </span>
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Heuristic anomalies detected
          </div>
        </div>

        {/* High Risk / Scam Blocked */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider font-mono text-red-400">High-Risk Fraud</span>
            <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <AlertOctagon className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-red-400 font-mono">{highCount}</span>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-red-500/15 text-red-300 border border-red-500/30 font-mono">
              {highPct}%
            </span>
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Advance-fee & theft indicators
          </div>
        </div>
      </div>

      {/* Middle Row: Distribution Donut & Threat Intelligence Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Risk Donut */}
        <div className="glass-panel p-6 rounded-2xl border border-white/[0.08] lg:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>Risk Distribution</span>
              </h3>
              <span className="text-xs text-slate-500 font-mono">Ratio</span>
            </div>

            {total === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-slate-500 text-sm">
                <Radar className="w-8 h-8 mb-2 opacity-40 text-blue-400" />
                <span>No scans logged yet</span>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center my-4">
                <div className="relative">
                  <svg width={size} height={size} className="transform -rotate-90">
                    <circle
                      cx={size / 2}
                      cy={size / 2}
                      r={radius}
                      fill="none"
                      stroke="rgba(255,255,255,0.05)"
                      strokeWidth={stroke}
                    />
                    {safeCount > 0 && (
                      <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="#10B981"
                        strokeWidth={stroke}
                        strokeDasharray={`${safeDash} ${circumference}`}
                        strokeDashoffset={safeOffset}
                        strokeLinecap="round"
                        className="transition-all duration-1000"
                      />
                    )}
                    {medCount > 0 && (
                      <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="#F59E0B"
                        strokeWidth={stroke}
                        strokeDasharray={`${medDash} ${circumference}`}
                        strokeDashoffset={medOffset}
                        strokeLinecap="round"
                        className="transition-all duration-1000"
                      />
                    )}
                    {highCount > 0 && (
                      <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="#EF4444"
                        strokeWidth={stroke}
                        strokeDasharray={`${highDash} ${circumference}`}
                        strokeDashoffset={highOffset}
                        strokeLinecap="round"
                        className="transition-all duration-1000"
                      />
                    )}
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span className="text-2xl font-black text-white font-mono">{total}</span>
                    <span className="text-[10px] text-slate-400 uppercase tracking-widest font-mono">Scans</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Donut Legend */}
          <div className="space-y-2 pt-4 border-t border-white/[0.06]">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
                Low Risk (Genuine)
              </span>
              <span className="font-mono text-slate-400">{safeCount} ({safePct}%)</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
                Medium Risk (Suspicious)
              </span>
              <span className="font-mono text-slate-400">{medCount} ({medPct}%)</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
                High Risk (Scam)
              </span>
              <span className="font-mono text-slate-400">{highCount} ({highPct}%)</span>
            </div>
          </div>
        </div>

        {/* Dual-Engine Core Capabilities Box */}
        <div className="glass-panel p-6 rounded-2xl border border-white/[0.08] lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  Dual-Engine Detection Heuristics
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  How JobShield AI inspects postings in real time
                </p>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                v2.0 Architecture
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 my-4">
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-400 font-mono mb-1">
                  <span>01. TF-IDF & Logistic Regression</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Extracts 10,000+ n-gram vocabulary features to calculate statistical scam probability against benchmark dataset vectors.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-400 font-mono mb-1">
                  <span>02. 8 Security Rule Heuristics</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Audits upfront payment fees, identity theft attempts, personal webmail, high-pressure urgency, and money mule schemes.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 font-mono mb-1">
                  <span>03. Critical Safety Floor</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Enforces an immediate 75+ High Risk minimum whenever critical extortion or credential theft triggers, protecting applicants.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-400 font-mono mb-1">
                  <span>04. Local AI Mentorship</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Optionally synthesizes plain-language cybersecurity explanations using locally-hosted Ollama LLMs with 100% private offline inference.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs">
            <span className="text-slate-400">Ready to audit an unverified recruitment ad?</span>
            <button
              onClick={onStartScan}
              className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 font-semibold cursor-pointer group"
            >
              <span>Scan Now</span>
              <ChevronRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Scans Quick Table */}
      <div className="glass-panel p-6 rounded-2xl border border-white/[0.08]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              Recent Scan Activity
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Chronological log of analyzed advertisements stored in SQLite
            </p>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            {recentScans?.length || 0} entries
          </span>
        </div>

        {!recentScans || recentScans.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm rounded-xl border border-dashed border-white/[0.06]">
            No scan logs yet. Run your first scan from the workspace!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-500 font-mono text-[11px] uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Timestamp</th>
                  <th className="pb-3 font-semibold">Job Title</th>
                  <th className="pb-3 font-semibold">Company</th>
                  <th className="pb-3 font-semibold">Risk Classification</th>
                  <th className="pb-3 font-semibold">Risk Score</th>
                  <th className="pb-3 font-semibold">Warnings</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {recentScans.slice(0, 6).map((scan) => {
                  const isLow = scan.risk_level === 'Low Risk';
                  const isMed = scan.risk_level === 'Medium Risk';
                  const badgeColor = isLow 
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' 
                    : isMed 
                    ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' 
                    : 'bg-red-500/15 text-red-400 border-red-500/30';
                  
                  return (
                    <tr key={scan.id} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="py-3.5 text-xs text-slate-400 font-mono">
                        {scan.timestamp}
                      </td>
                      <td className="py-3.5 font-semibold text-white">
                        {scan.job_title || 'Unspecified Title'}
                      </td>
                      <td className="py-3.5 text-slate-300 text-xs">
                        {scan.company_name || 'Not Disclosed'}
                      </td>
                      <td className="py-3.5">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeColor}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${isLow ? 'bg-emerald-400' : isMed ? 'bg-amber-400' : 'bg-red-400'}`} />
                          {scan.risk_level}
                        </span>
                      </td>
                      <td className="py-3.5 font-mono font-bold text-slate-200">
                        {scan.risk_score} <span className="text-[11px] text-slate-500">/100</span>
                      </td>
                      <td className="py-3.5 font-mono text-xs text-slate-400">
                        {scan.warning_count || 0} flag(s)
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          onClick={() => onSelectScan(scan)}
                          className="px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-blue-600/20 text-slate-300 hover:text-blue-400 border border-white/[0.08] hover:border-blue-500/30 text-xs font-medium transition-all cursor-pointer"
                        >
                          View Report
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
