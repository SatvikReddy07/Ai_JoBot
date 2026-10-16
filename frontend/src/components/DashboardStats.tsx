import React from "react";
import {
  Briefcase,
  Flame,
  Award,
  Sparkles,
  Bookmark,
  Send,
  Clock,
  ArrowUpRight
} from "lucide-react";
import { DashboardStats as StatsType } from "../types";

interface DashboardStatsProps {
  stats: StatsType | null;
  onFilterSelect?: (filterKey: string, filterVal: any) => void;
}

export const DashboardStats: React.FC<DashboardStatsProps> = ({
  stats,
  onFilterSelect
}) => {
  const cards = [
    {
      id: "total",
      label: "Total Discovered",
      value: stats ? stats.total_jobs : 0,
      icon: Briefcase,
      color: "from-blue-500/10 to-indigo-500/10 text-blue-400 border-blue-500/20",
      description: "Across verified career feeds",
      filterKey: "match_level",
      filterVal: "All"
    },
    {
      id: "new_today",
      label: "New Today",
      value: stats ? stats.new_jobs_today : 0,
      icon: Flame,
      color: "from-amber-500/10 to-orange-500/10 text-amber-400 border-amber-500/20",
      description: "Discovered in last 24h",
      filterKey: "sort_by",
      filterVal: "date_desc"
    },
    {
      id: "excellent",
      label: "Excellent Matches",
      value: stats ? stats.excellent_matches : 0,
      icon: Award,
      color: "from-emerald-500/10 to-teal-500/10 text-emerald-400 border-emerald-500/20",
      description: "Score 85–100 (High leadership fit)",
      filterKey: "match_level",
      filterVal: "Excellent Match"
    },
    {
      id: "strong",
      label: "Strong Matches",
      value: stats ? stats.strong_matches : 0,
      icon: Sparkles,
      color: "from-cyan-500/10 to-blue-500/10 text-cyan-400 border-cyan-500/20",
      description: "Score 75–84 (Solid alignment)",
      filterKey: "match_level",
      filterVal: "Strong Match"
    },
    {
      id: "saved",
      label: "Saved Opportunities",
      value: stats ? stats.saved_opportunities : 0,
      icon: Bookmark,
      color: "from-violet-500/10 to-purple-500/10 text-violet-400 border-violet-500/20",
      description: "Bookmarked for review",
      filterKey: "is_saved",
      filterVal: true
    },
    {
      id: "active_applications",
      label: "Active In Tracker",
      value: stats ? stats.active_applications : 0,
      icon: Send,
      color: "from-rose-500/10 to-pink-500/10 text-rose-400 border-rose-500/20",
      description: "Ready, Applied, or Interviewing",
      filterKey: "tab",
      filterVal: "tracker"
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.id}
            onClick={() => onFilterSelect && onFilterSelect(card.filterKey, card.filterVal)}
            className={`p-4 rounded-xl border bg-gradient-to-br ${card.color} hover:border-slate-600 transition-all cursor-pointer group shadow-sm`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">{card.label}</span>
              <Icon className="w-4 h-4 opacity-75 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className="mt-2.5 flex items-baseline justify-between">
              <span className="text-2xl font-bold tracking-tight text-white">
                {card.value.toLocaleString()}
              </span>
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300 transition-colors" />
            </div>
            <p className="mt-1 text-[11px] text-slate-400 truncate">{card.description}</p>
          </div>
        );
      })}
    </div>
  );
};
