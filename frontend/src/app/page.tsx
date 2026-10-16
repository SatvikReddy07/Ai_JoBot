"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Sidebar,
  NavTab
} from "../components/Sidebar";
import { Navbar } from "../components/Navbar";
import { DashboardStats } from "../components/DashboardStats";
import { JobList } from "../components/JobList";
import { JobModal } from "../components/JobModal";
import { ApplicationTracker } from "../components/ApplicationTracker";
import { EmployerManager } from "../components/EmployerManager";
import { SearchHistoryView } from "../components/SearchHistoryView";
import { SettingsView } from "../components/SettingsView";
import { CareerProfileView } from "../components/CareerProfileView";
import { ApplicationStudioView } from "../components/ApplicationStudioView";

import {
  Job,
  JobListResponse,
  DashboardStats as StatsType,
  EmployerBoard,
  SearchHistoryItem,
  Settings
} from "../types";
import {
  getDashboardStats,
  getJobs,
  getJobById,
  toggleSaveJob,
  updateJobStatus,
  runSearchNow,
  getEmployers,
  getSearchHistory,
  getSettings,
  JobFilterParams
} from "../lib/api";
import {
  Sparkles,
  Compass,
  Briefcase,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Building2
} from "lucide-react";

export default function Home() {
  const [currentTab, setCurrentTab] = useState<NavTab>("dashboard");
  const [stats, setStats] = useState<StatsType | null>(null);
  const [jobData, setJobData] = useState<JobListResponse | null>(null);
  const [allJobsForTracker, setAllJobsForTracker] = useState<Job[]>([]);
  const [employers, setEmployers] = useState<EmployerBoard[]>([]);
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [studioTargetJobId, setStudioTargetJobId] = useState<number | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleOpenStudio = (jobId: number) => {
    setStudioTargetJobId(jobId);
    setCurrentTab("studio");
  };

  // Filter state for Discover tab
  const [filters, setFilters] = useState<JobFilterParams>({
    q: "",
    country: "All",
    city: "",
    company: "",
    job_title: "",
    match_level: "All",
    employment_type: "All",
    sponsorship_status: "All",
    application_status: "All",
    sort_by: "score_desc",
    page: 1,
    page_size: 20
  });

  // Load Dashboard Data
  const loadDashboardData = useCallback(async () => {
    try {
      const [s, emps, hist, sett] = await Promise.all([
        getDashboardStats().catch(() => null),
        getEmployers().catch(() => []),
        getSearchHistory().catch(() => []),
        getSettings().catch(() => null)
      ]);
      if (s) setStats(s);
      setEmployers(emps);
      setHistory(hist);
      if (sett) setSettings(sett);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    }
  }, []);

  // Load Jobs
  const loadJobs = useCallback(async (customParams: JobFilterParams = {}) => {
    setIsLoadingJobs(true);
    try {
      const queryParams = { ...filters, ...customParams };
      const res = await getJobs(queryParams);
      setJobData(res);
    } catch (err) {
      console.error("Error loading jobs:", err);
    } finally {
      setIsLoadingJobs(false);
    }
  }, [filters]);

  // Load Tracker Jobs
  const loadTrackerJobs = useCallback(async () => {
    try {
      const res = await getJobs({ page_size: 100, page: 1 });
      setAllJobsForTracker(res.items);
    } catch (err) {
      console.error("Error loading tracker jobs:", err);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    if (currentTab === "dashboard") {
      loadJobs({ page_size: 10, page: 1, sort_by: "score_desc" });
    } else if (currentTab === "discover") {
      loadJobs({ is_saved: undefined, min_score: undefined });
    } else if (currentTab === "high_matches") {
      loadJobs({ min_score: 75, is_saved: undefined });
    } else if (currentTab === "saved") {
      loadJobs({ is_saved: true, min_score: undefined });
    } else if (currentTab === "tracker") {
      loadTrackerJobs();
    }
  }, [currentTab, loadJobs, loadTrackerJobs]);

  const handleFilterChange = (newFilters: Partial<JobFilterParams>) => {
    setFilters((prev) => {
      const updated = { ...prev, ...newFilters };
      loadJobs(updated);
      return updated;
    });
  };

  const handleResetFilters = () => {
    const defaultFilters: JobFilterParams = {
      q: "",
      country: "All",
      city: "",
      company: "",
      job_title: "",
      match_level: "All",
      employment_type: "All",
      sponsorship_status: "All",
      application_status: "All",
      sort_by: "score_desc",
      page: 1,
      page_size: 20
    };
    setFilters(defaultFilters);
    loadJobs(defaultFilters);
  };

  const handleSearchNow = async () => {
    setIsSearching(true);
    setNotification(null);
    try {
      const res = await runSearchNow();
      setNotification({
        type: "success",
        text: `Discovery completed! Found ${res.jobs_new} new and updated ${res.jobs_updated} vacancies across ${res.boards_searched} employer feeds.`
      });
      await Promise.all([loadDashboardData(), loadJobs(), loadTrackerJobs()]);
    } catch (err: any) {
      setNotification({
        type: "error",
        text: `Search error: ${err.message || "Failed to complete discovery."}`
      });
    } finally {
      setIsSearching(false);
      setTimeout(() => setNotification(null), 8000);
    }
  };

  const handleToggleSave = async (jobId: number, currentSaved: boolean) => {
    try {
      await toggleSaveJob(jobId, !currentSaved);
      loadDashboardData();
      loadJobs();
      loadTrackerJobs();
      if (selectedJob && selectedJob.id === jobId) {
        setSelectedJob({ ...selectedJob, is_saved: !currentSaved });
      }
    } catch (err: any) {
      alert("Error updating save status: " + err.message);
    }
  };

  const handleStatusChange = async (jobId: number, status: string, notes?: string) => {
    try {
      await updateJobStatus(jobId, status, notes);
      loadDashboardData();
      loadJobs();
      loadTrackerJobs();
      if (selectedJob && selectedJob.id === jobId) {
        setSelectedJob({
          ...selectedJob,
          application_status: status as any,
          application_notes: notes !== undefined ? notes : selectedJob.application_notes
        });
      }
    } catch (err: any) {
      alert("Error updating application status: " + err.message);
    }
  };

  const titles: Record<NavTab, { title: string; subtitle: string }> = {
    dashboard: {
      title: "Executive HSE Dashboard",
      subtitle: "Personalized intelligence for Global SHE & Security leadership opportunities"
    },
    discover: {
      title: "Discover HSE Opportunities",
      subtitle: "Explore verified vacancies across India, Singapore, Europe, and Australia"
    },
    high_matches: {
      title: "High Suitability Matches (Score 75+)",
      subtitle: "Top-tier executive roles matching your 18+ years APAC & Global background"
    },
    profile: {
      title: "My Career Profile",
      subtitle: "Master CV, verified professional background, and AI career matching configuration"
    },
    studio: {
      title: "AI Application Studio",
      subtitle: "Tailor executive CVs, generate cover letters, review ATS alignment & export packages"
    },
    saved: {

      title: "Saved Opportunities",
      subtitle: "Shortlisted positions bookmarked for CV tailoring and tracking"
    },
    tracker: {
      title: "Application Pipeline Tracker",
      subtitle: "Manage your candidacy stages from discovery to offers"
    },
    history: {
      title: "Search Audit & History",
      subtitle: "Review manual and automated daily feed discovery runs"
    },
    settings: {
      title: "Matching Rules & Employer Feeds",
      subtitle: "Configure scoring weights, candidate criteria, and live boards"
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        savedCount={stats ? stats.saved_opportunities : 0}
        highMatchCount={stats ? (stats.excellent_matches + stats.strong_matches) : 0}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar
          title={titles[currentTab].title}
          subtitle={titles[currentTab].subtitle}
          onSearchNow={handleSearchNow}
          isSearching={isSearching}
          filterParams={filters}
          lastSearchTime={stats?.last_successful_search}
        />

        {/* Global Notification Banner */}
        {notification && (
          <div
            className={`mx-8 mt-4 p-3.5 rounded-xl border text-xs flex items-center justify-between animate-fadeIn ${
              notification.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-rose-500/10 border-rose-500/30 text-rose-300"
            }`}
          >
            <div className="flex items-center space-x-2">
              {notification.type === "success" ? (
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              )}
              <span>{notification.text}</span>
            </div>
            <button
              onClick={() => setNotification(null)}
              className="text-slate-400 hover:text-white font-bold text-sm px-1"
            >
              &times;
            </button>
          </div>
        )}

        {/* Dynamic View Tab Body */}
        <main className="flex-1 p-8 overflow-y-auto space-y-6">
          {/* TAB 1: DASHBOARD */}
          {currentTab === "dashboard" && (
            <div className="space-y-6">
              {/* Executive KPI Stats */}
              <DashboardStats
                stats={stats}
                onFilterSelect={(k, v) => {
                  if (k === "tab") {
                    setCurrentTab(v as NavTab);
                  } else if (k === "match_level") {
                    setCurrentTab(v === "All" ? "discover" : "high_matches");
                  } else {
                    handleFilterChange({ [k]: v });
                    setCurrentTab("discover");
                  }
                }}
              />

              {/* Action Banner */}
              <div className="p-5 rounded-2xl bg-gradient-to-r from-blue-950/60 via-slate-900 to-indigo-950/60 border border-blue-500/20 shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    Automated Global Discovery Engine Active
                  </h3>
                  <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                    Searching public career feeds from verified multinational employers for Global HSE, Regional EHS, and SHE&amp;S leadership positions across India, Singapore, Europe, and Australia.
                  </p>
                </div>
                <button
                  onClick={handleSearchNow}
                  disabled={isSearching}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-md shadow-blue-500/20 transition-all active:scale-[0.98] whitespace-nowrap"
                >
                  <RefreshCw className={`w-4 h-4 ${isSearching ? "animate-spin" : ""}`} />
                  <span>{isSearching ? "Searching Feeds..." : "Run Live Discovery"}</span>
                </button>
              </div>

              {/* Top Matches Preview */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-emerald-400" />
                    Top Matching Leadership Roles
                  </h3>
                  <button
                    onClick={() => setCurrentTab("discover")}
                    className="text-xs text-blue-400 hover:text-blue-300 font-semibold"
                  >
                    View All {stats?.total_jobs || 0} Vacancies &rarr;
                  </button>
                </div>

                <JobList
                  jobData={jobData}
                  filters={filters}
                  onFilterChange={handleFilterChange}
                  onResetFilters={handleResetFilters}
                  onSelectJob={setSelectedJob}
                  onToggleSave={handleToggleSave}
                  onStatusChange={handleStatusChange}
                  isLoading={isLoadingJobs}
                  onSearchNow={handleSearchNow}
                />
              </div>
            </div>
          )}

          {/* TAB 2: DISCOVER JOBS */}
          {currentTab === "discover" && (
            <JobList
              jobData={jobData}
              filters={filters}
              onFilterChange={handleFilterChange}
              onResetFilters={handleResetFilters}
              onSelectJob={setSelectedJob}
              onToggleSave={handleToggleSave}
              onStatusChange={handleStatusChange}
              isLoading={isLoadingJobs}
              onSearchNow={handleSearchNow}
            />
          )}

          {/* TAB 3: HIGH MATCHES */}
          {currentTab === "high_matches" && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
                <span>Displaying roles evaluated with Suitability Score 75–100 (Strong &amp; Excellent alignment).</span>
                <span className="font-bold font-mono">{jobData?.total || 0} opportunities</span>
              </div>
              <JobList
                jobData={jobData}
                filters={filters}
                onFilterChange={handleFilterChange}
                onResetFilters={handleResetFilters}
                onSelectJob={setSelectedJob}
                onToggleSave={handleToggleSave}
                onStatusChange={handleStatusChange}
                isLoading={isLoadingJobs}
                onSearchNow={handleSearchNow}
              />
            </div>
          )}

          {/* TAB: MY CAREER PROFILE */}
          {currentTab === "profile" && (
            <CareerProfileView />
          )}

          {/* TAB: APPLICATION STUDIO (PHASE 3) */}
          {currentTab === "studio" && (
            <ApplicationStudioView initialJobId={studioTargetJobId} />
          )}

          {/* TAB 4: SAVED JOBS */}
          {currentTab === "saved" && (

            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs flex items-center justify-between">
                <span>Your shortlisted leadership opportunities saved for application preparation.</span>
                <span className="font-bold font-mono">{jobData?.total || 0} bookmarked</span>
              </div>
              <JobList
                jobData={jobData}
                filters={filters}
                onFilterChange={handleFilterChange}
                onResetFilters={handleResetFilters}
                onSelectJob={setSelectedJob}
                onToggleSave={handleToggleSave}
                onStatusChange={handleStatusChange}
                isLoading={isLoadingJobs}
                onSearchNow={handleSearchNow}
              />
            </div>
          )}

          {/* TAB 5: APPLICATION TRACKER */}
          {currentTab === "tracker" && (
            <ApplicationTracker
              jobs={allJobsForTracker}
              onSelectJob={setSelectedJob}
              onStatusChange={handleStatusChange}
            />
          )}

          {/* TAB 6: SEARCH HISTORY */}
          {currentTab === "history" && (
            <SearchHistoryView history={history} />
          )}

          {/* TAB 7: SETTINGS & EMPLOYERS */}
          {currentTab === "settings" && (
            <div className="space-y-8">
              {settings && (
                <SettingsView
                  settings={settings}
                  onRefresh={loadDashboardData}
                />
              )}

              <EmployerManager
                employers={employers}
                onRefresh={loadDashboardData}
              />
            </div>
          )}
        </main>
      </div>

      {/* Detailed Match Inspection Modal */}
      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onToggleSave={handleToggleSave}
          onStatusChange={handleStatusChange}
          onOpenStudio={handleOpenStudio}
        />
      )}
    </div>
  );
}
