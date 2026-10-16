import React from "react";
import {
  Search,
  Filter,
  Bookmark,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Eye,
  MapPin,
  Building2,
  Calendar,
  CheckCircle,
  RotateCcw
} from "lucide-react";
import { Job, JobListResponse } from "../types";
import { JobFilterParams } from "../lib/api";

interface JobListProps {
  jobData: JobListResponse | null;
  filters: JobFilterParams;
  onFilterChange: (newFilters: Partial<JobFilterParams>) => void;
  onResetFilters: () => void;
  onSelectJob: (job: Job) => void;
  onToggleSave: (jobId: number, currentSaved: boolean) => void;
  onStatusChange: (jobId: number, status: string) => void;
  isLoading: boolean;
  onSearchNow: () => void;
}

export const JobList: React.FC<JobListProps> = ({
  jobData,
  filters,
  onFilterChange,
  onResetFilters,
  onSelectJob,
  onToggleSave,
  onStatusChange,
  isLoading,
  onSearchNow
}) => {
  const getScoreBadge = (score: number) => {
    if (score >= 85) return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    if (score >= 75) return "bg-blue-500/15 text-blue-400 border-blue-500/30";
    if (score >= 60) return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    return "bg-slate-500/15 text-slate-400 border-slate-500/30";
  };

  const countries = [
    "All", "India", "Singapore", "Germany", "Netherlands", "Ireland", "Australia", "United Kingdom", "Switzerland", "Unknown"
  ];

  const matchLevels = ["All", "Excellent Match", "Strong Match", "Potential Match", "Low Match"];
  const aiPriorities = ["All", "High", "Medium", "Low"];
  const employmentTypes = ["All", "Permanent Full-time", "Full-time", "Unknown"];
  const sponsorshipOptions = ["All", "Confirmed", "Not Supported", "Unknown"];

  const items = jobData?.items || [];
  const total = jobData?.total || 0;
  const page = jobData?.page || 1;
  const totalPages = jobData?.total_pages || 1;

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Keyword Search */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={filters.q || ""}
              onChange={(e) => onFilterChange({ q: e.target.value, page: 1 })}
              placeholder="Search by HSE title, company, plant location, or expertise..."
              className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2.5 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* Quick Sort */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 whitespace-nowrap">Sort By:</span>
            <select
              value={filters.sort_by || "score_desc"}
              onChange={(e) => onFilterChange({ sort_by: e.target.value, page: 1 })}
              className="text-xs bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="score_desc">Highest Match Score</option>
              <option value="date_desc">Most Recently Discovered</option>
              <option value="company_asc">Company (A-Z)</option>
              <option value="score_asc">Lowest Match Score</option>
            </select>

            <button
              onClick={onResetFilters}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 transition-colors"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Multi-faceted Dropdowns */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-1">
          {/* Country */}
          <div>
            <label className="text-[11px] font-semibold text-slate-400 mb-1 block">Country</label>
            <select
              value={filters.country || "All"}
              onChange={(e) => onFilterChange({ country: e.target.value, page: 1 })}
              className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {countries.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* AI Priority Filter */}
          <div>
            <label className="text-[11px] font-semibold text-indigo-400 mb-1 block">AI Priority</label>
            <select
              value={filters.ai_priority || "All"}
              onChange={(e) => onFilterChange({ ai_priority: e.target.value, page: 1 })}
              className="w-full text-xs bg-slate-950 border border-indigo-500/30 rounded-lg px-2.5 py-1.5 text-indigo-200 focus:outline-none focus:border-indigo-500"
            >
              {aiPriorities.map((p) => (
                <option key={p} value={p}>{p === "All" ? "All Priorities" : `${p} Priority`}</option>
              ))}
            </select>
          </div>

          {/* Match Tier */}
          <div>
            <label className="text-[11px] font-semibold text-slate-400 mb-1 block">Rules Match Tier</label>
            <select
              value={filters.match_level || "All"}
              onChange={(e) => onFilterChange({ match_level: e.target.value, page: 1 })}
              className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {matchLevels.map((lvl) => (
                <option key={lvl} value={lvl}>{lvl}</option>
              ))}
            </select>
          </div>

          {/* Employment Type */}
          <div>
            <label className="text-[11px] font-semibold text-slate-400 mb-1 block">Employment Type</label>
            <select
              value={filters.employment_type || "All"}
              onChange={(e) => onFilterChange({ employment_type: e.target.value, page: 1 })}
              className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {employmentTypes.map((et) => (
                <option key={et} value={et}>{et}</option>
              ))}
            </select>
          </div>

          {/* Sponsorship */}
          <div>
            <label className="text-[11px] font-semibold text-slate-400 mb-1 block">Visa Sponsorship</label>
            <select
              value={filters.sponsorship_status || "All"}
              onChange={(e) => onFilterChange({ sponsorship_status: e.target.value, page: 1 })}
              className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {sponsorshipOptions.map((sp) => (
                <option key={sp} value={sp}>{sp}</option>
              ))}
            </select>
          </div>
        </div>
      </div>


      {/* Results Count Summary */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>
          Showing <strong className="text-white">{items.length}</strong> of{" "}
          <strong className="text-white">{total.toLocaleString()}</strong> vacancies
        </span>
        <span>Page {page} of {totalPages}</span>
      </div>

      {/* Jobs Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 select-none">
              <tr>
                <th className="py-3 px-4 font-semibold">Match Score</th>
                <th className="py-3 px-4 font-semibold">Job Title &amp; Scope</th>
                <th className="py-3 px-4 font-semibold">Company</th>
                <th className="py-3 px-4 font-semibold">Location</th>
                <th className="py-3 px-4 font-semibold">Type</th>
                <th className="py-3 px-4 font-semibold">Sponsorship</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {items.map((job) => (
                <tr
                  key={job.id}
                  className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                  onClick={() => onSelectJob(job)}
                >
                  {/* Match Score */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {job.ai_assessment ? (
                      <div className="flex flex-col gap-0.5 items-start">
                        <span className={`inline-flex items-center text-xs font-bold px-2 py-0.5 rounded-full border ${getScoreBadge(job.ai_assessment.match_score)}`}>
                          AI {job.ai_assessment.match_score} &bull; {job.ai_assessment.application_priority}
                        </span>
                        <span className="text-[10px] text-slate-500 font-medium">
                          Rules: {job.match_score}
                        </span>
                      </div>
                    ) : (
                      <span className={`inline-flex items-center text-xs font-bold px-2.5 py-0.5 rounded-full border ${getScoreBadge(job.match_score)}`}>
                        {job.match_score} &bull; {job.match_level.replace(" Match", "")}
                      </span>
                    )}
                  </td>


                  {/* Title */}
                  <td className="py-3.5 px-4 font-semibold text-white max-w-xs">
                    <div className="truncate group-hover:text-blue-400 transition-colors">
                      {job.title}
                    </div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
                      Source: {job.source}
                    </span>
                  </td>

                  {/* Company */}
                  <td className="py-3.5 px-4 whitespace-nowrap text-slate-200">
                    <div className="flex items-center space-x-1.5">
                      <Building2 className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span className="font-medium">{job.company}</span>
                    </div>
                  </td>

                  {/* Location */}
                  <td className="py-3.5 px-4 whitespace-nowrap text-slate-300">
                    <div className="flex items-center space-x-1.5">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span className="truncate max-w-[140px]" title={job.location}>
                        {job.city ? `${job.city}, ` : ""}{job.country || job.location}
                      </span>
                    </div>
                  </td>

                  {/* Type */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className={`text-[11px] px-2 py-0.5 rounded font-medium ${
                      job.employment_type === "Permanent Full-time"
                        ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                        : job.employment_type === "Full-time"
                        ? "bg-blue-500/10 text-blue-300 border border-blue-500/20"
                        : "bg-slate-800 text-slate-400"
                    }`}>
                      {job.employment_type}
                    </span>
                  </td>

                  {/* Sponsorship */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className={`text-[11px] font-medium ${
                      job.sponsorship_status === "Confirmed"
                        ? "text-emerald-400"
                        : job.sponsorship_status === "Not Supported"
                        ? "text-rose-400"
                        : "text-slate-400"
                    }`}>
                      {job.sponsorship_status}
                    </span>
                  </td>

                  {/* Status */}
                  <td className="py-3.5 px-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <select
                      value={job.application_status}
                      onChange={(e) => onStatusChange(job.id, e.target.value)}
                      className="bg-slate-950 text-[11px] font-medium text-slate-300 px-2 py-1 rounded border border-slate-800 focus:outline-none focus:border-blue-500"
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
                  </td>

                  {/* Actions */}
                  <td className="py-3.5 px-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end space-x-1.5">
                      <button
                        onClick={() => onToggleSave(job.id, job.is_saved)}
                        className={`p-1.5 rounded-lg border transition-colors ${
                          job.is_saved
                            ? "bg-blue-600/20 border-blue-500/40 text-blue-400"
                            : "bg-slate-800/80 border-slate-700/60 text-slate-400 hover:text-white"
                        }`}
                        title={job.is_saved ? "Remove from saved" : "Save opportunity"}
                      >
                        <Bookmark className={`w-3.5 h-3.5 ${job.is_saved ? "fill-blue-400" : ""}`} />
                      </button>

                      <button
                        onClick={() => onSelectJob(job)}
                        className="p-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                        title="View match analysis"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>

                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-400 hover:text-cyan-400 hover:bg-slate-700 transition-colors"
                        title="Open original job posting"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {items.length === 0 && (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-500">
              <Search className="w-6 h-6" />
            </div>
            <h4 className="text-base font-bold text-white">No Vacancies Found</h4>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              No jobs match your current filter combination. Try resetting your filters, expanding your target country criteria, or executing a live discovery run.
            </p>
            <div className="pt-2 flex items-center justify-center gap-3">
              <button
                onClick={onResetFilters}
                className="text-xs font-semibold px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                Reset Filters
              </button>
              <button
                onClick={onSearchNow}
                className="text-xs font-semibold px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
              >
                Search Live Feeds Now
              </button>
            </div>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
            <span className="text-xs text-slate-400">
              Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onFilterChange({ page: Math.max(1, page - 1) })}
                disabled={page <= 1}
                className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs text-slate-300 border border-slate-700 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
              <button
                onClick={() => onFilterChange({ page: Math.min(totalPages, page + 1) })}
                disabled={page >= totalPages}
                className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs text-slate-300 border border-slate-700 transition-colors"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
