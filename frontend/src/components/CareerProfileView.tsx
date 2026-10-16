"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  UserProfile,
  MasterCV,
  EmploymentRecord
} from "../types";
import {
  getUserProfile,
  updateUserProfile,
  uploadMasterCv,
  setUserAiConsent,
  getCvDownloadUrl
} from "../lib/api";
import {
  User,
  Briefcase,
  GraduationCap,
  Award,
  ShieldCheck,
  UploadCloud,
  FileText,
  Download,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Info
} from "lucide-react";

export const CareerProfileView: React.FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  // Editable Form State
  const [name, setName] = useState("");
  const [currentRole, setCurrentRole] = useState("");
  const [currentCompany, setCurrentCompany] = useState("");
  const [location, setLocation] = useState("");
  const [experienceYears, setExperienceYears] = useState(18);
  const [summary, setSummary] = useState("");
  const [employmentHistory, setEmploymentHistory] = useState<EmploymentRecord[]>([]);
  const [qualifications, setQualifications] = useState<string[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [achievements, setAchievements] = useState<string[]>([]);
  const [targetCountries, setTargetCountries] = useState<string[]>([]);
  const [targetTitles, setTargetTitles] = useState<string[]>([]);
  const [consentGiven, setConsentGiven] = useState(false);

  // New item inputs
  const [newQualification, setNewQualification] = useState("");
  const [newSkill, setNewSkill] = useState("");
  const [newAchievement, setNewAchievement] = useState("");
  const [newCountry, setNewCountry] = useState("");
  const [newTitle, setNewTitle] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const data = await getUserProfile();
      if (!data) throw new Error("No profile data received from backend.");
      setProfile(data);
      setName(data.name || "");
      setCurrentRole(data.current_role || "");
      setCurrentCompany(data.current_company || "");
      setLocation(data.location || "");
      setExperienceYears(typeof data.experience_years === "number" ? data.experience_years : 18);
      setSummary(data.summary || "");
      setEmploymentHistory(Array.isArray(data.employment_history) ? data.employment_history : []);
      setQualifications(Array.isArray(data.qualifications) ? data.qualifications : []);
      setSkills(Array.isArray(data.skills) ? data.skills : []);
      setAchievements(Array.isArray(data.achievements) ? data.achievements : []);
      setTargetCountries(Array.isArray(data.target_countries) ? data.target_countries : []);
      setTargetTitles(Array.isArray(data.target_titles) ? data.target_titles : []);
      setConsentGiven(Boolean(data.consent_given_for_ai));
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to load profile." });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = [".pdf", ".docx"];
    const dotIndex = (file.name || "").lastIndexOf(".");
    const extension = dotIndex !== -1 ? file.name.substring(dotIndex).toLowerCase() : "";
    if (!allowed.includes(extension)) {
      setFeedback({ type: "error", text: "Please upload a valid PDF (.pdf) or Word document (.docx)." });
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setIsUploading(true);
    setFeedback({ type: "info", text: `Extracting text from ${file.name} using PyMuPDF / python-docx...` });

    try {
      const res = await uploadMasterCv(file);
      // Dual-compatibility: support nested { profile: UserProfile, ... } and direct flat UserProfile
      const prof: UserProfile = (res && typeof res === "object" && "profile" in res && res.profile)
        ? res.profile
        : (res as unknown as UserProfile);

      if (!prof) {
        throw new Error("CV upload succeeded but no profile data was returned.");
      }

      setProfile(prof);
      setName(prof.name || "");
      setCurrentRole(prof.current_role || "");
      setCurrentCompany(prof.current_company || "");
      setLocation(prof.location || "");
      setExperienceYears(typeof prof.experience_years === "number" ? prof.experience_years : 18);
      setSummary(prof.summary || "");
      setEmploymentHistory(Array.isArray(prof.employment_history) ? prof.employment_history : []);
      setQualifications(Array.isArray(prof.qualifications) ? prof.qualifications : []);
      setSkills(Array.isArray(prof.skills) ? prof.skills : []);
      setAchievements(Array.isArray(prof.achievements) ? prof.achievements : []);
      
      const fileName = (res && typeof res === "object" && "filename" in res && res.filename) || file.name;
      setFeedback({
        type: "success",
        text: `CV "${fileName}" parsed successfully! Profile updated with extracted background.`
      });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to upload and parse CV." });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleConsentToggle = async () => {
    const nextVal = !consentGiven;
    try {
      await setUserAiConsent(nextVal);
      setConsentGiven(nextVal);
      setFeedback({
        type: "success",
        text: nextVal
          ? "AI consent enabled: Profile data will be used for Gemini-powered job suitability matching."
          : "AI consent disabled: Matching will use local rules engine only. Zero data sent externally."
      });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to update AI consent." });
    }
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const updated = await updateUserProfile({
        name,
        current_role: currentRole,
        current_company: currentCompany,
        location,
        experience_years: experienceYears,
        summary,
        employment_history: employmentHistory,
        qualifications,
        skills,
        achievements,
        target_countries: targetCountries,
        target_titles: targetTitles
      });
      setProfile(updated);
      setFeedback({ type: "success", text: "Career Profile successfully saved and confirmed!" });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to save profile." });
    } finally {
      setIsSaving(false);
    }
  };

  // Employment helpers
  const handleRoleChange = (index: number, field: keyof EmploymentRecord, value: any) => {
    const copy = [...employmentHistory];
    copy[index] = { ...copy[index], [field]: value };
    setEmploymentHistory(copy);
  };

  const handleAddHighlight = (index: number, highlightText: string) => {
    if (!highlightText.trim()) return;
    const copy = [...employmentHistory];
    const existingHighlights = Array.isArray(copy[index]?.highlights) ? copy[index].highlights : [];
    copy[index] = {
      ...copy[index],
      highlights: [...existingHighlights, highlightText.trim()]
    };
    setEmploymentHistory(copy);
  };

  const handleRemoveHighlight = (roleIndex: number, hlIndex: number) => {
    const copy = [...employmentHistory];
    const existingHighlights = Array.isArray(copy[roleIndex]?.highlights) ? copy[roleIndex].highlights : [];
    copy[roleIndex] = {
      ...copy[roleIndex],
      highlights: existingHighlights.filter((_, i) => i !== hlIndex)
    };
    setEmploymentHistory(copy);
  };

  const handleAddRole = () => {
    setEmploymentHistory([
      {
        company: "New Organization",
        role: "Leadership Role",
        location: "India",
        highlights: ["Leadership responsibility and HSE assurance"],
        source: "user_confirmed"
      },
      ...employmentHistory
    ]);
  };

  const handleRemoveRole = (index: number) => {
    setEmploymentHistory(employmentHistory.filter((_, i) => i !== index));
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] space-y-4">
        <RefreshCw className="w-10 h-10 text-emerald-500 animate-spin" />
        <p className="text-slate-400 font-medium">Loading your verified career profile...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      {/* Top Banner & Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 p-6 rounded-2xl border border-slate-700/60 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">My Career Profile</h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              <ShieldCheck className="w-3.5 h-3.5" /> Phase 2 AI Verified
            </span>
            {consentGiven ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <Sparkles className="w-3 h-3 text-indigo-400" /> Gemini Enabled
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                <Lock className="w-3 h-3 text-amber-400" /> Local Rules Only
              </span>
            )}
          </div>
          <p className="text-slate-400 text-sm">
            Primary source of professional truth for automated AI matching against real HSE leadership vacancies.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadProfile}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium border border-slate-600/60 transition"
          >
            <RefreshCw className="w-4 h-4" /> Reset
          </button>
          <button
            onClick={handleSaveProfile}
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-900/30 transition disabled:opacity-50"
          >
            {isSaving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" /> Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" /> Save & Confirm Profile
              </>
            )}
          </button>
        </div>
      </div>

      {/* Feedback Alert */}
      {feedback && (
        <div
          className={`flex items-start gap-3 p-4 rounded-xl border transition-all ${
            feedback.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : feedback.type === "error"
              ? "bg-rose-950/40 border-rose-500/40 text-rose-300"
              : "bg-blue-950/40 border-blue-500/40 text-blue-300"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          ) : feedback.type === "error" ? (
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          ) : (
            <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          )}
          <div className="text-sm flex-1 font-medium">{feedback.text}</div>
          <button
            onClick={() => setFeedback(null)}
            className="text-xs opacity-70 hover:opacity-100 transition ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Master CV & Privacy Consent Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Master CV Card */}
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Master CV Document</h3>
                  <p className="text-xs text-slate-400">Extracts text via PyMuPDF (PDF) & python-docx (DOCX)</p>
                </div>
              </div>
              {profile?.cv ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  CV Stored Locally
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
                  Using Baseline Facts
                </span>
              )}
            </div>

            {profile?.cv ? (
              <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 mb-5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-sm font-semibold text-slate-200 truncate">{profile.cv.filename}</span>
                  </div>
                  <span className="text-xs font-mono text-slate-400 uppercase bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
                    {profile.cv.file_type}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                  <span>Size: {(profile.cv.file_size / 1024).toFixed(1)} KB</span>
                  <span>Uploaded: {new Date(profile.cv.extracted_at).toLocaleDateString()}</span>
                </div>

                <div className="pt-2 flex gap-2">
                  <a
                    href={getCvDownloadUrl()}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-700/70 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-600 transition"
                  >
                    <Download className="w-3.5 h-3.5" /> Download Master CV
                  </a>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 mb-5 text-xs text-slate-400">
                No external document uploaded yet. The profile is currently populated with your verified career baseline (Raghunath Reddy, Global SHE & Security Manager).
              </div>
            )}
          </div>

          <div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.docx"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-emerald-500/40 text-slate-200 text-sm font-medium transition shadow-sm group"
            >
              {isUploading ? (
                <>
                  <RefreshCw className="w-4 h-4 text-emerald-400 animate-spin" />
                  <span>Parsing CV Document...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                  <span>{profile?.cv ? "Replace Master CV (PDF or DOCX)" : "Upload Master CV (PDF or DOCX)"}</span>
                </>
              )}
            </button>
            <p className="text-[11px] text-slate-500 mt-2 text-center">
              Original CV files remain strictly on your local PC (`data/cv/`) and are never sent externally.
            </p>
          </div>
        </div>

        {/* Privacy & AI Consent Card */}
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${
                  consentGiven
                    ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"
                    : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                }`}>
                  <Lock className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Privacy & AI Consent</h3>
                  <p className="text-xs text-slate-400">Mandatory privacy compliance check</p>
                </div>
              </div>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                consentGiven
                  ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                  : "bg-amber-500/20 text-amber-300 border-amber-500/30"
              }`}>
                {consentGiven ? "AI Enabled" : "Consent Required"}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-300 space-y-2 mb-5">
              <p>
                <strong className="text-white">Strict Local Privacy Rule:</strong> Your raw CV file is NEVER sent to Google Gemini or external services.
              </p>
              <p className="text-slate-400">
                When you grant consent below, only structured professional criteria (skills, years of experience, qualification titles) are sent over encrypted HTTPS to the official Google Gemini API for deep vacancy matching.
              </p>
              <p className="text-slate-400">
                If consent is off, or if your daily quota is reached, the local rules-based engine runs automatically at ₹0 cost.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/60 border border-slate-700/60">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-white">AI Suitability Analysis</div>
              <div className="text-xs text-slate-400">
                {consentGiven ? "Gemini 2.5 Flash active for deep job evaluations" : "Local heuristic rules matching active"}
              </div>
            </div>
            <button
              onClick={handleConsentToggle}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                consentGiven ? "bg-indigo-600" : "bg-slate-700"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  consentGiven ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Editable Profile Sections */}
      <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md space-y-6">
        <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Verified Candidate Overview</h2>
          </div>
          <span className="text-xs text-slate-400">Editable fields saved to local database</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">Candidate Full Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-200 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">Current Role</label>
            <input
              type="text"
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-200 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">Current Organization</label>
            <input
              type="text"
              value={currentCompany}
              onChange={(e) => setCurrentCompany(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-200 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">Base Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-200 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">Total HSE Experience (Years)</label>
            <input
              type="number"
              value={experienceYears}
              onChange={(e) => setExperienceYears(parseInt(e.target.value) || 0)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-200 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1.5">Executive Summary</label>
          <textarea
            rows={3}
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/70 border border-slate-700 text-slate-200 text-sm focus:border-emerald-500 focus:outline-none resize-y"
          />
        </div>
      </div>

      {/* Employment History */}
      <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md space-y-6">
        <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Employment History & Leadership Roles</h2>
          </div>
          <button
            onClick={handleAddRole}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition"
          >
            <Plus className="w-3.5 h-3.5" /> Add Role
          </button>
        </div>

        <div className="space-y-4">
          {(employmentHistory || []).map((role, idx) => (
            <div
              key={idx}
              className="p-5 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-3 relative group"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 flex-1">
                  <input
                    type="text"
                    value={role?.company || ""}
                    placeholder="Company Name"
                    onChange={(e) => handleRoleChange(idx, "company", e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700 text-white font-semibold text-sm focus:outline-none"
                  />
                  <input
                    type="text"
                    value={role?.role || ""}
                    placeholder="Role Title"
                    onChange={(e) => handleRoleChange(idx, "role", e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700 text-slate-200 text-sm focus:outline-none"
                  />
                  <input
                    type="text"
                    value={role?.location || ""}
                    placeholder="Location"
                    onChange={(e) => handleRoleChange(idx, "location", e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700 text-slate-300 text-sm focus:outline-none"
                  />
                </div>
                <button
                  onClick={() => handleRemoveRole(idx)}
                  className="text-slate-500 hover:text-rose-400 transition p-1"
                  title="Remove Role"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Highlights */}
              <div className="space-y-1.5 pt-1">
                <div className="text-xs font-semibold text-slate-400">Responsibilities & Highlights:</div>
                <div className="space-y-1.5">
                  {((role && role.highlights) || []).map((hl, hIdx) => (
                    <div key={hIdx} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                      <span className="text-xs text-slate-300 flex-1">{hl}</span>
                      <button
                        onClick={() => handleRemoveHighlight(idx, hIdx)}
                        className="text-slate-500 hover:text-rose-400 transition text-xs"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
                <div className="pt-2">
                  <input
                    type="text"
                    placeholder="Add bullet highlight and press Enter..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddHighlight(idx, (e.target as HTMLInputElement).value);
                        (e.target as HTMLInputElement).value = "";
                      }
                    }}
                    className="w-full px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-700 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Qualifications, Skills, Achievements Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Qualifications */}
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-3">
              <GraduationCap className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-bold text-white">Qualifications</h3>
            </div>
            <div className="space-y-2">
              {(qualifications || []).map((q, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs text-slate-200">
                  <span className="font-medium">{q}</span>
                  <button
                    onClick={() => setQualifications(qualifications.filter((_, i) => i !== idx))}
                    className="text-slate-500 hover:text-rose-400 text-sm ml-2"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add qualification..."
                value={newQualification}
                onChange={(e) => setNewQualification(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newQualification.trim()) {
                    setQualifications([...qualifications, newQualification.trim()]);
                    setNewQualification("");
                  }
                }}
                className="flex-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => {
                  if (newQualification.trim()) {
                    setQualifications([...qualifications, newQualification.trim()]);
                    setNewQualification("");
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
              >
                Add
              </button>
            </div>
          </div>
        </div>

        {/* Skills */}
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-3">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-bold text-white">Core HSE Skills</h3>
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-[220px] overflow-y-auto pr-1">
              {(skills || []).map((s, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 font-medium"
                >
                  {s}
                  <button
                    onClick={() => setSkills(skills.filter((_, i) => i !== idx))}
                    className="text-slate-500 hover:text-rose-400 font-bold"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add skill..."
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newSkill.trim()) {
                    setSkills([...skills, newSkill.trim()]);
                    setNewSkill("");
                  }
                }}
                className="flex-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => {
                  if (newSkill.trim()) {
                    setSkills([...skills, newSkill.trim()]);
                    setNewSkill("");
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
              >
                Add
              </button>
            </div>
          </div>
        </div>

        {/* Achievements */}
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-md flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-3">
              <Award className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-bold text-white">Key Achievements</h3>
            </div>
            <div className="space-y-2">
              {(achievements || []).map((ach, idx) => (
                <div key={idx} className="flex items-start justify-between p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs text-slate-200">
                  <span className="font-medium leading-relaxed">{ach}</span>
                  <button
                    onClick={() => setAchievements(achievements.filter((_, i) => i !== idx))}
                    className="text-slate-500 hover:text-rose-400 text-sm ml-2 shrink-0"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add achievement..."
                value={newAchievement}
                onChange={(e) => setNewAchievement(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newAchievement.trim()) {
                    setAchievements([...achievements, newAchievement.trim()]);
                    setNewAchievement("");
                  }
                }}
                className="flex-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => {
                  if (newAchievement.trim()) {
                    setAchievements([...achievements, newAchievement.trim()]);
                    setNewAchievement("");
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
