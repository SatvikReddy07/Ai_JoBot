import React, { useState } from "react";
import {
  Settings as SettingsIcon,
  User,
  Sliders,
  Globe2,
  Clock,
  Save,
  CheckCircle,
  AlertCircle,
  GraduationCap,
  ShieldCheck,
  Building2,
  Terminal
} from "lucide-react";
import { Settings, ScoringWeights } from "../types";
import { updateSettings } from "../lib/api";

interface SettingsViewProps {
  settings: Settings;
  onRefresh: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onRefresh
}) => {
  const [profileName, setProfileName] = useState(settings.profile_name);
  const [currentRole, setCurrentRole] = useState(settings.profile_current_role);
  const [experienceYears, setExperienceYears] = useState(settings.profile_experience_years);
  const [minScore, setMinScore] = useState(settings.min_match_score);
  const [weights, setWeights] = useState<ScoringWeights>({ ...settings.scoring_weights });
  const [autoHour, setAutoHour] = useState(settings.auto_search_hour);
  const [autoMinute, setAutoMinute] = useState(settings.auto_search_minute);

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const totalWeights =
    Number(weights.experience_seniority) +
    Number(weights.hse_technical_skills) +
    Number(weights.qualifications) +
    Number(weights.industry_relevance) +
    Number(weights.location_international) +
    Number(weights.employment_preferences);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totalWeights !== 100) {
      setErrorMsg(`Scoring weights must sum to exactly 100 (Current total: ${totalWeights}).`);
      return;
    }
    setErrorMsg("");
    setIsSaving(true);

    try {
      await updateSettings({
        profile_name: profileName,
        profile_current_role: currentRole,
        profile_experience_years: Number(experienceYears),
        min_match_score: Number(minScore),
        scoring_weights: weights,
        auto_search_hour: Number(autoHour),
        auto_search_minute: Number(autoMinute)
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update settings.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-blue-400" />
            Candidate Profile &amp; Rules-Based Matching Configuration
          </h3>
          <p className="text-xs text-slate-400">
            Tune scoring weights, target countries, and Windows Task Scheduler preferences.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {saveSuccess && (
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" />
              Settings Saved!
            </span>
          )}
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? "Saving..." : "Save Settings"}</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Profile Overview Card */}
      <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800 pb-2">
          <User className="w-4 h-4 text-emerald-400" />
          Professional Profile Baseline
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Full Name</label>
            <input
              type="text"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-semibold mb-1">Current Leadership Role</label>
            <input
              type="text"
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 font-semibold mb-1">Total Experience (Years)</label>
            <input
              type="number"
              value={experienceYears}
              onChange={(e) => setExperienceYears(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Read-only verification card of qualifications */}
        <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2">
          <p className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5">
            <GraduationCap className="w-3.5 h-3.5 text-cyan-400" />
            Verified Profile Qualifications &amp; Prior Track Record
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-slate-500 block">Education 1</span>
              <span className="font-semibold text-slate-200">M.Tech Environmental Eng.</span>
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-slate-500 block">Education 2</span>
              <span className="font-semibold text-slate-200">B.Tech Mechanical Eng.</span>
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-slate-500 block">Management</span>
              <span className="font-semibold text-slate-200">MBA Human Resources</span>
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-slate-500 block">Safety Diploma</span>
              <span className="font-semibold text-slate-200">Diploma in Industrial Safety</span>
            </div>
          </div>
          <p className="text-[10px] text-slate-500 pt-1">
            Current: Global SHE &amp; Security Manager at dsm-firmenich, Hyderabad (19 APAC manufacturing plants oversight).
          </p>
        </div>
      </div>

      {/* Configurable Scoring Weights */}
      <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Sliders className="w-4 h-4 text-cyan-400" />
            Rules-Based Scoring Weights (Total: 100 Points)
          </h4>
          <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
            totalWeights === 100
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
          }`}>
            Total: {totalWeights}/100 pts
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-1">Experience &amp; Seniority</label>
            <input
              type="number"
              min={0}
              max={50}
              value={weights.experience_seniority}
              onChange={(e) => setWeights({ ...weights, experience_seniority: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <span className="text-[10px] text-slate-500">Global/Regional scope (default: 25)</span>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">HSE Technical Skills</label>
            <input
              type="number"
              min={0}
              max={50}
              value={weights.hse_technical_skills}
              onChange={(e) => setWeights({ ...weights, hse_technical_skills: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <span className="text-[10px] text-slate-500">ISO 14001/45001, RCA, Audits (default: 25)</span>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Educational Qualifications</label>
            <input
              type="number"
              min={0}
              max={30}
              value={weights.qualifications}
              onChange={(e) => setWeights({ ...weights, qualifications: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <span className="text-[10px] text-slate-500">M.Tech, B.Tech, MBA, Safety (default: 15)</span>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Industry Relevance</label>
            <input
              type="number"
              min={0}
              max={30}
              value={weights.industry_relevance}
              onChange={(e) => setWeights({ ...weights, industry_relevance: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <span className="text-[10px] text-slate-500">Manufacturing, chemical, matrix (default: 15)</span>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Location &amp; International</label>
            <input
              type="number"
              min={0}
              max={30}
              value={weights.location_international}
              onChange={(e) => setWeights({ ...weights, location_international: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <span className="text-[10px] text-slate-500">Target countries &amp; relocation (default: 15)</span>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Employment Preferences</label>
            <input
              type="number"
              min={0}
              max={20}
              value={weights.employment_preferences}
              onChange={(e) => setWeights({ ...weights, employment_preferences: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <span className="text-[10px] text-slate-500">Permanent Full-time (default: 5)</span>
          </div>
        </div>
      </div>

      {/* Phase 2: Gemini AI Engine & Quota Configuration */}
      <div className="p-5 rounded-xl bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border border-indigo-500/30 space-y-4">
        <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            Gemini AI Engine &amp; Quota Controls (Phase 2)
          </h4>
          <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
            ₹0 / Month Free Tier
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Model Architecture</span>
            <div className="text-sm font-bold text-white font-mono">gemini-2.5-flash</div>
            <p className="text-[11px] text-slate-500">Official Google GenAI SDK. Configurable via backend environment.</p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Daily Request Quota</span>
            <div className="text-sm font-bold text-white font-mono">50 calls / day</div>
            <p className="text-[11px] text-slate-500">Hard limit prevents unexpected usage. Excess automatically falls back to rules.</p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Smart SHA-256 Cache</span>
            <div className="text-sm font-bold text-emerald-400 font-mono">Zero-Call Hits</div>
            <p className="text-[11px] text-slate-500">Unchanged job descriptions return instantly without consuming quota.</p>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800 text-[11px] text-slate-400 space-y-1">
          <div className="font-semibold text-slate-300">How to configure your free Gemini API key:</div>
          <p>
            1. Generate a free API key at <span className="text-indigo-300">https://aistudio.google.com/</span>
          </p>
          <p>
            2. Add <code className="text-cyan-300 bg-slate-900 px-1 py-0.5 rounded">GEMINI_API_KEY="your_api_key_here"</code> to your <code className="text-cyan-300 bg-slate-900 px-1 py-0.5 rounded">.env</code> file in the project root.
          </p>
          <p>
            3. Restart the backend service. Never hardcode keys in frontend code or commit credentials to Git.
          </p>
        </div>
      </div>

      {/* Automated Daily Search Configuration */}
      <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800 pb-2">
          <Clock className="w-4 h-4 text-amber-400" />
          Windows Scheduled Task Automation
        </h4>


        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-1">Daily Automated Search Time</label>
            <div className="flex items-center space-x-2">
              <input
                type="number"
                min={0}
                max={23}
                value={autoHour}
                onChange={(e) => setAutoHour(Number(e.target.value))}
                className="w-20 bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
              />
              <span className="text-slate-400 font-bold">:</span>
              <input
                type="number"
                min={0}
                max={59}
                value={autoMinute}
                onChange={(e) => setAutoMinute(Number(e.target.value))}
                className="w-20 bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
              />
              <span className="text-slate-400 text-xs">24-hour clock (e.g., 08:00 AM)</span>
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Schedule Activation</label>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Your Windows computer can run headless daily searches without keeping the dashboard open.
              Run this command in PowerShell once to register the Windows Scheduled Task:
            </p>
            <div className="mt-1.5 p-2 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-cyan-300 select-all">
              powershell -ExecutionPolicy Bypass -File scripts\setup_windows_scheduler.ps1 -Time &quot;08:00&quot;
            </div>
          </div>
        </div>
      </div>
    </form>
  );
};
