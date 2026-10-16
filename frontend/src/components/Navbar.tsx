import React, { useState, useEffect } from "react";
import { Search, RefreshCw, Download, Bell, Sparkles } from "lucide-react";
import { getExportCsvUrl, JobFilterParams, getAiUsageStats } from "../lib/api";
import { AIUsageStats } from "../types";

interface NavbarProps {
  title: string;
  subtitle?: string;
  onSearchNow: () => void;
  isSearching: boolean;
  filterParams?: JobFilterParams;
  lastSearchTime?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  title,
  subtitle,
  onSearchNow,
  isSearching,
  filterParams = {},
  lastSearchTime
}) => {
  const exportUrl = getExportCsvUrl(filterParams);
  const [aiUsage, setAiUsage] = useState<AIUsageStats | null>(null);

  useEffect(() => {
    getAiUsageStats()
      .then((data) => setAiUsage(data))
      .catch(() => {});
  }, [isSearching]);

  return (
    <header className="h-16 px-8 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md flex items-center justify-between sticky top-0 z-20">
      <div>
        <h2 className="text-lg font-bold text-white tracking-tight">{title}</h2>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>

      <div className="flex items-center space-x-3">
        {/* Phase 2 AI Usage Badge */}
        {aiUsage && (
          <span
            className="hidden sm:inline-flex items-center gap-1.5 text-xs text-indigo-300 bg-indigo-950/40 border border-indigo-500/30 px-2.5 py-1.5 rounded-lg font-medium"
            title={`Gemini API: ${aiUsage.daily_used} used of ${aiUsage.daily_limit} daily limit (${aiUsage.remaining} remaining today)`}
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>AI: {aiUsage.daily_used}/{aiUsage.daily_limit}</span>
          </span>
        )}

        {lastSearchTime && (
          <span className="hidden md:inline-flex text-xs text-slate-400 bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-700/50">
            Last verified: {new Date(lastSearchTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}


        {/* CSV Export Button */}
        <a
          href={exportUrl}
          download
          className="inline-flex items-center space-x-2 text-xs font-semibold px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 transition-colors shadow-sm"
          title="Export matching opportunities to CSV"
        >
          <Download className="w-3.5 h-3.5 text-slate-400" />
          <span>Export CSV</span>
        </a>

        {/* Search Jobs Now Trigger Button */}
        <button
          onClick={onSearchNow}
          disabled={isSearching}
          className={`inline-flex items-center space-x-2 text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-md ${
            isSearching
              ? "bg-blue-600/50 text-blue-200 cursor-not-allowed"
              : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/20 active:scale-[0.98]"
          }`}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSearching ? "animate-spin" : ""}`} />
          <span>{isSearching ? "Searching Feeds..." : "Search Jobs Now"}</span>
        </button>
      </div>
    </header>
  );
};
