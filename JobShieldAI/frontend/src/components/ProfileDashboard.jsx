import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  BadgeCheck,
  CheckCircle2,
  Fingerprint,
  LoaderCircle,
  Mail,
  Pencil,
  Save,
  ShieldCheck,
  UserRound
} from 'lucide-react';

export default function ProfileDashboard({ user, token, onProfileUpdated }) {
  const name = user?.name || user?.full_name || 'JobShield Analyst';
  const email = user?.email || 'Email unavailable';
  const role = user?.role || 'analyst';
  const authMethod = user?.auth_provider === 'google' ? 'Google OAuth' : 'Email and password';
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [nameDraft, setNameDraft] = useState(name);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  useEffect(() => {
    setNameDraft(name);
  }, [name]);

  const handleSaveProfile = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setIsSaving(true);

    try {
      const response = await fetch('/api/auth/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ full_name: nameDraft.trim() }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Unable to update your profile.');
      }

      onProfileUpdated(data);
      setNameDraft(data.user.name);
      setIsEditing(false);
      setSuccessMessage('Display name updated.');
    } catch (requestError) {
      setErrorMessage(requestError.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setNameDraft(name);
    setIsEditing(false);
    setErrorMessage('');
    setSuccessMessage('');
  };

  const details = [
    { label: 'Full name', value: name, icon: UserRound },
    { label: 'Email address', value: email, icon: Mail },
    { label: 'Access role', value: role, icon: ShieldCheck },
    { label: 'Sign-in method', value: authMethod, icon: Fingerprint },
  ];

  if (user?.id !== undefined && user?.id !== null) {
    details.push({ label: 'Account ID', value: `#${user.id}`, icon: BadgeCheck });
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      <div>
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-2 font-mono">
          <UserRound className="w-3.5 h-3.5" />
          Account Center
        </div>
        <h2 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
          Profile Dashboard
        </h2>
        <p className="text-slate-400 text-sm mt-1">
          View the identity and sign-in details associated with your JobShield account.
        </p>
      </div>

      <section className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/[0.08]">
        <div className="flex flex-col sm:flex-row sm:items-center gap-5">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={`${name} profile`}
              referrerPolicy="no-referrer"
              className="w-20 h-20 rounded-2xl object-cover border border-white/10"
            />
          ) : (
            <div className="w-20 h-20 rounded-2xl bg-blue-500/15 border border-blue-500/25 text-blue-300 flex items-center justify-center">
              <span className="text-2xl font-bold">{initials || <UserRound className="w-8 h-8" />}</span>
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-xl font-bold text-white break-words">{name}</h3>
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] font-semibold uppercase tracking-wide">
                <BadgeCheck className="w-3 h-3" />
                Signed in
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1 break-all">{email}</p>
            <p className="text-xs text-slate-500 mt-2">
              Only your display name can be changed here. Identity and access details stay protected.
            </p>
          </div>
          <div className="sm:self-start">
            {!isEditing && (
              <button
                type="button"
                onClick={() => {
                  setNameDraft(name);
                  setErrorMessage('');
                  setSuccessMessage('');
                  setIsEditing(true);
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-blue-500/25 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-300 transition-colors hover:bg-blue-500/20"
              >
                <Pencil className="w-3.5 h-3.5" />
                Edit profile
              </button>
            )}
          </div>
        </div>
        {isEditing && (
          <form onSubmit={handleSaveProfile} className="mt-6 pt-5 border-t border-white/[0.08] space-y-3">
            <label htmlFor="profile-display-name" className="block text-xs font-semibold text-slate-300">
              Display name
            </label>
            <input
              id="profile-display-name"
              type="text"
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
              minLength={2}
              maxLength={80}
              required
              autoComplete="name"
              className="w-full max-w-lg rounded-xl border border-white/10 bg-slate-950 px-4 py-3 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving ? <LoaderCircle className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                {isSaving ? 'Saving…' : 'Save changes'}
              </button>
              <button
                type="button"
                onClick={handleCancelEdit}
                disabled={isSaving}
                className="rounded-xl border border-white/10 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/[0.04] disabled:opacity-60"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
        {errorMessage && (
          <div role="alert" className="mt-4 flex items-center gap-2 text-sm text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {errorMessage}
          </div>
        )}
        {successMessage && (
          <div role="status" className="mt-4 flex items-center gap-2 text-sm text-emerald-300">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            {successMessage}
          </div>
        )}
      </section>

      <section aria-label="Account details">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-bold text-white">Account Details</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {details.map((detail) => {
            const Icon = detail.icon;
            return (
              <div
                key={detail.label}
                className="glass-card p-5 rounded-2xl border border-white/[0.08]"
              >
                <div className="flex items-center gap-2 text-slate-400">
                  <Icon className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-semibold uppercase tracking-wide">
                    {detail.label}
                  </span>
                </div>
                <div className="mt-3 text-sm text-white font-medium break-words">
                  {detail.value}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
