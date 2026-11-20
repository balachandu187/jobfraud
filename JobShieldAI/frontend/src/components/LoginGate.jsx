import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { ShieldCheck } from 'lucide-react';

export default function LoginGate({ googleClientId, onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const authenticateLocal = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');

    try {
      const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const body = mode === 'register'
        ? { email, password, full_name: fullName }
        : { email, password };
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Authentication failed.');
      onAuthenticated(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const authenticateGoogle = async (credentialResponse) => {
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: credentialResponse.credential }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Google authentication failed.');
      onAuthenticated(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-white flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-3xl border border-cyan-500/20 bg-slate-900/80 p-8 shadow-2xl">
        <div className="text-center mb-6">
          <ShieldCheck className="w-12 h-12 mx-auto text-cyan-400 mb-3" />
          <h1 className="text-2xl font-bold">JobShield AI</h1>
          <p className="text-sm text-slate-400 mt-1">Security Clearance Required</p>
        </div>

        {googleClientId ? (
          <div className="flex justify-center mb-5">
            <GoogleLogin
              onSuccess={authenticateGoogle}
              onError={() => setError('Google sign-in was cancelled or failed.')}
              theme="filled_black"
              shape="pill"
              size="large"
              text="continue_with"
              width="320"
            />
          </div>
        ) : (
          <div className="mb-5 rounded-xl border border-amber-700/60 bg-amber-950/40 p-3 text-xs text-amber-300">
            Google sign-in is not configured. Set <b>GOOGLE_CLIENT_ID</b> in <b>JobShieldAI/.env</b> locally or in the deployed service environment.
          </div>
        )}

        <div className="flex items-center gap-3 mb-5">
          <div className="h-px flex-1 bg-white/10" />
          <span className="text-[10px] uppercase text-slate-500">or sign in with email</span>
          <div className="h-px flex-1 bg-white/10" />
        </div>

        <div className="flex rounded-xl bg-slate-950 p-1 mb-5">
          <button type="button" onClick={() => setMode('login')} className={`flex-1 py-2 rounded-lg text-sm ${mode === 'login' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400'}`}>Sign In</button>
          <button type="button" onClick={() => setMode('register')} className={`flex-1 py-2 rounded-lg text-sm ${mode === 'register' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400'}`}>Sign Up</button>
        </div>

        {error && <div className="mb-4 rounded-xl border border-rose-800 bg-rose-950/60 p-3 text-xs text-rose-300">{error}</div>}

        <form onSubmit={authenticateLocal} className="space-y-3">
          {mode === 'register' && (
            <input value={fullName} onChange={(event) => setFullName(event.target.value)} required placeholder="Full name" className="w-full rounded-xl border border-white/10 bg-slate-950 px-4 py-3 text-sm" />
          )}
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required placeholder="Email address" className="w-full rounded-xl border border-white/10 bg-slate-950 px-4 py-3 text-sm" />
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} placeholder="Password" className="w-full rounded-xl border border-white/10 bg-slate-950 px-4 py-3 text-sm" />
          <button type="submit" disabled={busy} className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-3 text-sm font-bold text-black disabled:opacity-60">
            {mode === 'register' ? 'Create Account' : 'Authorize Session'}
          </button>
        </form>
      </div>
    </div>
  );
}
