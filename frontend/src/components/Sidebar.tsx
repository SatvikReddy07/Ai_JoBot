import React from "react";
import {
  LayoutDashboard,
  Compass,
  Sparkles,
  Bookmark,
  Kanban,
  History,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Building2,
  ExternalLink,
  UserCheck
} from "lucide-react";

export type NavTab =
  | "dashboard"
  | "discover"
  | "high_matches"
  | "profile"
  | "saved"
  | "tracker"
  | "history"
  | "settings";

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  savedCount: number;
  highMatchCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  savedCount,
  highMatchCount
}) => {
  const navItems = [
    {
      id: "dashboard" as NavTab,
      label: "Dashboard",
      icon: LayoutDashboard,
      badge: null
    },
    {
      id: "discover" as NavTab,
      label: "Discover Jobs",
      icon: Compass,
      badge: null
    },
    {
      id: "high_matches" as NavTab,
      label: "High Matches",
      icon: Sparkles,
      badge: highMatchCount > 0 ? highMatchCount : null,
      badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
    },
    {
      id: "profile" as NavTab,
      label: "My Career Profile",
      icon: UserCheck,
      badge: "AI Profile",
      badgeColor: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
    },
    {
      id: "saved" as NavTab,

      label: "Saved Jobs",
      icon: Bookmark,
      badge: savedCount > 0 ? savedCount : null,
      badgeColor: "bg-blue-500/20 text-blue-300 border-blue-500/30"
    },
    {
      id: "tracker" as NavTab,
      label: "Application Tracker",
      icon: Kanban,
      badge: null
    },
    {
      id: "history" as NavTab,
      label: "Search History",
      icon: History,
      badge: null
    },
    {
      id: "settings" as NavTab,
      label: "Settings",
      icon: Settings,
      badge: null
    }
  ];

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col justify-between h-screen sticky top-0 bg-slate-900/90 backdrop-blur-xl border-r border-slate-800 select-none z-30">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800/80 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/20 flex items-center justify-center">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
              HSE Career Agent
            </h1>
            <p className="text-xs text-slate-400 font-medium">Phase 1 &bull; Leadership Hub</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? "text-blue-400" : "text-slate-400"
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge !== null && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${
                      item.badgeColor || "bg-slate-800 text-slate-300 border-slate-700"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Executive Profile Widget */}
      <div className="p-4 m-3 rounded-xl bg-slate-950/70 border border-slate-800/80 shadow-inner">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center text-slate-950 font-bold text-xs shadow-md">
              RR
            </div>
            <div>
              <p className="text-xs font-bold text-white leading-tight">Raghunath Reddy</p>
              <p className="text-[11px] text-slate-400 truncate max-w-[120px]">
                Global SHE &amp; Security
              </p>
            </div>
          </div>
          <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold px-1.5 py-0.5 rounded">
            18+ Yrs
          </span>
        </div>

        <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1">
            <Building2 className="w-3 h-3 text-slate-500" />
            dsm-firmenich
          </span>
          <span className="text-cyan-400 font-medium">APAC/Global</span>
        </div>
      </div>
    </aside>
  );
};
