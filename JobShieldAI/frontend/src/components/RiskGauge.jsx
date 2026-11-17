import React from 'react';

export default function RiskGauge({ score = 0, riskLevel = 'Low Risk', verdict = 'Likely Genuine', themeColor = '#10B981' }) {
  // Clamp score between 0 and 100
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));
  
  // Angle: -180 deg (0) to 0 deg (100)
  // In radians: PI to 2*PI, or semi-circle
  const radius = 88;
  const strokeWidth = 14;
  const cx = 120;
  const cy = 115;
  const circumference = Math.PI * radius; // Semi-circle circumference
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference;

  // Calculate needle angle (-90deg at 0 to +90deg at 100)
  const needleAngle = -90 + (clampedScore / 100) * 180;

  return (
    <div className="flex flex-col items-center justify-center relative p-2">
      <svg width="240" height="150" viewBox="0 0 240 150" className="overflow-visible">
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10B981" />
            <stop offset="35%" stopColor="#10B981" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="75%" stopColor="#EF4444" />
            <stop offset="100%" stopColor="#DC2626" />
          </linearGradient>
          <filter id="gaugeGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Background Track Arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Ticks & Threshold Markers */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          filter="url(#gaugeGlow)"
          className="transition-all duration-1000 ease-out"
        />

        {/* Tick Labels */}
        <text x="26" y="132" fill="#64748B" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">0</text>
        <text x="64" y="62" fill="#64748B" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">35</text>
        <text x="114" y="24" fill="#64748B" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">50</text>
        <text x="166" y="62" fill="#64748B" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">65</text>
        <text x="206" y="132" fill="#64748B" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">100</text>

        {/* Needle Pin / Center Point */}
        <circle cx={cx} cy={cy} r="6" fill="#1E293B" stroke={themeColor} strokeWidth="3" />
        
        {/* Animated Needle */}
        <g transform={`rotate(${needleAngle} ${cx} ${cy})`} className="transition-transform duration-1000 ease-out">
          <line
            x1={cx}
            y1={cy}
            x2={cx}
            y2={cy - radius + 6}
            stroke={themeColor}
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          <circle cx={cx} cy={cy - radius + 6} r="3" fill="#FFFFFF" />
        </g>
      </svg>

      {/* Numerical readout */}
      <div className="text-center -mt-3">
        <div className="flex items-baseline justify-center gap-1">
          <span 
            className="text-4xl font-extrabold tracking-tight font-mono transition-colors duration-500"
            style={{ color: themeColor }}
          >
            {clampedScore}
          </span>
          <span className="text-sm font-semibold text-slate-400 font-mono">/ 100</span>
        </div>
        <div className="mt-1 flex items-center justify-center gap-1.5">
          <span 
            className="inline-block w-2 h-2 rounded-full animate-ping"
            style={{ backgroundColor: themeColor }}
          />
          <span 
            className="text-xs uppercase tracking-wider font-bold px-2 py-0.5 rounded-full"
            style={{ 
              backgroundColor: `${themeColor}20`,
              color: themeColor,
              border: `1px solid ${themeColor}40`
            }}
          >
            {riskLevel} • {verdict}
          </span>
        </div>
      </div>
    </div>
  );
}
