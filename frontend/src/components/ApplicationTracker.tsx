import React, { useState } from "react";
import {
  Kanban,
  ExternalLink,
  Eye,
  MapPin,
  Building2,
  Calendar,
  Sparkles,
  FileText
} from "lucide-react";
import { Job } from "../types";

interface ApplicationTrackerProps {
  jobs: Job[];
  onSelectJob: (job: Job) => void;
  onStatusChange: (jobId: number, status: string) => void;
}

export const ApplicationTracker: React.FC<ApplicationTrackerProps> = ({
  jobs,
  onSelectJob,
  onStatusChange
}) => {
  const lanes = [
    { id: "Saved", label: "Saved / Shortlisted", color: "border-blue-500/30 bg-blue-500/5 text-blue-400" },
    { id: "Interested", label: "Interested", color: "border-cyan-500/30 bg-cyan-500/5 text-cyan-400" },
    { id: "Ready to Apply", label: "Ready to Apply", color: "border-amber-500/30 bg-amber-500/5 text-amber-400" },
    { id: "Applied", label: "Applied", color: "border-indigo-500/30 bg-indigo-500/5 text-indigo-400" },
    { id: "Interview", label: "Interview", color: "border-emerald-500/30 bg-emerald-500/5 text-emerald-400" },
    { id: "Offer", label: "Offer", color: "border-emerald-400 bg-emerald-400/10 text-emerald-300 font-bold" },
    { id: "Closed", label: "Closed / Archived", color: "border-slate-700 bg-slate-800/20 text-slate-400" }
  ];

  const getScoreBadge = (score: number) => {
    if (score >= 85) return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    if (score >= 75) return "bg-blue-500/20 text-blue-300 border-blue-500/30";
    if (score >= 60) return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    return "bg-slate-500/20 text-slate-300 border-slate-500/30";
  };

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Kanban className="w-4 h-4 text-blue-400" />
            Executive Application Pipeline
          </h3>
          <p className="text-xs text-slate-400">
            Track your progress across opportunities from initial discovery to active interviews and offers.
          </p>
        </div>
        <span className="text-xs bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 font-medium">
          Total in Active Pipeline: {jobs.filter(j => j.application_status !== "Discovered").length}
        </span>
      </div>

      {/* Kanban Board Container */}
      <div className="flex space-x-4 overflow-x-auto pb-6">
        {lanes.map((lane) => {
          const laneJobs = jobs.filter((j) => j.application_status === lane.id);

          return (
            <div
              key={lane.id}
              className="w-80 flex-shrink-0 flex flex-col bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden max-h-[75vh]"
            >
              {/* Lane Header */}
              <div className={`p-3 border-b flex items-center justify-between ${lane.color}`}>
                <span className="text-xs font-bold tracking-tight">{lane.label}</span>
                <span className="text-xs bg-slate-950/60 px-2 py-0.5 rounded-full border border-slate-700/60 font-mono">
                  {laneJobs.length}
                </span>
              </div>

              {/* Lane Cards */}
              <div className="p-2.5 space-y-2.5 overflow-y-auto flex-1">
                {laneJobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => onSelectJob(job)}
                    className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition-all cursor-pointer shadow-sm space-y-2 group"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getScoreBadge(job.match_score)}`}>
                        {job.match_score} pts
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono uppercase">
                        {job.source}
                      </span>
                    </div>

                    <h4 className="text-xs font-bold text-white group-hover:text-blue-400 transition-colors line-clamp-2">
                      {job.title}
                    </h4>

                    <div className="space-y-1 text-[11px] text-slate-400">
                      <div className="flex items-center space-x-1 text-slate-300">
                        <Building2 className="w-3 h-3 text-slate-500 flex-shrink-0" />
                        <span className="truncate">{job.company}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <MapPin className="w-3 h-3 text-slate-500 flex-shrink-0" />
                        <span className="truncate">{job.country || job.location}</span>
                      </div>
                    </div>

                    {job.application_notes && (
                      <div className="pt-1.5 border-t border-slate-800/80 text-[10px] text-slate-400 line-clamp-2 italic">
                        &quot;{job.application_notes}&quot;
                      </div>
                    )}

                    {/* Move Status Selector */}
                    <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                      <label className="text-[10px] text-slate-500 font-medium">Move to:</label>
                      <select
                        value={job.application_status}
                        onChange={(e) => onStatusChange(job.id, e.target.value)}
                        className="bg-slate-900 text-[10px] font-medium text-slate-300 px-2 py-0.5 rounded border border-slate-800 focus:outline-none focus:border-blue-500"
                      >
                        {lanes.map((l) => (
                          <option key={l.id} value={l.id}>{l.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}

                {laneJobs.length === 0 && (
                  <div className="p-6 text-center text-slate-600 text-xs italic">
                    No roles in this stage
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
