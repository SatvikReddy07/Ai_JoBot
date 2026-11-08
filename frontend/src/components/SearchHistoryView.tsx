import React from "react";
import { History, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { SearchHistoryItem } from "../types";

interface SearchHistoryViewProps {
  history: SearchHistoryItem[];
}

export const SearchHistoryView: React.FC<SearchHistoryViewProps> = ({ history }) => {
  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <History className="w-4 h-4 text-blue-400" />
            Job Search Execution History
          </h3>
          <p className="text-xs text-slate-400">
            Log of manual and automated daily searches executed by the discovery engine.
          </p>
        </div>
        <span className="text-xs bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 font-mono">
          {history.length} Search Runs Recorded
        </span>
      </div>

      {/* History Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
            <tr>
              <th className="py-3 px-4 font-semibold">Timestamp</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold">Boards Checked</th>
              <th className="py-3 px-4 font-semibold">New Jobs</th>
              <th className="py-3 px-4 font-semibold">Updated/Verified</th>
              <th className="py-3 px-4 font-semibold">Notes / Diagnostics</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {history.map((run) => (
              <tr key={run.id} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-3.5 px-4 text-slate-300 font-mono">
                  {new Date(run.started_at).toLocaleString()}
                </td>
                <td className="py-3.5 px-4">
                  <span className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                    run.status === "success"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                  }`}>
                    {run.status === "success" ? (
                      <>
                        <CheckCircle className="w-3 h-3" />
                        <span>Success</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-3 h-3" />
                        <span>Failed / Partial</span>
                      </>
                    )}
                  </span>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-300">
                  {run.boards_searched} boards
                </td>
                <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                  +{run.jobs_new}
                </td>
                <td className="py-3.5 px-4 font-mono text-blue-400">
                  {run.jobs_updated}
                </td>
                <td className="py-3.5 px-4 text-slate-400 max-w-lg whitespace-pre-wrap break-words" title={run.error_message || ""}>
                  {run.error_message ? (
                    <span className="text-amber-400/90">{run.error_message}</span>
                  ) : (
                    <span className="text-slate-500">All queries completed normally</span>
                  )}
                </td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 italic">
                  No search runs recorded yet. Click &quot;Search Jobs Now&quot; to execute your first live discovery run.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
