import React from 'react';
import { 
  Cpu, 
  Layers, 
  ShieldCheck, 
  Database, 
  Sparkles, 
  ArrowDown, 
  ArrowRight, 
  Terminal, 
  Lock, 
  FileCheck,
  CheckCircle2,
  Workflow
} from 'lucide-react';

export default function Architecture() {
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-2 font-mono">
          <Workflow className="w-3.5 h-3.5" />
          Technical Specifications
        </div>
        <h2 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
          Dual-Engine Detection Pipeline Architecture
        </h2>
        <p className="text-slate-400 text-sm mt-1 max-w-3xl">
          JobShield AI fuses statistical Natural Language Processing with deterministic heuristic threat patterns to provide robust, explainable recruitment scam defense without external cloud dependencies.
        </p>
      </div>

      {/* Interactive Visual Architecture Flowchart */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/[0.08] relative overflow-hidden space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
          <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            End-to-End Threat Intelligence Pipeline
          </span>
          <span className="text-xs font-mono text-slate-500">Local Execution Graph</span>
        </div>

        {/* Pipeline Stage 1: Input */}
        <div className="flex flex-col items-center">
          <div className="p-4 rounded-xl bg-slate-900 border border-blue-500/30 text-center w-full max-w-md shadow-lg shadow-blue-500/5">
            <div className="text-xs font-mono font-bold text-blue-400 uppercase tracking-wider mb-1">
              [ Stage 01 ] Job Advertisement Input
            </div>
            <div className="text-xs text-slate-300">
              Raw text, salary brackets, recruiter emails, and application channels
            </div>
          </div>
          <ArrowDown className="w-5 h-5 text-blue-500 my-2 animate-bounce" />
        </div>

        {/* Pipeline Stage 2: Dual-Engine Parallel Processing */}
        <div className="p-5 rounded-2xl bg-black/40 border border-white/[0.08]">
          <div className="text-center text-xs font-mono uppercase tracking-widest text-slate-400 font-bold mb-4">
            Stage 02 // Parallel Hybrid Processing Core
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Engine A: ML NLP */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-indigo-500/30 space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  <span className="text-sm font-bold text-white">Engine A: NLP & Machine Learning</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Statistical
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Applies scikit-learn's <strong className="text-indigo-300">TF-IDF Vectorizer</strong> across 10,000+ vocabulary features, followed by a calibrated <strong className="text-indigo-300">Logistic Regression</strong> classifier.
              </p>
              <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.04] text-[11px] font-mono text-slate-300 space-y-1">
                <div>• Output: Fraud Probability [0.0 - 1.0]</div>
                <div>• Classification: Genuine vs Fraudulent</div>
              </div>
            </div>

            {/* Engine B: Heuristic Rules */}
            <div className="p-5 rounded-xl bg-slate-900/80 border border-amber-500/30 space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  <span className="text-sm font-bold text-white">Engine B: Heuristic Threat Rules</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Deterministic
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Scans through <strong className="text-amber-300">8 Regex Rules</strong> covering advance-fee extortion, Telegram redirects, generic personal webmail domains, and OTP/identity theft.
              </p>
              <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.04] text-[11px] font-mono text-slate-300 space-y-1">
                <div>• Output: Cumulative Threat Score [0 - 100]</div>
                <div>• Categorized Explanations & Severity Weights</div>
              </div>
            </div>
          </div>
        </div>

        {/* Pipeline Stage 3: Ensemble Risk Blending */}
        <div className="flex flex-col items-center">
          <ArrowDown className="w-5 h-5 text-indigo-500 my-2" />
          <div className="p-5 rounded-xl bg-slate-900 border border-purple-500/40 text-center w-full max-w-xl shadow-lg shadow-purple-500/10">
            <div className="text-xs font-mono font-bold text-purple-400 uppercase tracking-wider mb-1">
              [ Stage 03 ] Ensemble Risk Analyzer & Safety Floor
            </div>
            <div className="text-xs text-slate-300">
              Blends 50% ML Probability + 50% Rule Heuristic Score. If any <span className="text-red-400 font-bold">CRITICAL</span> severity flag (e.g., upfront fee or banking details) triggers, an automatic <span className="text-red-400 font-bold">75+ Risk Floor</span> is strictly enforced.
            </div>
          </div>
          <ArrowDown className="w-5 h-5 text-purple-500 my-2" />
        </div>

        {/* Pipeline Stage 4: Output & Persistence */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/[0.06] text-center">
            <Terminal className="w-5 h-5 text-emerald-400 mx-auto mb-2" />
            <div className="text-xs font-bold text-white">Full-Stack SaaS UI</div>
            <div className="text-[11px] text-slate-400 mt-1">
              React + Tailwind glassmorphic dashboard & SVG Risk Gauge
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/[0.06] text-center">
            <Database className="w-5 h-5 text-blue-400 mx-auto mb-2" />
            <div className="text-xs font-bold text-white">SQLite Persistence</div>
            <div className="text-[11px] text-slate-400 mt-1">
              Embedded relational storage for audits and telemetry
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/[0.06] text-center">
            <Sparkles className="w-5 h-5 text-indigo-400 mx-auto mb-2" />
            <div className="text-xs font-bold text-white">Local Ollama LLM</div>
            <div className="text-[11px] text-slate-400 mt-1">
              100% private offline explanation synthesis
            </div>
          </div>
        </div>
      </div>

      {/* Technical Specifications Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-2xl border border-white/[0.08]">
          <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4 text-blue-400" />
            <span>Architecture & Security Guarantees</span>
          </h3>
          <ul className="space-y-3 text-xs text-slate-300">
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Zero Cloud Dependency:</strong> All inference runs 100% locally on standard hardware without external API bills or telemetry leaks.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Explainable AI:</strong> Replaces opaque black-box verdicts with itemized heuristic evidence and concrete safety checklists.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Audited SQLite Storage:</strong> Indexed by timestamp and risk tier for compliance reporting and historical pattern analysis.</span>
            </li>
          </ul>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-white/[0.08]">
          <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-indigo-400" />
            <span>Technology Stack</span>
          </h3>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <span className="text-slate-400 font-mono">Backend Engine</span>
              <span className="text-slate-200 font-medium">FastAPI + Python 3.13</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <span className="text-slate-400 font-mono">Machine Learning</span>
              <span className="text-slate-200 font-medium">Scikit-Learn (TF-IDF + Logistic Reg)</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <span className="text-slate-400 font-mono">Frontend Client</span>
              <span className="text-slate-200 font-medium">React 19 + Vite 8 + Tailwind CSS</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <span className="text-slate-400 font-mono">Local LLM Interface</span>
              <span className="text-slate-200 font-medium">Ollama REST Engine (llama3.2 / gemma)</span>
            </div>
            <div className="flex justify-between p-2 rounded-lg bg-black/30 border border-white/[0.04]">
              <span className="text-slate-400 font-mono">Data Persistence</span>
              <span className="text-slate-200 font-medium">SQLite 3 (Local Embedded)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
