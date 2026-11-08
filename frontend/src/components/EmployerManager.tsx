import React, { useState } from "react";
import {
  Building2,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Sliders,
  ExternalLink
} from "lucide-react";
import { EmployerBoard } from "../types";
import { addEmployer, updateEmployer, deleteEmployer, runSearchNow } from "../lib/api";

interface EmployerManagerProps {
  employers: EmployerBoard[];
  onRefresh: () => void;
}

export const EmployerManager: React.FC<EmployerManagerProps> = ({
  employers,
  onRefresh
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCompany, setNewCompany] = useState("");
  const [newPlatform, setNewPlatform] = useState<"greenhouse" | "lever">("greenhouse");
  const [newToken, setNewToken] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [testingBoardId, setTestingBoardId] = useState<number | null>(null);

  const handleAddBoard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompany.trim() || !newToken.trim()) {
      setErrorMessage("Company name and board token are required.");
      return;
    }
    setErrorMessage("");
    setIsSubmitting(true);

    try {
      await addEmployer({
        company_name: newCompany.trim(),
        platform: newPlatform,
        board_token: newToken.trim().toLowerCase(),
        is_enabled: true
      });
      setShowAddModal(false);
      setNewCompany("");
      setNewToken("");
      onRefresh();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to add board.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleEnable = async (board: EmployerBoard) => {
    try {
      await updateEmployer(board.id, { is_enabled: !board.is_enabled });
      onRefresh();
    } catch (err: any) {
      alert("Error toggling board: " + err.message);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (confirm(`Are you sure you want to delete '${name}'?`)) {
      try {
        await deleteEmployer(id);
        onRefresh();
      } catch (err: any) {
        alert("Error deleting board: " + err.message);
      }
    }
  };

  const handleTestBoard = async (id: number) => {
    setTestingBoardId(id);
    try {
      const res = await runSearchNow(id);
      alert(`Search completed for board: ${res.message}`);
      onRefresh();
    } catch (err: any) {
      alert("Search failed: " + err.message);
    } finally {
      setTestingBoardId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-400" />
            Configured Employer Career Feeds
          </h3>
          <p className="text-xs text-slate-400">
            Manage public Greenhouse and Lever feeds. These cover selected employers, not the whole job market. A listed job still needs eligibility review.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add Employer Feed</span>
        </button>
      </div>

      {/* Employers Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
            <tr>
              <th className="py-3 px-4 font-semibold">Company Name</th>
              <th className="py-3 px-4 font-semibold">Platform</th>
              <th className="py-3 px-4 font-semibold">Board Token</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold">Last Checked</th>
              <th className="py-3 px-4 font-semibold">Postings in Feed</th>
              <th className="py-3 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {employers.map((board) => (
              <tr key={board.id} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-3.5 px-4 font-semibold text-white">
                  {board.company_name}
                  <p className="text-[11px] text-slate-400 font-normal mt-1 whitespace-normal break-words">{board.last_status || "Not checked"}</p>
                </td>
                <td className="py-3.5 px-4">
                  <span className={`text-[11px] px-2 py-0.5 rounded font-mono uppercase ${
                    board.platform === "greenhouse"
                      ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                      : "bg-purple-500/10 text-purple-300 border border-purple-500/20"
                  }`}>
                    {board.platform}
                  </span>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                  {board.board_token}
                </td>
                <td className="py-3.5 px-4">
                  <button
                    onClick={() => handleToggleEnable(board)}
                    className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-colors ${
                      board.is_enabled
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
                        : "bg-slate-800 text-slate-500 border-slate-700 hover:bg-slate-700"
                    }`}
                  >
                    {board.is_enabled ? (
                      <>
                        <CheckCircle className="w-3 h-3 text-emerald-400" />
                        <span>Enabled</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3 h-3 text-slate-500" />
                        <span>Disabled</span>
                      </>
                    )}
                  </button>
                </td>
                <td className="py-3.5 px-4 text-slate-400">
                  {board.last_searched_at ? (
                    <span>{new Date(board.last_searched_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
                  ) : (
                    <span className="text-slate-600">Pending initial search</span>
                  )}
                </td>
                <td className="py-3.5 px-4 font-mono font-medium text-slate-300">
                  {board.last_job_count || 0}
                </td>
                <td className="py-3.5 px-4 text-right">
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      onClick={() => handleTestBoard(board.id)}
                      disabled={testingBoardId === board.id}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                      title="Run search for this feed"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${testingBoardId === board.id ? "animate-spin text-blue-400" : ""}`} />
                    </button>
                    <button
                      onClick={() => handleDelete(board.id, board.company_name)}
                      className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-colors"
                      title="Delete feed"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Board Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Add Employer Career Feed</h3>
            <p className="text-xs text-slate-400">
              Provide the employer name and public board token from Greenhouse or Lever.
            </p>

            {errorMessage && (
              <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {errorMessage}
              </div>
            )}

            <form onSubmit={handleAddBoard} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Company Name</label>
                <input
                  type="text"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                  placeholder="e.g. Stripe, Figma, Deliveroo"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Platform</label>
                <select
                  value={newPlatform}
                  onChange={(e) => setNewPlatform(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="greenhouse">Greenhouse (boards-api.greenhouse.io)</option>
                  <option value="lever">Lever (api.lever.co)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Board Token / Slug</label>
                <input
                  type="text"
                  value={newToken}
                  onChange={(e) => setNewToken(e.target.value)}
                  placeholder="e.g. stripe, deliveroo, figma"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
                  required
                />
                <p className="mt-1 text-[11px] text-slate-500">
                  The URL identifier (e.g., from boards.greenhouse.io/&lt;token&gt;).
                </p>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? "Adding..." : "Add Feed"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
