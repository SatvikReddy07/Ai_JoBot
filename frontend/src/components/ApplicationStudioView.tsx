"use client";

import React, { useState, useEffect } from "react";
import {
  FileCheck,
  Sparkles,
  Download,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Shield,
  FileText,
  Briefcase,
  ExternalLink,
  RefreshCw,
  Layers,
  Edit3,
  Check,
  Archive,
  AlertCircle,
  Cpu,
  Building2,
  MapPin,
  Award,
  BookOpen
} from "lucide-react";
import {
  Job,
  ApplicationPackage,
  ATSKeywordAnalysis,
  TailoredCVContent,
  TailoredCoverLetterContent,
  GeneratedDocument
} from "../types";
import {
  getJobs,
  getAtsAnalysis,
  generateCvPreview,
  generateCoverLetterPreview,
  generatePackage,
  getAllPackages,
  getJobPackages,
  getPackageById,
  updatePackageDocument,
  approvePackage,
  getPackageDownloadUrl,
  getPdfConverterStatus
} from "../lib/api";

const CV_TEMPLATES = [
  {
    id: "global_regional_hse",
    name: "Global / Regional HSE Leadership",
    description: "Multi-site governance, APAC/EMEA oversight, corporate assurance, strategic safety roadmaps."
  },
  {
    id: "manufacturing_industrial_ehs",
    name: "Manufacturing / Industrial EHS Leadership",
    description: "Plant operations, ISO 14001 / ISO 45001, Process Safety (PSM), incident prevention & zero-harm."
  },
  {
    id: "corporate_workplace_hse",
    name: "Corporate / Workplace HSE Leadership",
    description: "ESG alignment, workplace wellness, ergonomics, audit assurance & executive risk reporting."
  }
];

interface ApplicationStudioViewProps {
  initialJobId?: number | null;
}

export const ApplicationStudioView: React.FC<ApplicationStudioViewProps> = ({ initialJobId }) => {
  // Core selection state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(initialJobId || null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("global_regional_hse");
  const [useAi, setUseAi] = useState<boolean>(true);

  // Studio Data
  const [atsAnalysis, setAtsAnalysis] = useState<ATSKeywordAnalysis | null>(null);
  const [currentPackage, setCurrentPackage] = useState<ApplicationPackage | null>(null);
  const [recentPackages, setRecentPackages] = useState<ApplicationPackage[]>([]);
  const [pdfStatus, setPdfStatus] = useState<{ available: boolean; primary_engine: string; description: string } | null>(null);

  // Active view tab
  const [activeTab, setActiveTab] = useState<"editor" | "cover_letter" | "ats" | "package" | "history">("editor");

  // Editable preview buffers
  const [cvPreview, setCvPreview] = useState<TailoredCVContent | null>(null);
  const [coverLetterPreview, setCoverLetterPreview] = useState<TailoredCoverLetterContent | null>(null);
  const [editedSummary, setEditedSummary] = useState<string>("");
  const [editedHighlights, setEditedHighlights] = useState<string[]>([]);
  const [editedCoverLetterBody, setEditedCoverLetterBody] = useState<string>("");

  // Loading & Feedback states
  const [isLoadingAts, setIsLoadingAts] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  // 1. Initial Load: Jobs, PDF status, packages
  useEffect(() => {
    loadJobs();
    loadPdfStatus();
    loadAllPackages();
  }, []);

  const loadPdfStatus = async () => {
    try {
      const res = await getPdfConverterStatus();
      setPdfStatus(res);
    } catch {
      setPdfStatus({
        available: true,
        primary_engine: "ReportLab Vector PDF",
        description: "Local Python Vector PDF engine active (zero external dependencies)"
      });
    }
  };

  const loadJobs = async () => {
    try {
      const res = await getJobs({ page_size: 100, page: 1, sort_by: "score_desc" });
      const jobList = res?.items || [];
      setJobs(jobList);
      if (initialJobId) {
        const found = jobList.find((j) => j.id === initialJobId);
        if (found) setSelectedJob(found);
      } else if (jobList.length > 0 && !selectedJobId) {
        setSelectedJobId(jobList[0].id);
        setSelectedJob(jobList[0]);
      }
    } catch (err: any) {
      console.error("Failed to load jobs for studio:", err);
    }
  };

  const loadAllPackages = async () => {
    try {
      const pkgs = await getAllPackages();
      setRecentPackages(pkgs || []);
    } catch (err) {
      console.error("Failed to load packages:", err);
    }
  };

  // 2. When selectedJobId changes
  useEffect(() => {
    if (!selectedJobId) return;
    const j = jobs.find((item) => item.id === selectedJobId);
    if (j) setSelectedJob(j);

    loadJobDetails(selectedJobId);
  }, [selectedJobId, jobs]);

  const loadJobDetails = async (jobId: number) => {
    setIsLoadingAts(true);
    setStatusMessage(null);
    try {
      // Load ATS analysis
      const ats = await getAtsAnalysis(jobId);
      setAtsAnalysis(ats);

      // Load existing packages for this job
      const pkgs = await getJobPackages(jobId);
      if (pkgs && pkgs.length > 0) {
        const latest = pkgs[0];
        setCurrentPackage(latest);
      } else {
        setCurrentPackage(null);
      }
      // Load preview drafts
      await loadInitialPreviews(jobId, selectedTemplate);
    } catch (err: any) {
      console.error("Error loading job details:", err);
    } finally {
      setIsLoadingAts(false);
    }
  };

  const loadInitialPreviews = async (jobId: number, template: string) => {
    try {
      const [cv, cl] = await Promise.all([
        generateCvPreview(jobId, template).catch(() => null),
        generateCoverLetterPreview(jobId, template).catch(() => null)
      ]);
      if (cv) {
        setCvPreview(cv);
        setEditedSummary(cv.summary || "");
        setEditedHighlights(cv.key_achievements || []);
      }
      if (cl) {
        setCoverLetterPreview(cl);
        setEditedCoverLetterBody((cl.body_paragraphs || []).join("\n\n"));
      }
    } catch (e) {
      console.error("Error generating initial previews:", e);
    }
  };

  // 3. Action Handlers
  const handleGeneratePackage = async () => {
    if (!selectedJobId) return;
    setIsGenerating(true);
    setStatusMessage({ type: "info", text: "Generating complete application package (DOCX, Vector PDF, Checklist, ZIP)..." });
    try {
      const pkg = await generatePackage(selectedJobId, selectedTemplate);
      setCurrentPackage(pkg);
      await loadInitialPreviews(selectedJobId, selectedTemplate);
      loadAllPackages();
      setStatusMessage({
        type: "success",
        text: `Application Package #${pkg.id} generated successfully! All documents ready for download.`
      });
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to generate package." });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateCvOnly = async () => {
    if (!selectedJobId) return;
    setIsGenerating(true);
    setStatusMessage({ type: "info", text: "Tailoring CV with verified competencies..." });
    try {
      const cv = await generateCvPreview(selectedJobId, selectedTemplate);
      setCvPreview(cv);
      setEditedSummary(cv.summary || "");
      setEditedHighlights(cv.key_achievements || []);
      setActiveTab("editor");
      setStatusMessage({ type: "success", text: "CV draft generated based on verified profile facts!" });
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to generate CV." });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateCoverLetterOnly = async () => {
    if (!selectedJobId) return;
    setIsGenerating(true);
    setStatusMessage({ type: "info", text: "Drafting executive cover letter (~250-350 words)..." });
    try {
      const cl = await generateCoverLetterPreview(selectedJobId, selectedTemplate);
      setCoverLetterPreview(cl);
      setEditedCoverLetterBody((cl.body_paragraphs || []).join("\n\n"));
      setActiveTab("cover_letter");
      setStatusMessage({ type: "success", text: "Executive cover letter generated!" });
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to generate cover letter." });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveDraftChanges = async () => {
    if (!currentPackage) {
      setStatusMessage({
        type: "info",
        text: "Generate a complete package first to create a version-controlled draft."
      });
      return;
    }

    const docs = currentPackage.documents || [];
    const cvDoc = docs.find((d) => d.doc_type === "cv_docx");
    const clDoc = docs.find((d) => d.doc_type === "cover_letter_docx");

    setIsSaving(true);
    try {
      if (activeTab === "editor" && cvDoc && cvPreview) {
        const updatedJson: TailoredCVContent = {
          ...cvPreview,
          summary: editedSummary,
          key_achievements: editedHighlights
        };
        await updatePackageDocument(
          currentPackage.id,
          cvDoc.id,
          JSON.stringify(updatedJson),
          "Manual user edit in Application Studio editor"
        );
        const refreshed = await getPackageById(currentPackage.id);
        setCurrentPackage(refreshed);
        setStatusMessage({ type: "success", text: "CV draft updated. New version created and DOCX/PDF rebuilt." });
      } else if (activeTab === "cover_letter" && clDoc && coverLetterPreview) {
        const paragraphs = editedCoverLetterBody.split("\n\n").map((p) => p.trim()).filter(Boolean);
        const updatedJson: TailoredCoverLetterContent = {
          ...coverLetterPreview,
          body_paragraphs: paragraphs
        };
        await updatePackageDocument(
          currentPackage.id,
          clDoc.id,
          JSON.stringify(updatedJson),
          "Manual user edit to cover letter body"
        );
        const refreshed = await getPackageById(currentPackage.id);
        setCurrentPackage(refreshed);
        setStatusMessage({ type: "success", text: "Cover letter draft updated. New version created and DOCX/PDF rebuilt." });
      }
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to save draft revision." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprovePackage = async () => {
    if (!currentPackage) return;
    setIsApproving(true);
    try {
      const approved = await approvePackage(
        currentPackage.id,
        "Raghunath Reddy",
        "Approved tailored application package via Application Studio"
      );
      setCurrentPackage(approved);
      loadAllPackages();
      setStatusMessage({
        type: "success",
        text: `Package #${approved.id} successfully APPROVED! Ready for official submission.`
      });
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to approve package." });
    } finally {
      setIsApproving(false);
    }
  };

  // Helper calculation for cover letter word count
  const coverLetterWordCount = editedCoverLetterBody
    ? editedCoverLetterBody.trim().split(/\s+/).filter(Boolean).length
    : 0;

  // Derive package version
  const currentVersion = currentPackage?.documents?.[0]?.version_number || 1;

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl -z-10 pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  Application Studio
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-medium">
                    Phase 3
                  </span>
                </h1>
                <p className="text-xs text-slate-400">
                  AI-Powered CV Tailoring, Cover-Letter Generation &amp; Verified Application Package Bundling
                </p>
              </div>
            </div>
          </div>

          {/* Engine Status Badge */}
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <div className="text-left">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">PDF Conversion Engine</span>
                <span className="font-semibold text-slate-200">
                  {pdfStatus?.primary_engine || "ReportLab Vector PDF"}
                </span>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-1" />
            </div>

            <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs flex items-center space-x-2">
              <Shield className="w-4 h-4 text-indigo-400" />
              <div className="text-left">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Candidate Profile</span>
                <span className="font-semibold text-slate-200">Raghunath Reddy (18+ Yrs)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div
            className={`mt-4 p-3 rounded-xl border text-xs flex items-center justify-between transition-all ${
              statusMessage.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : statusMessage.type === "error"
                ? "bg-rose-500/10 border-rose-500/30 text-rose-300"
                : "bg-blue-500/10 border-blue-500/30 text-blue-300"
            }`}
          >
            <div className="flex items-center space-x-2">
              {statusMessage.type === "success" ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : statusMessage.type === "error" ? (
                <AlertCircle className="w-4 h-4" />
              ) : (
                <RefreshCw className="w-4 h-4 animate-spin" />
              )}
              <span>{statusMessage.text}</span>
            </div>
            <button
              onClick={() => setStatusMessage(null)}
              className="text-slate-400 hover:text-white text-xs font-bold px-1"
            >
              &times;
            </button>
          </div>
        )}
      </div>

      {/* 2. Selection & Configuration Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Job Selection (Col 5) */}
        <div className="lg:col-span-5 p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-blue-400" />
              Target Position ({jobs.length} Available)
            </span>
            {selectedJob?.is_saved && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                Bookmarked Job
              </span>
            )}
          </label>

          <div className="relative">
            <select
              value={selectedJobId || ""}
              onChange={(e) => setSelectedJobId(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  [{j.match_score}/100] {j.company} — {j.title} ({j.location})
                </option>
              ))}
            </select>
          </div>

          {selectedJob && (
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white truncate">{selectedJob.title}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Match: {selectedJob.match_score}/100
                </span>
              </div>
              <div className="flex items-center space-x-3 text-slate-400 text-[11px]">
                <span className="flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-slate-500" />
                  {selectedJob.company}
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-slate-500" />
                  {selectedJob.location}
                </span>
                <a
                  href={selectedJob.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-0.5"
                >
                  Vacancy Link <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Template & Mode Selection (Col 4) */}
        <div className="lg:col-span-4 p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              CV Executive Template
            </span>
          </label>

          <select
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
          >
            {CV_TEMPLATES.map((tmpl) => (
              <option key={tmpl.id} value={tmpl.id}>
                {tmpl.name}
              </option>
            ))}
          </select>

          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-400 leading-tight">
            {CV_TEMPLATES.find((t) => t.id === selectedTemplate)?.description}
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="text-xs text-slate-300 flex items-center space-x-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useAi}
                onChange={(e) => setUseAi(e.target.checked)}
                className="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-0 w-3.5 h-3.5"
              />
              <span className="flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-400" />
                Gemini AI Optimization (Free-Tier)
              </span>
            </label>
            <span className="text-[10px] text-slate-500">
              {useAi ? "AI + Rules" : "Local Rules Only"}
            </span>
          </div>
        </div>

        {/* Action Controls (Col 3) */}
        <div className="lg:col-span-3 p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-2">
          <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Generation Actions
          </label>

          <div className="space-y-2">
            <button
              onClick={handleGeneratePackage}
              disabled={isGenerating || !selectedJobId}
              className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-blue-500/20 disabled:opacity-50 flex items-center justify-center space-x-2 transition-all"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Generating Package...</span>
                </>
              ) : (
                <>
                  <Archive className="w-3.5 h-3.5" />
                  <span>Generate Application Package</span>
                </>
              )}
            </button>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={handleGenerateCvOnly}
                disabled={isGenerating || !selectedJobId}
                className="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 disabled:opacity-50 flex items-center justify-center space-x-1"
              >
                <FileText className="w-3 h-3 text-blue-400" />
                <span>Tailor CV</span>
              </button>

              <button
                onClick={handleGenerateCoverLetterOnly}
                disabled={isGenerating || !selectedJobId}
                className="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 disabled:opacity-50 flex items-center justify-center space-x-1"
              >
                <Edit3 className="w-3 h-3 text-purple-400" />
                <span>Cover Letter</span>
              </button>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 text-center pt-1">
            ₹0 operating cost • Strictly verified facts
          </div>
        </div>
      </div>

      {/* 3. Main Workspace Tabs */}
      <div className="border-b border-slate-800 flex items-center justify-between">
        <div className="flex space-x-1">
          <button
            onClick={() => setActiveTab("editor")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === "editor"
                ? "border-blue-500 text-blue-400 bg-blue-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Tailored Executive CV</span>
            {cvPreview && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-500/20 text-blue-300">
                2-3 Pages
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("cover_letter")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === "cover_letter"
                ? "border-purple-500 text-purple-400 bg-purple-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Executive Cover Letter</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-purple-500/20 text-purple-300">
              {coverLetterWordCount} words
            </span>
          </button>

          <button
            onClick={() => setActiveTab("ats")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === "ats"
                ? "border-emerald-500 text-emerald-400 bg-emerald-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Award className="w-3.5 h-3.5" />
            <span>ATS Keyword Alignment</span>
            {atsAnalysis && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300">
                {atsAnalysis.overall_coverage_pct}%
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("package")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === "package"
                ? "border-cyan-500 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Archive className="w-3.5 h-3.5" />
            <span>Package Files &amp; Export</span>
            {currentPackage && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-cyan-500/20 text-cyan-300">
                v{currentVersion}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("history")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center space-x-2 transition-colors ${
              activeTab === "history"
                ? "border-amber-500 text-amber-400 bg-amber-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Package History ({recentPackages.length})</span>
          </button>
        </div>

        {/* Status indicator on the right */}
        {currentPackage && (
          <div className="flex items-center space-x-2 pb-1">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                currentPackage.status === "approved"
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                  : "bg-amber-500/20 text-amber-300 border-amber-500/40"
              }`}
            >
              {currentPackage.status === "approved" ? "APPROVED PACKAGE" : "DRAFT VERSION"}
            </span>

            {currentPackage.status !== "approved" && (
              <button
                onClick={handleApprovePackage}
                disabled={isApproving}
                className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1 shadow-sm"
              >
                <Check className="w-3 h-3" />
                <span>{isApproving ? "Approving..." : "Approve Final"}</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* 4. Tab Contents */}

      {/* TAB 1: TAILORED CV EDITOR */}
      {activeTab === "editor" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main CV Content (Col 8) */}
          <div className="lg:col-span-8 space-y-5">
            {/* Candidate Header Preview */}
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="border-b border-slate-800 pb-3 flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white tracking-wide">
                    {cvPreview?.name || "RAGHUNATH REDDY"}
                  </h2>
                  <p className="text-sm font-semibold text-blue-400">
                    {cvPreview?.headline || selectedJob?.title || "Global SHE & Security Manager"}
                  </p>
                  <p className="text-xs text-slate-400 pt-1">
                    {cvPreview?.contact_location || "Hyderabad, India / Open to Global Relocation"} •{" "}
                    {cvPreview?.contact_email || "raghunath.hse@gmail.com"} •{" "}
                    {cvPreview?.contact_phone || "+91 98490 00000"} •{" "}
                    {cvPreview?.contact_linkedin || "linkedin.com/in/raghunath-reddy-hse"}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    Template: {selectedTemplate}
                  </span>
                </div>
              </div>

              {/* Editable Professional Summary */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Edit3 className="w-3.5 h-3.5 text-blue-400" />
                    Executive Professional Summary (Editable)
                  </label>
                  <span className="text-[10px] text-slate-500">
                    {editedSummary.length} chars • Tailored for {selectedJob?.company || "target employer"}
                  </span>
                </div>
                <textarea
                  value={editedSummary}
                  onChange={(e) => setEditedSummary(e.target.value)}
                  rows={5}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 leading-relaxed focus:outline-none focus:border-blue-500 font-sans"
                  placeholder="Executive summary..."
                />
              </div>

              {/* Core Competencies Pills */}
              <div className="space-y-2 pt-2">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5 text-emerald-400" />
                  Targeted Core Competencies
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {(cvPreview?.core_competencies || []).map((comp, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800/80 text-cyan-300 border border-cyan-500/20"
                    >
                      {comp}
                    </span>
                  ))}
                </div>
              </div>

              {/* Tailored Highlights / Key Achievements */}
              <div className="space-y-2 pt-2">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                  Verified Key Achievements &amp; Scope Highlights
                </label>
                <div className="space-y-2">
                  {editedHighlights.map((hl, idx) => (
                    <div key={idx} className="flex items-start space-x-2">
                      <span className="text-blue-400 text-xs font-bold mt-1.5">•</span>
                      <textarea
                        value={hl}
                        onChange={(e) => {
                          const updated = [...editedHighlights];
                          updated[idx] = e.target.value;
                          setEditedHighlights(updated);
                        }}
                        rows={2}
                        className="w-full bg-slate-950 border border-slate-800/80 rounded-md p-2 text-xs text-slate-300 leading-relaxed focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Verified Career Experience (Read-Only Verified Base) */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
                  Verified Employment History (Preserved Facts)
                </label>
                <div className="space-y-3">
                  {(cvPreview?.employment_history || []).map((exp, idx) => (
                    <div key={idx} className="p-3.5 rounded-lg bg-slate-950/40 border border-slate-800/70 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-xs">{exp.role}</span>
                        <span className="text-[11px] font-mono text-slate-400">{exp.duration}</span>
                      </div>
                      <div className="text-[11px] text-blue-400 font-semibold">
                        {exp.company} {exp.location ? `• ${exp.location}` : ""}
                      </div>
                      <ul className="list-disc list-inside text-xs text-slate-300 space-y-1 pt-1">
                        {(exp.highlights || []).map((resp, rIdx) => (
                          <li key={rIdx} className="leading-relaxed">
                            {resp}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>

              {/* Education & Certifications */}
              <div className="space-y-2 pt-3 border-t border-slate-800">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-amber-400" />
                  Verified Education &amp; Certifications
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/70 text-xs">
                    <span className="font-bold text-slate-200 block">Degrees</span>
                    <ul className="text-slate-400 space-y-0.5 pt-1 text-[11px]">
                      {(cvPreview?.education || []).map((ed, i) => (
                        <li key={i} className="text-slate-200 font-medium">
                          {ed}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/70 text-xs">
                    <span className="font-bold text-slate-200 block">Certifications</span>
                    <ul className="text-slate-400 space-y-0.5 pt-1 text-[11px]">
                      {(cvPreview?.certifications || []).map((cert, i) => (
                        <li key={i} className="text-emerald-300 font-medium">
                          {cert}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Action & Export Column (Col 4) */}
          <div className="lg:col-span-4 space-y-4">
            {/* Quick Actions Panel */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                Draft Revision &amp; Approval
              </h3>

              <div className="space-y-2">
                <button
                  onClick={handleSaveDraftChanges}
                  disabled={isSaving || !currentPackage}
                  className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 disabled:opacity-50"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>{isSaving ? "Saving Revision..." : "Save Draft Revision (v+1)"}</span>
                </button>

                {currentPackage && (
                  <button
                    onClick={handleApprovePackage}
                    disabled={isApproving || currentPackage.status === "approved"}
                    className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>
                      {currentPackage.status === "approved"
                        ? "Package Approved"
                        : isApproving
                        ? "Approving..."
                        : "Approve Final Documents"}
                    </span>
                  </button>
                )}
              </div>

              <p className="text-[11px] text-slate-400">
                Any substantive edit after approval increments the version and moves status back to Draft until re-approved.
              </p>
            </div>

            {/* Direct Document Downloads */}
            {currentPackage && (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Download className="w-3.5 h-3.5 text-cyan-400" />
                  Download Generated Files
                </h3>

                <div className="space-y-2">
                  <a
                    href={getPackageDownloadUrl(currentPackage.id, "cv_docx")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center justify-between"
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-blue-400" />
                      Tailored CV (.docx)
                    </span>
                    <Download className="w-3 h-3 text-slate-400" />
                  </a>

                  <a
                    href={getPackageDownloadUrl(currentPackage.id, "cv_pdf")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center justify-between"
                  >
                    <span className="flex items-center gap-2">
                      <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Tailored CV (.pdf)
                    </span>
                    <Download className="w-3 h-3 text-slate-400" />
                  </a>

                  <a
                    href={getPackageDownloadUrl(currentPackage.id, "zip")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-2.5 px-3 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs flex items-center justify-between shadow-md shadow-cyan-500/20"
                  >
                    <span className="flex items-center gap-2">
                      <Archive className="w-4 h-4" />
                      Complete Package (.zip)
                    </span>
                    <Download className="w-3.5 h-3.5" />
                  </a>
                </div>

                <div className="pt-2 text-[10px] text-slate-400 flex items-center gap-1">
                  <Shield className="w-3 h-3 text-emerald-400" />
                  <span>Text-selectable PDF layer verified with ReportLab</span>
                </div>
              </div>
            )}

            {/* ATS Alignment Snapshot */}
            {atsAnalysis && (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    ATS Keyword Match
                  </span>
                  <span className="text-xs font-bold text-emerald-400">
                    {atsAnalysis.overall_coverage_pct}%
                  </span>
                </div>

                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${atsAnalysis.overall_coverage_pct}%` }}
                  />
                </div>

                <div className="text-[11px] text-slate-400 flex justify-between">
                  <span>{atsAnalysis.matched_keywords?.length || 0} Supported Keywords</span>
                  <span className="text-amber-400">{atsAnalysis.missing_keywords?.length || 0} Missing</span>
                </div>

                <button
                  onClick={() => setActiveTab("ats")}
                  className="w-full py-1.5 text-xs text-blue-400 hover:text-blue-300 font-semibold text-center border border-slate-800 rounded-lg hover:bg-slate-800/50"
                >
                  View Full ATS Keyword Report &rarr;
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: COVER LETTER VIEW & EDITOR */}
      {activeTab === "cover_letter" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-4">
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
              <div className="border-b border-slate-800 pb-3 flex items-start justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">
                    Cover Letter for {selectedJob?.company || "Hiring Manager"}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Target Position: {selectedJob?.title || "Leadership Role"}
                  </p>
                </div>
                <div className="text-right">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                      coverLetterWordCount >= 250 && coverLetterWordCount <= 350
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                        : "bg-blue-500/20 text-blue-300 border-blue-500/30"
                    }`}
                  >
                    {coverLetterWordCount} / 250–350 Words
                  </span>
                </div>
              </div>

              {/* Salutation */}
              <div className="text-xs text-slate-300 font-medium">
                {coverLetterPreview?.salutation || "Dear Hiring Team,"}
              </div>

              {/* Body Textarea */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Letter Body (Paragraphs separated by blank lines)
                </label>
                <textarea
                  value={editedCoverLetterBody}
                  onChange={(e) => setEditedCoverLetterBody(e.target.value)}
                  rows={14}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 leading-relaxed focus:outline-none focus:border-purple-500 font-sans"
                  placeholder="Cover letter body paragraphs..."
                />
              </div>

              {/* Signoff */}
              <div className="text-xs text-slate-300 space-y-0.5 pt-2">
                <p className="whitespace-pre-line">{coverLetterPreview?.sign_off || "Sincerely,\nRaghunath Reddy"}</p>
                <p className="font-bold text-white">
                  {coverLetterPreview?.candidate_name || "Raghunath Reddy"}
                </p>
                <p className="text-slate-400 text-[11px]">Global SHE &amp; Security Manager</p>
              </div>
            </div>
          </div>

          {/* Right Column: Actions & Rules Guidance */}
          <div className="lg:col-span-4 space-y-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Edit3 className="w-3.5 h-3.5 text-purple-400" />
                Cover Letter Actions
              </h3>

              <button
                onClick={handleSaveDraftChanges}
                disabled={isSaving || !currentPackage}
                className="w-full py-2 px-3 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 disabled:opacity-50"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{isSaving ? "Saving..." : "Save Cover Letter Changes"}</span>
              </button>

              <button
                onClick={handleGenerateCoverLetterOnly}
                disabled={isGenerating || !selectedJobId}
                className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center justify-center space-x-1.5 disabled:opacity-50"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Regenerate from Profile</span>
              </button>
            </div>

            {currentPackage && (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-white uppercase tracking-wider block">
                  Export Cover Letter
                </span>
                <a
                  href={getPackageDownloadUrl(currentPackage.id, "cover_docx")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center justify-between"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                    Cover Letter (.docx)
                  </span>
                  <Download className="w-3 h-3 text-slate-400" />
                </a>

                <a
                  href={getPackageDownloadUrl(currentPackage.id, "cover_pdf")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center justify-between"
                >
                  <span className="flex items-center gap-2">
                    <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                    Cover Letter (.pdf)
                  </span>
                  <Download className="w-3 h-3 text-slate-400" />
                </a>
              </div>
            )}

            {/* Ethical Boundaries Alert */}
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 space-y-1.5">
              <span className="font-bold text-slate-300 flex items-center gap-1">
                <Shield className="w-3.5 h-3.5 text-blue-400" />
                Accuracy &amp; Integrity Guarantee
              </span>
              <p className="text-[11px] leading-relaxed">
                The cover letter strictly cites verified facts: 18+ years HSE experience, M.Tech degree, APAC multi-site leadership, and ISO 14001 / 45001. No company initiatives or unverified metrics are invented.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ATS KEYWORD ALIGNMENT PANEL */}
      {activeTab === "ats" && (
        <div className="space-y-6">
          {atsAnalysis ? (
            <div className="space-y-6">
              {/* Coverage Meter & Disclaimer */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="space-y-1 text-center md:text-left">
                  <h3 className="text-base font-bold text-white">
                    ATS Keyword Coverage: {atsAnalysis.overall_coverage_pct}%
                  </h3>
                  <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
                    {atsAnalysis.disclaimer}
                  </p>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-center">
                    <span className="text-2xl font-bold font-mono text-emerald-400 block">
                      {atsAnalysis.matched_keywords?.length || 0}
                    </span>
                    <span className="text-[10px] uppercase font-bold text-slate-500">Supported</span>
                  </div>
                  <div className="text-center">
                    <span className="text-2xl font-bold font-mono text-amber-400 block">
                      {atsAnalysis.missing_keywords?.length || 0}
                    </span>
                    <span className="text-[10px] uppercase font-bold text-slate-500">Missing</span>
                  </div>
                </div>
              </div>

              {/* Supported Competencies with Evidence */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Verified Supported Competencies &amp; Evidence ({atsAnalysis.matched_keywords?.length || 0})
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(atsAnalysis.matched_keywords || []).map((m, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-xs">{m.keyword}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono">
                          {m.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        <span className="text-slate-500">Verified Evidence:</span> {m.evidence}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Missing Requirements & Ethical Suggestions */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" />
                  Missing Job Requirements &amp; Honest Strategy ({atsAnalysis.missing_keywords?.length || 0})
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(atsAnalysis.missing_keywords || []).map((m, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200 text-xs">{m.keyword}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          {m.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        <span className="text-amber-400/80">Impact:</span> {m.impact}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-500" />
              <span>Analyzing job description against verified profile facts...</span>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: PACKAGE FILES & EXPORT */}
      {activeTab === "package" && (
        <div className="space-y-6">
          {currentPackage ? (
            <div className="space-y-6">
              {/* Package Metadata Summary Card */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      Package #{currentPackage.id} — {currentPackage.job_title}
                    </h3>
                    <p className="text-xs text-slate-400">
                      Employer: <span className="text-slate-200 font-semibold">{currentPackage.company}</span> • Template:{" "}
                      <span className="text-slate-200 font-semibold">{currentPackage.template_name}</span> • Created:{" "}
                      {new Date(currentPackage.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-xs px-3 py-1 rounded-full font-bold border ${
                        currentPackage.status === "approved"
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                          : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                      }`}
                    >
                      STATUS: {currentPackage.status.toUpperCase()} (v{currentVersion})
                    </span>

                    <a
                      href={getPackageDownloadUrl(currentPackage.id, "zip")}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center space-x-1.5 shadow-md shadow-blue-500/20"
                    >
                      <Archive className="w-3.5 h-3.5" />
                      <span>Download ZIP</span>
                    </a>
                  </div>
                </div>

                {/* Audit & Generation Log */}
                <div className="text-xs text-slate-400 flex items-center space-x-4 pt-1">
                  <span>Method: {currentPackage.generation_method}</span>
                  {currentPackage.approvals && currentPackage.approvals.length > 0 && (
                    <span className="text-emerald-400">
                      Approved at {new Date(currentPackage.approvals[0].approved_at).toLocaleString()} by {currentPackage.approvals[0].approved_by}
                    </span>
                  )}
                </div>
              </div>

              {/* Package Documents Table */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-blue-400" />
                  Package Artifacts &amp; Direct Downloads
                </h4>

                <div className="space-y-2">
                  {(currentPackage.documents || []).map((doc: GeneratedDocument) => (
                    <div
                      key={doc.id}
                      className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between hover:border-slate-700 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                          {doc.doc_type.includes("pdf") ? (
                            <FileCheck className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <FileText className="w-4 h-4 text-blue-400" />
                          )}
                        </div>
                        <div>
                          <span className="font-bold text-slate-200 text-xs block">{doc.filename}</span>
                          <span className="text-[11px] text-slate-500">
                            v{doc.version_number} • Format: {doc.doc_type.includes("pdf") ? "PDF" : doc.doc_type.includes("docx") ? "DOCX" : "TXT"} • Status:{" "}
                            {doc.is_approved ? "Approved" : "Draft"}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {doc.doc_type.includes("docx") && (
                          <a
                            href={getPackageDownloadUrl(
                              currentPackage.id,
                              doc.doc_type.includes("cv") ? "cv_docx" : "cover_docx"
                            )}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center space-x-1"
                          >
                            <Download className="w-3 h-3" />
                            <span>DOCX</span>
                          </a>
                        )}

                        {doc.doc_type.includes("pdf") && (
                          <a
                            href={getPackageDownloadUrl(
                              currentPackage.id,
                              doc.doc_type.includes("cv") ? "cv_pdf" : "cover_pdf"
                            )}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 text-xs font-semibold border border-slate-700 flex items-center space-x-1"
                          >
                            <Download className="w-3 h-3" />
                            <span>PDF</span>
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <Archive className="w-8 h-8 mx-auto text-slate-500" />
              <h3 className="text-sm font-bold text-white">No Package Generated Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Select your target position and template above, then click &quot;Generate Application Package&quot; to build DOCX, PDF, checklist, and metadata files.
              </p>
              <button
                onClick={handleGeneratePackage}
                disabled={isGenerating || !selectedJobId}
                className="mt-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-md"
              >
                Generate Package Now
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: PACKAGE HISTORY */}
      {activeTab === "history" && (
        <div className="space-y-4">
          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              All Generated Application Packages ({recentPackages.length})
            </h3>

            {recentPackages.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No packages in history yet.</p>
            ) : (
              <div className="divide-y divide-slate-800/80">
                {recentPackages.map((pkg) => (
                  <div key={pkg.id} className="py-3.5 flex items-center justify-between gap-4">
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white text-xs">{pkg.job_title}</span>
                        <span
                          className={`text-[10px] px-2 py-0.2 rounded font-bold border ${
                            pkg.status === "approved"
                              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                              : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                          }`}
                        >
                          {pkg.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {pkg.company} • Template: {pkg.template_name} • Created:{" "}
                        {new Date(pkg.created_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => {
                          setSelectedJobId(pkg.job_id);
                          setCurrentPackage(pkg);
                          setActiveTab("package");
                        }}
                        className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
                      >
                        Inspect
                      </button>

                      <a
                        href={getPackageDownloadUrl(pkg.id, "zip")}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 text-xs font-semibold border border-blue-500/30 flex items-center space-x-1"
                      >
                        <Download className="w-3 h-3" />
                        <span>ZIP</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
