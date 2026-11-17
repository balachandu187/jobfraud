import React, { useState } from 'react';
import { 
  Search, 
  Trash2, 
  ChevronDown, 
  ChevronUp, 
  AlertTriangle, 
  ShieldCheck, 
  AlertOctagon, 
  Clock, 
  Filter, 
  FileText,
  RotateCcw,
  Check
} from 'lucide-react';

export default function ScanHistory({ 
  scans, 
  onRefresh, 
  onSelectScan 
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [clearingAll, setClearingAll] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  // Filter scans based on search query and risk level
  const filteredScans = (scans || []).filter((scan) => {
    const matchesQuery = 
      (scan.job_title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (scan.company_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (scan.job_text || '').toLowerCase().includes(searchQuery.toLowerCase());
    
    if (!matchesQuery) return false;

    if (filterRisk === 'ALL') return true;
    if (filterRisk === 'LOW' && scan.risk_level === 'Low Risk') return true;
    if (filterRisk === 'MEDIUM' && scan.risk_level === 'Medium Risk') return true;
    if (filterRisk === 'HIGH' && scan.risk_level === 'High Risk') return true;

    return false;
  });

  const handleDeleteScan = async (scanId, e) => {
    e.stopPropagation();
    setDeletingId(scanId);
    try {
      const res = await fetch(`/api/history/${scanId}`, { method: 'DELETE' });
      if (res.ok) {
        onRefresh();
      }
    } catch (err) {
      console.error('Delete error:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    setClearingAll(true);
    try {
      const res = await fetch('/api/history', { method: 'DELETE' });
      if (res.ok) {
        onRefresh();
        setConfirmClear(false);
      }
    } catch (err) {
      console.error('Clear error:', err);
    } finally {
      setClearingAll(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-2 font-mono">
            <Clock className="w-3.5 h-3.5" />
            Audit Persistence
          </div>
          <h2 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
            Historical Scan Archives
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Searchable SQLite audit trail of all previous job advertisement credibility inspections.
          </p>
        </div>

        {/* Clear All Action */}
        {scans && scans.length > 0 && (
          <div>
            {!confirmClear ? (
              <button
                onClick={() => setConfirmClear(true)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-semibold transition-all cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All Logs</span>
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleClearAll}
                  disabled={clearingAll}
                  className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all cursor-pointer"
                >
                  {clearingAll ? 'Purging...' : 'Confirm Delete All'}
                </button>
                <button
                  onClick={() => setConfirmClear(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold transition-all cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel p-4 rounded-2xl border border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title, employer, or keyword snippet..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-blue-500 font-sans"
          />
        </div>

        {/* Risk Filter Pills */}
        <div className="flex items-center gap-1.5 self-start md:self-auto">
          {[
            { id: 'ALL', label: 'All Records' },
            { id: 'LOW', label: 'Low Risk', color: 'text-emerald-400' },
            { id: 'MEDIUM', label: 'Medium Risk', color: 'text-amber-400' },
            { id: 'HIGH', label: 'High Risk', color: 'text-red-400' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setFilterRisk(pill.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                filterRisk === pill.id
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {/* Scan Log Cards List */}
      {!filteredScans || filteredScans.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-white/[0.08] text-center text-slate-500 text-sm">
          <FileText className="w-10 h-10 mx-auto mb-3 opacity-30 text-blue-400" />
          <div className="font-semibold text-slate-300">No matching audit records found</div>
          <p className="text-xs text-slate-500 mt-1">
            Try adjusting your search criteria or filter options above.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredScans.map((scan) => {
            const isExpanded = expandedId === scan.id;
            const isLow = scan.risk_level === 'Low Risk';
            const isMed = scan.risk_level === 'Medium Risk';
            const themeColor = isLow ? '#10B981' : isMed ? '#F59E0B' : '#EF4444';

            return (
              <div
                key={scan.id}
                className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden transition-all"
              >
                {/* Header Strip */}
                <div 
                  onClick={() => setExpandedId(isExpanded ? null : scan.id)}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer hover:bg-white/[0.02]"
                >
                  <div className="flex items-center gap-3">
                    <span 
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: themeColor }}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">
                          {scan.job_title || 'Unspecified Title'}
                        </span>
                        <span className="text-xs text-slate-400">
                          @ {scan.company_name || 'Not Disclosed'}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono mt-0.5 flex items-center gap-2">
                        <span>{scan.timestamp}</span>
                        <span>•</span>
                        <span>Audit Record #{scan.id}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 self-end sm:self-auto">
                    <div className="text-right">
                      <span 
                        className="text-xs font-bold px-2 py-0.5 rounded-full font-mono uppercase"
                        style={{
                          backgroundColor: `${themeColor}15`,
                          color: themeColor,
                          border: `1px solid ${themeColor}30`
                        }}
                      >
                        {scan.risk_level}
                      </span>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        Score: <strong className="text-slate-200">{scan.risk_score}</strong>/100
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={(e) => handleDeleteScan(scan.id, e)}
                        disabled={deletingId === scan.id}
                        className="p-2 rounded-lg hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition-colors cursor-pointer"
                        title="Delete record"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <div className="text-slate-500 p-1">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-white/[0.04] bg-black/20 space-y-4 text-xs animate-fadeIn">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                        <span className="text-slate-500 font-mono text-[10px] uppercase">ML Classification</span>
                        <div className="font-bold text-slate-200 mt-0.5">{scan.prediction}</div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                        <span className="text-slate-500 font-mono text-[10px] uppercase">Composite Risk Score</span>
                        <div className="font-bold text-slate-200 mt-0.5 font-mono">{scan.risk_score} / 100</div>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                        <span className="text-slate-500 font-mono text-[10px] uppercase">Red Flags Logged</span>
                        <div className="font-bold text-slate-200 mt-0.5 font-mono">{scan.warning_count} Warnings</div>
                      </div>
                    </div>

                    {/* Job Text Preview */}
                    <div>
                      <span className="text-slate-400 font-mono text-[11px] block mb-1">
                        Original Advertisement Snippet:
                      </span>
                      <div className="p-3 rounded-xl bg-slate-950 border border-white/[0.06] text-slate-300 font-sans text-xs leading-relaxed max-h-36 overflow-y-auto">
                        {scan.job_text}
                      </div>
                    </div>

                    {/* Warnings List */}
                    {scan.warnings && scan.warnings.length > 0 && (
                      <div>
                        <span className="text-slate-400 font-mono text-[11px] block mb-1.5">
                          Logged Threat Indicators:
                        </span>
                        <div className="space-y-1.5">
                          {scan.warnings.map((w, idx) => (
                            <div key={idx} className="p-2.5 rounded-lg bg-slate-900/80 border border-white/[0.04] flex items-center justify-between">
                              <span className="font-medium text-slate-200">⚠️ {w.title}</span>
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">
                                {w.severity}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
