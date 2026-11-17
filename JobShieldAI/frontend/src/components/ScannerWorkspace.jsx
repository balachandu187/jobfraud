import React, { useState } from 'react';
import { 
  Radar, 
  Sparkles, 
  ShieldCheck, 
  AlertTriangle, 
  AlertOctagon, 
  Terminal, 
  Copy, 
  Check, 
  ChevronDown, 
  ChevronUp, 
  RotateCw,
  Cpu,
  Layers,
  FileText,
  Building,
  Mail,
  DollarSign,
  BookmarkCheck,
  Zap,
  Info,
  Link2,
  ImageUp,
  Loader2
} from 'lucide-react';
import RiskGauge from './RiskGauge';

export default function ScannerWorkspace({ 
  currentScan, 
  onScanComplete, 
  systemStatus 
}) {
  // Input Form State
  const [activeInputTab, setActiveInputTab] = useState('raw'); // 'raw' or 'structured'
  const [jobTitle, setJobTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [salaryInfo, setSalaryInfo] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [instructions, setInstructions] = useState('');
  const [skills, setSkills] = useState('');
  const [jobDescription, setJobDescription] = useState('');

  // Scanning & AI State
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [useOllama, setUseOllama] = useState(false);
  const [selectedModel, setSelectedModel] = useState(systemStatus?.active_ollama_model || 'llama3.2:latest');
  const [expandedWarning, setExpandedWarning] = useState(null);
  const [copiedReport, setCopiedReport] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [dynamicAiText, setDynamicAiText] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [extracting, setExtracting] = useState(false);

  // Demo Presets
  const presets = [
    {
      id: 'scam_fee',
      label: '🚨 Upfront Fee Scam',
      badge: 'High Risk',
      color: 'border-red-500/30 text-red-400 bg-red-500/10',
      data: {
        title: 'Work From Home Typist & Data Entry',
        company: 'FastCareers Online Services',
        salary: '₹80,000 per month',
        email: 'careers.recruitmentdesk@gmail.com',
        instructions: 'Pay ₹2,000 refundable registration fee to confirm your joining. No interview required.',
        skills: 'Basic typing, MS Word, Internet browsing',
        description: 'Congratulations! You are selected for an online work-from-home job with an attractive salary of ₹80,000 per month. Direct selection letter issued without any interview. Pay ₹2,000 registration fees to confirm your position today. Telegram contact @FastCareersAdmin.'
      }
    },
    {
      id: 'genuine_tech',
      label: '🛡️ Genuine Tech Role',
      badge: 'Safe',
      color: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10',
      data: {
        title: 'Senior Software Engineer (Python / FastAPI)',
        company: 'ABC Technologies Ltd',
        salary: '₹14,00,000 - ₹18,00,000 per annum',
        email: 'talent@abctechnologies.com',
        instructions: 'Apply through company official careers portal. Technical interview and coding assessment required.',
        skills: 'Python, FastAPI, PostgreSQL, Docker, Git, REST APIs',
        description: 'Senior Software Engineer position at ABC Technologies Ltd. Candidates should have solid Python, backend API engineering, and distributed systems experience. Applicants will undergo two rounds of technical interviews and credentials verification. Apply through the company official careers portal.'
      }
    },
    {
      id: 'scam_otp',
      label: '⚠️ OTP & Identity Scam',
      badge: 'Critical Risk',
      color: 'border-amber-500/30 text-amber-400 bg-amber-500/10',
      data: {
        title: 'Back Office Assistant & Payment Coordinator',
        company: 'Apex Global Hires',
        salary: '₹60,000 monthly',
        email: 'apexhires@yahoo.com',
        instructions: 'Send Aadhaar card, bank account number, and share verification OTP when prompted.',
        skills: 'None required, immediate joining',
        description: 'Immediate hiring! Guaranteed job placement with daily salary. Send your Aadhaar details, bank account information, and share verification OTP to complete appointment letter issuance. Message HR directly on WhatsApp.'
      }
    }
  ];

  const handleApplyPreset = (preset) => {
    setJobTitle(preset.data.title);
    setCompanyName(preset.data.company);
    setSalaryInfo(preset.data.salary);
    setContactEmail(preset.data.email);
    setInstructions(preset.data.instructions);
    setSkills(preset.data.skills);
    setJobDescription(preset.data.description);
    setErrorMessage('');
  };

  const handleClearInputs = () => {
    setJobTitle('');
    setCompanyName('');
    setSalaryInfo('');
    setContactEmail('');
    setInstructions('');
    setSkills('');
    setJobDescription('');
    setErrorMessage('');
  };

  // Extracts a readable error message from a failed API response.
  const describeFailure = async (response, fallback) => {
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') return body.detail;
      if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
    } catch {
      /* response was not JSON */
    }
    return fallback;
  };

  const handleRunScan = async (e) => {
    if (e) e.preventDefault();
    if (!jobDescription.trim()) {
      setErrorMessage('Please provide the job advertisement text to analyze.');
      return;
    }
    setErrorMessage('');
    setIsScanning(true);
    setScanStep(1);

    // Progress simulation steps
    const timer1 = setTimeout(() => setScanStep(2), 350);
    const timer2 = setTimeout(() => setScanStep(3), 700);

    try {
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_title: jobTitle,
          company_name: companyName,
          salary_info: salaryInfo,
          contact_email: contactEmail,
          instructions: instructions,
          skills: skills,
          job_description: jobDescription,
          ollama_model: selectedModel,
          include_ai_explanation: useOllama
        })
      });

      if (!response.ok) {
        setErrorMessage(await describeFailure(response, `Scan failed (HTTP ${response.status}).`));
        return;
      }

      const data = await response.json();
      setDynamicAiText(data.ai_explanation?.text || null);
      onScanComplete(data);
    } catch (err) {
      console.error('Scan error:', err);
      setErrorMessage('Failed to connect to backend scan engine. Please ensure api.py is running.');
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      setIsScanning(false);
      setScanStep(0);
    }
  };

  // Fetches the posting from a URL, then scans the extracted text server-side.
  const handleUrlScan = async (e) => {
    if (e) e.preventDefault();
    if (!sourceUrl.trim()) {
      setErrorMessage('Enter the URL of the job advertisement.');
      return;
    }
    setErrorMessage('');
    setIsScanning(true);
    setScanStep(1);
    const timer = setTimeout(() => setScanStep(2), 500);
    try {
      const response = await fetch('/api/scan/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: sourceUrl.trim(),
          job_title: jobTitle,
          company_name: companyName,
          ollama_model: selectedModel,
          include_ai_explanation: useOllama
        })
      });
      if (!response.ok) {
        setErrorMessage(await describeFailure(response, `Could not analyse that URL (HTTP ${response.status}).`));
        return;
      }
      const data = await response.json();
      setJobDescription(data.job_description || '');
      setDynamicAiText(data.ai_explanation?.text || null);
      onScanComplete(data);
    } catch (err) {
      console.error('URL scan error:', err);
      setErrorMessage('Failed to reach the backend scan engine.');
    } finally {
      clearTimeout(timer);
      setIsScanning(false);
      setScanStep(0);
    }
  };

  // OCRs an uploaded screenshot on the server, then scans the extracted text.
  const handleImageScan = async (e) => {
    if (e) e.preventDefault();
    if (!imageFile) {
      setErrorMessage('Choose a screenshot of the job advertisement first.');
      return;
    }
    setErrorMessage('');
    setIsScanning(true);
    setScanStep(1);
    const timer = setTimeout(() => setScanStep(2), 600);
    try {
      const form = new FormData();
      form.append('file', imageFile);
      form.append('job_title', jobTitle);
      form.append('company_name', companyName);
      form.append('ollama_model', selectedModel);
      form.append('include_ai_explanation', String(useOllama));

      const response = await fetch('/api/scan/image', { method: 'POST', body: form });
      if (!response.ok) {
        setErrorMessage(await describeFailure(response, `Could not read that screenshot (HTTP ${response.status}).`));
        return;
      }
      const data = await response.json();
      setJobDescription(data.job_description || '');
      setDynamicAiText(data.ai_explanation?.text || null);
      onScanComplete(data);
    } catch (err) {
      console.error('Image scan error:', err);
      setErrorMessage('Failed to upload the screenshot to the backend.');
    } finally {
      clearTimeout(timer);
      setIsScanning(false);
      setScanStep(0);
    }
  };

  const handleGenerateOllama = async () => {
    if (!currentScan) return;
    setAiLoading(true);
    try {
      const res = await fetch('/api/ollama/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_title: currentScan.job_title,
          company_name: currentScan.company_name,
          risk_score: currentScan.risk_result?.risk_score || 0,
          risk_level: currentScan.risk_result?.risk_level || 'Unknown',
          warnings: currentScan.risk_result?.warnings || [],
          model_name: selectedModel
        })
      });
      const data = await res.json();
      setDynamicAiText(data.text);
    } catch (err) {
      console.error('Ollama error:', err);
      setDynamicAiText('Local Ollama engine unreachable on localhost:11434. Displaying rule-based checklist.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleCopyReport = () => {
    if (!currentScan) return;
    const risk = currentScan.risk_result;
    const warningsText = risk?.warnings?.map(w => `• [${w.severity}] ${w.title}: ${w.explanation}`).join('\n') || 'None';
    const tipsText = currentScan.safety_tips?.map(t => `✓ ${t}`).join('\n') || 'None';
    
    const report = `================================================
JOBSHIELD AI — RECRUITMENT CREDIBILITY REPORT
================================================
Job Title: ${currentScan.job_title || 'Unspecified'}
Employer:  ${currentScan.company_name || 'Not Disclosed'}
Security Assessment: ${risk?.risk_level} (${risk?.verdict})
Composite Risk Score: ${risk?.risk_score} / 100

MACHINE LEARNING TELEMETRY:
• Prediction: ${currentScan.ml_result?.prediction_label}
• Fraud Probability: ${currentScan.ml_result?.fraud_score_pct}%
• Genuine Probability: ${Math.round((currentScan.ml_result?.genuine_probability || 0) * 100)}%

DETECTED RED FLAGS:
${warningsText}

SAFETY ACTION PLAN:
${tipsText}

AI SYNTHESIS:
${dynamicAiText || currentScan.ai_explanation?.text || 'Automated rule verification complete.'}
================================================`;

    navigator.clipboard.writeText(report);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  const risk = currentScan?.risk_result;
  const ml = currentScan?.ml_result;
  const warnings = risk?.warnings || [];
  const safetyTips = currentScan?.safety_tips || [];

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-2 font-mono">
            <Radar className="w-3.5 h-3.5 animate-spin text-blue-400" />
            Inspection Console
          </div>
          <h2 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
            Dual-Engine Job Scanner
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Evaluate job postings against probabilistic NLP models and 8 high-confidence fraud heuristics.
          </p>
        </div>

        {/* Live Preset Demo Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500 font-mono font-medium hidden sm:inline">
            Load Preset:
          </span>
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => handleApplyPreset(p)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-150 hover:scale-[1.03] active:scale-[0.98] cursor-pointer ${p.color}`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Split-Screen 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* ======================================================== */}
        {/* LEFT COLUMN: Input Workspace (5 cols on lg)              */}
        {/* ======================================================== */}
        <div className="lg:col-span-5 glass-panel p-6 rounded-2xl border border-white/[0.08] space-y-5">
          {/* Input Mode Tabs */}
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              {[
                { id: 'raw', label: 'Raw Text' },
                { id: 'structured', label: 'Structured Fields' },
                { id: 'url', label: 'From URL' },
                { id: 'image', label: 'Screenshot' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => { setActiveInputTab(tab.id); setErrorMessage(''); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    activeInputTab === tab.id
                      ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20 font-bold'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={handleClearInputs}
              className="text-xs text-slate-500 hover:text-slate-300 font-mono transition-colors cursor-pointer"
            >
              Reset
            </button>
          </div>

          {/* URL ingestion form */}
          {activeInputTab === 'url' && (
            <form onSubmit={handleUrlScan} className="space-y-3 animate-fadeIn">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Job Advertisement URL
                </label>
                <input
                  type="url"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://company.com/careers/apply/12345"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
                <p className="text-[11px] text-slate-500 mt-1.5 leading-relaxed">
                  The server fetches the page, strips navigation and scripts, then runs the
                  dual-engine scan. Private and loopback addresses are refused.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">Job Title (optional)</label>
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="e.g. Backend Engineer"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">Company (optional)</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. ABC Technologies"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              {errorMessage && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isScanning}
                className={`w-full py-3 px-4 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2.5 transition-all shadow-lg ${
                  isScanning
                    ? 'bg-blue-700/60 cursor-not-allowed border border-blue-500/30'
                    : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-500/20 border border-blue-400/40 cursor-pointer'
                }`}
              >
                {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4 text-blue-200" />}
                <span>{isScanning ? 'Fetching and scanning page...' : 'Fetch URL & Scan'}</span>
              </button>
            </form>
          )}

          {/* Screenshot / OCR form */}
          {activeInputTab === 'image' && (
            <form onSubmit={handleImageScan} className="space-y-3 animate-fadeIn">
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Screenshot of the Advertisement
              </label>
              <label className="flex flex-col items-center justify-center gap-2 p-6 rounded-xl border border-dashed border-white/[0.12] bg-slate-900/50 hover:border-blue-500/40 transition-colors cursor-pointer">
                <ImageUp className="w-6 h-6 text-slate-500" />
                <span className="text-xs text-slate-400">
                  {imageFile ? imageFile.name : 'Click to choose a PNG or JPG (max 8 MB)'}
                </span>
                {imageFile && (
                  <span className="text-[11px] text-slate-500 font-mono">
                    {(imageFile.size / 1024).toFixed(0)} KB
                  </span>
                )}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                />
              </label>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Text is extracted with Tesseract OCR on the server, then scored. Requires the
                Tesseract binary to be installed on the host.
              </p>

              {errorMessage && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isScanning || !imageFile}
                className={`w-full py-3 px-4 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2.5 transition-all shadow-lg ${
                  isScanning || !imageFile
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/[0.06]'
                    : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-500/20 border border-blue-400/40 cursor-pointer'
                }`}
              >
                {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImageUp className="w-4 h-4 text-blue-200" />}
                <span>{isScanning ? 'Running OCR and scan...' : 'Extract Text & Scan'}</span>
              </button>
            </form>
          )}

          {/* Form */}
          <form onSubmit={handleRunScan} className={`space-y-4 ${activeInputTab === 'url' || activeInputTab === 'image' ? 'hidden' : ''}`}>
            {activeInputTab === 'structured' && (
              <div className="space-y-3.5 animate-fadeIn">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      Job Title
                    </label>
                    <input
                      type="text"
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      placeholder="e.g. Senior Software Engineer"
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      Company Name
                    </label>
                    <input
                      type="text"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="e.g. ABC Technologies Ltd"
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      Offered Compensation
                    </label>
                    <input
                      type="text"
                      value={salaryInfo}
                      onChange={(e) => setSalaryInfo(e.target.value)}
                      placeholder="e.g. ₹80,000 per month"
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      Recruiter Email / URL
                    </label>
                    <input
                      type="text"
                      value={contactEmail}
                      onChange={(e) => setContactEmail(e.target.value)}
                      placeholder="e.g. hr@abctechnologies.com"
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Application Instructions / Contact Channels
                  </label>
                  <input
                    type="text"
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="e.g. Apply on careers portal or WhatsApp HR"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-900/80 border border-white/[0.08] text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {/* Description Text Area */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-mono text-slate-300 font-semibold">
                  Job Advertisement Text <span className="text-red-400">*</span>
                </label>
                <span className="text-[11px] text-slate-500 font-mono">
                  {jobDescription.length} characters
                </span>
              </div>
              <textarea
                rows={activeInputTab === 'raw' ? 9 : 5}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job advertisement, WhatsApp offer letter, email thread, or recruitment pitch here..."
                className="w-full px-3.5 py-3 rounded-xl bg-slate-900/90 border border-white/[0.08] text-white text-xs leading-relaxed placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-sans resize-y"
              />
            </div>

            {/* Ollama Local AI Option */}
            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.06] space-y-2.5">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useOllama}
                    onChange={(e) => setUseOllama(e.target.checked)}
                    className="w-4 h-4 rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-0 cursor-pointer"
                  />
                  <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    Enrich with Local Ollama AI
                  </span>
                </label>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${systemStatus?.ollama_available ? 'bg-emerald-500/15 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                  {systemStatus?.ollama_available ? 'Ollama Online' : 'Offline (Fallback)'}
                </span>
              </div>

              {useOllama && (
                <div className="pt-2 border-t border-white/[0.04] flex items-center justify-between gap-3">
                  <span className="text-[11px] text-slate-400 font-mono">Model:</span>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="px-2 py-1 rounded bg-slate-800 border border-white/[0.08] text-xs text-slate-300 focus:outline-none font-mono"
                  >
                    {(() => {
                      // Prefer models actually pulled locally; fall back to suggestions.
                      const models = systemStatus?.ollama_models?.length
                        ? systemStatus.ollama_models
                        : (systemStatus?.suggested_ollama_models || ['llama3.2:latest']);
                      return models.map((m) => <option key={m} value={m}>{m}</option>);
                    })()}
                  </select>
                </div>
              )}
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Run Button */}
            <button
              type="submit"
              disabled={isScanning}
              className={`w-full py-3 px-4 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2.5 transition-all shadow-lg ${
                isScanning
                  ? 'bg-blue-700/60 cursor-not-allowed border border-blue-500/30'
                  : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-500/20 border border-blue-400/40 hover:scale-[1.01] active:scale-[0.99] cursor-pointer'
              }`}
            >
              {isScanning ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin text-white" />
                  <span>
                    {scanStep === 1 && 'Extracting n-gram vector features...'}
                    {scanStep === 2 && 'Executing 8 heuristic security rules...'}
                    {scanStep === 3 && 'Calibrating composite risk index...'}
                    {scanStep === 0 && 'Scanning Advertisement...'}
                  </span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-blue-300" />
                  <span>Run Dual-Engine Security Scan</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* ======================================================== */}
        {/* RIGHT COLUMN: Live Intelligence Results (7 cols on lg)   */}
        {/* ======================================================== */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Idle / Empty Placeholder State */}
          {!currentScan && !isScanning && (
            <div className="glass-panel p-10 rounded-2xl border border-white/[0.08] text-center flex flex-col items-center justify-center min-h-[500px]">
              <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-4 shadow-lg shadow-blue-500/10 relative">
                <Radar className="w-8 h-8 text-blue-400 animate-pulse" />
                <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-blue-500 animate-ping" />
              </div>
              <h3 className="text-lg font-bold text-white">Live Intelligence Stream</h3>
              <p className="text-slate-400 text-xs max-w-sm mt-1.5 leading-relaxed">
                Awaiting advertisement submission. Choose a demo preset on the left or paste a real posting to generate comprehensive threat telemetry.
              </p>
              
              <div className="mt-8 grid grid-cols-3 gap-3 w-full max-w-md text-left">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                  <div className="text-[11px] font-mono font-bold text-emerald-400">01. NLP Vector</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">TF-IDF n-grams</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                  <div className="text-[11px] font-mono font-bold text-amber-400">02. Heuristics</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">8 Fraud Rules</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04]">
                  <div className="text-[11px] font-mono font-bold text-red-400">03. Risk Floor</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Critical 75+</div>
                </div>
              </div>
            </div>
          )}

          {/* Scanning Animation State */}
          {isScanning && (
            <div className="glass-panel p-12 rounded-2xl border border-blue-500/30 text-center flex flex-col items-center justify-center min-h-[500px] relative overflow-hidden">
              <div className="absolute inset-0 bg-blue-500/5 pointer-events-none" />
              <div className="w-20 h-20 rounded-full border-2 border-blue-500/30 flex items-center justify-center relative mb-6">
                <div className="w-16 h-16 rounded-full border border-blue-400/50 flex items-center justify-center">
                  <Radar className="w-8 h-8 text-blue-400 animate-spin" />
                </div>
                <span className="absolute inset-0 rounded-full border border-blue-500 animate-ping opacity-30" />
              </div>

              <h3 className="text-xl font-bold text-white">Inspecting Threat Vectors</h3>
              <p className="text-slate-400 text-xs mt-1">Cross-referencing ML classifiers and extortion heuristics...</p>

              <div className="w-64 bg-slate-800 h-1.5 rounded-full mt-6 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-300"
                  style={{ width: scanStep === 1 ? '35%' : scanStep === 2 ? '70%' : '95%' }}
                />
              </div>
            </div>
          )}

          {/* Full Results View */}
          {currentScan && !isScanning && (
            <div className="space-y-6 animate-fadeIn">
              
              {/* Header Card */}
              <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] relative overflow-hidden">
                <div 
                  className="absolute top-0 left-0 bottom-0 w-1.5"
                  style={{ backgroundColor: risk?.theme_color || '#3B82F6' }}
                />
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pl-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold text-white tracking-tight">
                        {currentScan.job_title || 'Unspecified Job Position'}
                      </h3>
                      <span 
                        className="text-[11px] font-bold px-2 py-0.5 rounded-full font-mono uppercase tracking-wider"
                        style={{ 
                          backgroundColor: `${risk?.theme_color}20`,
                          color: risk?.theme_color,
                          border: `1px solid ${risk?.theme_color}40`
                        }}
                      >
                        {risk?.risk_level}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex items-center gap-3">
                      <span>Employer: <strong className="text-slate-200">{currentScan.company_name || 'Not Disclosed'}</strong></span>
                      <span>•</span>
                      <span>Audit ID: <strong className="font-mono text-slate-200">#{currentScan.scan_id}</strong></span>
                    </div>
                  </div>

                  <button
                    onClick={handleCopyReport}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs font-semibold text-slate-300 border border-white/[0.08] transition-all cursor-pointer self-start sm:self-auto"
                  >
                    {copiedReport ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Report</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Gauge & Machine Learning Telemetry Split */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
                {/* Gauge Card (5 cols) */}
                <div className="md:col-span-5 glass-panel p-5 rounded-2xl border border-white/[0.08] flex flex-col items-center justify-center text-center">
                  <span className="text-xs font-bold uppercase tracking-wider font-mono text-slate-400 mb-2">
                    Ensemble Risk Index
                  </span>
                  <RiskGauge
                    score={risk?.risk_score}
                    riskLevel={risk?.risk_level}
                    verdict={risk?.verdict}
                    themeColor={risk?.theme_color}
                  />
                  <div className="text-[11px] text-slate-500 mt-3 font-mono">
                    Ensemble Blended Weight (50% ML + 50% Rules)
                  </div>
                </div>

                {/* Engine Breakdown (7 cols) */}
                <div className="md:col-span-7 glass-panel p-5 rounded-2xl border border-white/[0.08] flex flex-col justify-between space-y-4">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider font-mono text-slate-400">
                      Dual-Engine Evaluation Telemetry
                    </span>
                    
                    <div className="mt-3.5 space-y-3">
                      {/* ML Fraud Probability Bar */}
                      <div>
                        <div className="flex justify-between text-xs font-mono mb-1">
                          <span className="text-slate-300">ML Fraud Probability</span>
                          <span className="text-red-400 font-bold">{ml?.fraud_score_pct || 0}%</span>
                        </div>
                        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-red-500 h-full rounded-full transition-all duration-1000"
                            style={{ width: `${ml?.fraud_score_pct || 0}%` }}
                          />
                        </div>
                      </div>

                      {/* ML Genuine Probability Bar */}
                      <div>
                        <div className="flex justify-between text-xs font-mono mb-1">
                          <span className="text-slate-300">ML Genuine Probability</span>
                          <span className="text-emerald-400 font-bold">
                            {Math.round((ml?.genuine_probability || 0) * 100)}%
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-emerald-500 h-full rounded-full transition-all duration-1000"
                            style={{ width: `${(ml?.genuine_probability || 0) * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* Rule Heuristic Threat Score */}
                      <div>
                        <div className="flex justify-between text-xs font-mono mb-1">
                          <span className="text-slate-300">Rule-Based Threat Score</span>
                          <span className="text-amber-400 font-bold">{risk?.rule_score || 0} / 100</span>
                        </div>
                        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-amber-500 h-full rounded-full transition-all duration-1000"
                            style={{ width: `${risk?.rule_score || 0}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-900/60 border border-white/[0.04] text-[11px] text-slate-400 flex items-start gap-2">
                    <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                    <span>
                      {risk?.disclaimer}
                    </span>
                  </div>
                </div>
              </div>

              {/* Detected Red Flags Section */}
              <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Triggered Warning Signs ({warnings.length})
                  </h4>
                  <span className="text-xs text-slate-500 font-mono">
                    8 Heuristics Audited
                  </span>
                </div>

                {warnings.length === 0 ? (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2.5">
                    <ShieldCheck className="w-4 h-4 shrink-0" />
                    <span>No critical extortion indicators or suspicious recruitment patterns triggered.</span>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {warnings.map((w, index) => {
                      const isCritical = w.severity === 'CRITICAL';
                      const isHigh = w.severity === 'HIGH';
                      const color = isCritical ? '#EF4444' : isHigh ? '#F59E0B' : '#EAB308';
                      const isExpanded = expandedWarning === index;

                      return (
                        <div 
                          key={w.id || index}
                          className="rounded-xl bg-slate-900/70 border border-white/[0.06] overflow-hidden transition-all"
                        >
                          <button
                            type="button"
                            onClick={() => setExpandedWarning(isExpanded ? null : index)}
                            className="w-full p-3.5 flex items-center justify-between text-left hover:bg-white/[0.02] cursor-pointer"
                          >
                            <div className="flex items-center gap-2.5">
                              <span 
                                className="w-2 h-2 rounded-full shrink-0"
                                style={{ backgroundColor: color }}
                              />
                              <div>
                                <span className="text-xs font-bold text-white tracking-tight">
                                  {w.title}
                                </span>
                                <span className="text-[10px] text-slate-400 ml-2 font-mono">
                                  [{w.category}]
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span 
                                className="text-[10px] font-bold font-mono px-2 py-0.5 rounded uppercase"
                                style={{ 
                                  backgroundColor: `${color}15`, 
                                  color: color,
                                  border: `1px solid ${color}30` 
                                }}
                              >
                                {w.severity} (+{w.weight})
                              </span>
                              {isExpanded ? (
                                <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                              ) : (
                                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                              )}
                            </div>
                          </button>

                          {isExpanded && (
                            <div className="px-4 pb-3.5 pt-1 text-xs text-slate-300 leading-relaxed border-t border-white/[0.04] bg-black/20">
                              {w.explanation}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Safety Action Checklist */}
              <div className="glass-panel p-5 rounded-2xl border border-white/[0.08] space-y-3">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <BookmarkCheck className="w-4 h-4 text-emerald-400" />
                  Prescribed Safety Recommendations
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {safetyTips.map((tip, idx) => (
                    <div 
                      key={idx} 
                      className="p-3 rounded-xl bg-slate-900/60 border border-white/[0.04] text-xs text-slate-300 flex items-start gap-2.5"
                    >
                      <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{tip}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Terminal-Style AI Mentor Card */}
              <div className="rounded-2xl bg-black/80 border border-slate-700/80 p-5 font-mono relative overflow-hidden shadow-2xl">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-bold text-slate-200">
                      OLLAMA_AI_MENTOR // SECURITY_SYNTHESIS
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-500">
                      MODEL: {selectedModel}
                    </span>
                    <button
                      onClick={handleGenerateOllama}
                      disabled={aiLoading}
                      className="text-xs px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors flex items-center gap-1 cursor-pointer"
                    >
                      <RotateCw className={`w-3 h-3 ${aiLoading ? 'animate-spin' : ''}`} />
                      <span>{aiLoading ? 'Querying...' : 'Regenerate'}</span>
                    </button>
                  </div>
                </div>

                <div className="text-xs leading-relaxed text-emerald-400/90 whitespace-pre-wrap">
                  {dynamicAiText || currentScan.ai_explanation?.text || (
                    `> Dual-engine analysis completed.\n> Job evaluated as [${risk?.risk_level}] with score ${risk?.risk_score}/100.\n> Heuristic rules evaluated: ${warnings.length} warning signals flagged.\n> Applicant action: Verify employer portal and never pay advance fees.`
                  )}
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
