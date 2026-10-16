"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  ExternalLink,
  Bookmark,
  CheckCircle2,
  AlertCircle,
  MapPin,
  Building2,
  Briefcase,
  GraduationCap,
  Sparkles,
  ShieldCheck,
  Globe2,
  Calendar,
  FileText,
  Save,
  RefreshCw,
  TrendingUp,
  ThumbsUp,
  AlertTriangle,
  Quote,
  Zap,
  Info
} from "lucide-react";
import { Job, AIJobAssessment } from "../types";
import { analyzeJobWithAi, getJobAiAssessment } from "../lib/api";

interface JobModalProps {
  job: Job | null;
  onClose: () => void;
  onToggleSave: (jobId: number, currentSaved: boolean) => void;
  onStatusChange: (jobId: number, status: string, notes?: string) => void;
}

export const JobModal: React.FC<JobModalProps> = ({
  job,
  onClose,
  onToggleSave,
  onStatusChange
}) => {
  if (!job) return null;

  const [notes, setNotes] = useState(job.application_notes || "");
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Phase 2 AI Assessment state
  const [aiAssessment, setAiAssessment] = useState<AIJobAssessment | null>(job.ai_assessment || null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    setNotes(job.application_notes || "");
    setAiAssessment(job.ai_assessment || null);
    setAiError(null);

    // Fetch existing AI assessment if not already on job object
    if (!job.ai_assessment) {
      getJobAiAssessment(job.id)
        .then((res) => {
          if (res) setAiAssessment(res);
        })
        .catch(() => {});
    }
  }, [job]);

  const handleRunAiAnalysis = async (force: boolean = false) => {
    setIsAnalyzing(true);
    setAiError(null);
    try {
      const assessment = await analyzeJobWithAi(job.id, force);
      setAiAssessment(assessment);
    } catch (err: any) {
      setAiError(err.message || "Failed to analyze job with AI.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getScoreBadge = (score: number) => {
    if (score >= 85) return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    if (score >= 75) return "bg-blue-500/20 text-blue-300 border-blue-500/30";
    if (score >= 60) return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    return "bg-slate-500/20 text-slate-300 border-slate-500/30";
  };

  const getPriorityBadge = (priority: string) => {
    if (priority === "High") return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    if (priority === "Medium") return "bg-blue-500/20 text-blue-300 border-blue-500/30";
    return "bg-slate-500/20 text-slate-300 border-slate-500/30";
  };

  const handleSaveNotes = async () => {
    setIsSavingNotes(true);
    await onStatusChange(job.id, job.application_status, notes);
    setIsSavingNotes(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto animate-fadeIn">
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800/80 bg-slate-900/95 sticky top-0 z-10 flex items-start justify-between">
          <div className="space-y-1.5 max-w-[85%]">
            <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
              <span className={`text-xs px-2.5 py-0.5 rounded-full border font-bold ${getScoreBadge(aiAssessment?.match_score ?? job.match_score)}`}>
                {aiAssessment ? `AI: ${aiAssessment.match_score}/100` : `Rules: ${job.match_score}/100`}
              </span>

              {aiAssessment && (
                <span className={`text-xs px-2.5 py-0.5 rounded-full border font-bold ${getPriorityBadge(aiAssessment.application_priority)}`}>
                  Priority: {aiAssessment.application_priority}
                </span>
              )}

              <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                {job.source.toUpperCase()}
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800/80 text-cyan-300 border border-cyan-500/20 font-medium">
                {job.employment_type}
              </span>
              {job.sponsorship_status !== "Unknown" && (
                <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${
                  job.sponsorship_status === "Confirmed"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                }`}>
                  Sponsorship: {job.sponsorship_status}
                </span>
              )}
            </div>

            <h3 className="text-xl font-bold text-white tracking-tight pt-1">
              {job.title}
            </h3>

            <div className="flex items-center space-x-4 text-xs text-slate-400 pt-0.5">
              <span className="flex items-center gap-1 font-semibold text-slate-200">
                <Building2 className="w-3.5 h-3.5 text-blue-400" />
                {job.company}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                {job.location} {job.country && job.country !== "Unknown" ? `(${job.country})` : ""}
              </span>
              {job.posted_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  Posted {new Date(job.posted_date).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          
          {/* AI Career Matching Assessment Card */}
          <div className="p-5 rounded-2xl bg-gradient-to-b from-slate-900 to-indigo-950/40 border border-indigo-500/30 shadow-lg space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-indigo-500/20 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    AI Career Match &amp; Fit Analysis
                    {aiAssessment && (
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                        aiAssessment.engine_used === "ai"
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                          : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                      }`}>
                        {aiAssessment.engine_used === "ai" ? "Gemini AI" : "Local Rules Fallback"}
                      </span>
                    )}
                  </h4>
                  <p className="text-xs text-slate-400">
                    Deep evaluation against Raghunath Reddy's verified master profile
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleRunAiAnalysis(Boolean(aiAssessment))}
                  disabled={isAnalyzing}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-indigo-900/30 transition"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Evaluating Profile...</span>
                    </>
                  ) : aiAssessment ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Reanalyze Job</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-3.5 h-3.5" />
                      <span>AI Analyze Job</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {aiError && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{aiError}</span>
              </div>
            )}

            {aiAssessment ? (
              <div className="space-y-4">
                {/* Career Growth Opportunity Progress */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <TrendingUp className="w-4 h-4 text-cyan-400" />
                      Career Opportunity &amp; Progression Score (Separately Evaluated)
                    </span>
                    <span className="font-bold text-cyan-300 font-mono text-sm">
                      {aiAssessment.career_growth_score}/100
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, aiAssessment.career_growth_score))}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed pt-1">
                    {aiAssessment.career_growth_summary}
                  </p>
                </div>

                {/* Reasons to Apply vs Reconsider Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Reasons to Apply */}
                  <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
                    <div className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                      <ThumbsUp className="w-4 h-4" /> Reasons to Apply
                    </div>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {aiAssessment.reasons_to_apply.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Reasons to Reconsider */}
                  <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
                    <div className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" /> Reasons to Reconsider
                    </div>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {aiAssessment.reasons_to_reconsider.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* International Eligibility & Visa */}
                {aiAssessment.visa_relocation_considerations && (
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                    <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                      <Globe2 className="w-3.5 h-3.5 text-indigo-400" />
                      International Eligibility &amp; Visa Relocation
                    </div>
                    <p className="text-slate-300 leading-relaxed">
                      {aiAssessment.visa_relocation_considerations}
                    </p>
                  </div>
                )}

                {/* Skills & Missing Requirements */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {aiAssessment.matching_skills.length > 0 && (
                    <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800">
                      <p className="text-xs font-semibold text-emerald-400 mb-2 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Verified Matching Skills
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {aiAssessment.matching_skills.map((s, idx) => (
                          <span key={idx} className="text-[11px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {aiAssessment.missing_requirements.length > 0 && (
                    <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800">
                      <p className="text-xs font-semibold text-amber-400 mb-2 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Skill Gaps or Unstated Requirements
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {aiAssessment.missing_requirements.map((m, idx) => (
                          <span key={idx} className="text-[11px] bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded">
                            {m}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Evidence References */}
                {aiAssessment.evidence_references && Object.keys(aiAssessment.evidence_references).length > 0 && (
                  <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-1.5">
                    <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                      <Quote className="w-3.5 h-3.5 text-slate-500" />
                      Direct Evidence from Vacancy Description
                    </div>
                    <div className="text-[11px] font-mono text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                      {JSON.stringify(aiAssessment.evidence_references, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-center space-y-2">
                <p className="text-xs text-slate-400">
                  Click <strong>AI Analyze Job</strong> above to run deep suitability matching using Google Gemini.
                </p>
                <p className="text-[11px] text-slate-500">
                  Cached assessments are saved locally by SHA-256 hash. If Gemini is unavailable or rate limited, local rules scoring activates automatically.
                </p>
              </div>
            )}
          </div>

          {/* Application Tracker & Notes Box */}
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                Application Pipeline &amp; Personal Notes
              </span>

              <div className="flex items-center space-x-2">
                <label className="text-xs text-slate-400">Status:</label>
                <select
                  value={job.application_status}
                  onChange={(e) => onStatusChange(job.id, e.target.value, notes)}
                  className="bg-slate-800 text-xs font-medium text-white px-2.5 py-1 rounded border border-slate-700 focus:outline-none focus:border-blue-500"
                >
                  <option value="Discovered">Discovered</option>
                  <option value="Saved">Saved</option>
                  <option value="Interested">Interested</option>
                  <option value="Ready to Apply">Ready to Apply</option>
                  <option value="Applied">Applied</option>
                  <option value="Interview">Interview</option>
                  <option value="Offer">Offer</option>
                  <option value="Rejected">Rejected</option>
                  <option value="Closed">Closed</option>
                </select>
              </div>
            </div>

            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add interview notes, tailored CV focus areas, referral contacts, or thoughts on this role..."
              rows={2}
              className="w-full text-xs bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />

            <div className="flex justify-end items-center gap-2">
              {saveSuccess && <span className="text-xs text-emerald-400 font-medium">Notes saved!</span>}
              <button
                onClick={handleSaveNotes}
                disabled={isSavingNotes}
                className="inline-flex items-center space-x-1.5 text-xs font-medium px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Notes</span>
              </button>
            </div>
          </div>

          {/* Full Job Description */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Briefcase className="w-4 h-4 text-slate-400" />
              Advertised Job Description
            </h4>
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 text-xs text-slate-300 leading-relaxed whitespace-pre-line font-mono select-text">
              {job.description}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/95 sticky bottom-0 flex items-center justify-between">
          <button
            onClick={() => onToggleSave(job.id, job.is_saved)}
            className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold border transition-all ${
              job.is_saved
                ? "bg-blue-600/20 text-blue-300 border-blue-500/40 hover:bg-blue-600/30"
                : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${job.is_saved ? "fill-blue-400 text-blue-400" : ""}`} />
            <span>{job.is_saved ? "Saved in Opportunities" : "Save Job"}</span>
          </button>

          <div className="flex items-center space-x-2">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-5 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-md shadow-blue-500/20 transition-all"
            >
              <span>Apply on Original Career Page</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
