import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ListOrdered,
  Plus,
  ArrowRight,
  Inbox,
  Link2,
  RefreshCw,
  ShieldAlert,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { fetchTasks } from "../api";
import { TaskStatusBadge } from "../components/TaskStatusBadge";
import { TaskTypeBadge } from "../components/TaskTypeBadge";
import type { TaskItem } from "../api";

export default function TaskListView() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const loadData = async () => {
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (err) {
      console.error("Error fetching tasks:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2500); // Poll every 2.5s
    return () => clearInterval(interval);
  }, []);

  const handleManualRefresh = () => {
    setIsRefreshing(true);
    loadData();
  };

  const pendingApprovalCount = tasks.filter((t) => t.status === "pending_approval").length;
  const runningCount = tasks.filter((t) => t.status === "running" || t.status === "pending").length;
  const doneCount = tasks.filter((t) => t.status === "done").length;
  const failedOrRejectedCount = tasks.filter((t) => t.status === "failed" || t.status === "rejected").length;

  const filteredTasks = tasks.filter((t) => {
    if (statusFilter === "all") return true;
    if (statusFilter === "pending_approval") return t.status === "pending_approval";
    if (statusFilter === "done") return t.status === "done";
    if (statusFilter === "running") return t.status === "running" || t.status === "pending";
    if (statusFilter === "failed_rejected") return t.status === "failed" || t.status === "rejected";
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto py-8 px-6 md:px-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              MRPL Execution Log
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-3 font-sans mt-1">
            <ListOrdered className="h-6 w-6 text-emerald-700" />
            <span>Sovereign Task Queue</span>
          </h2>
          <p className="text-sm text-slate-600 mt-0.5 font-sans">
            Real-time execution log of air-gapped agent runs, vision extractions, and document generators.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleManualRefresh}
            className="p-2.5 bg-white hover:bg-slate-50 text-slate-600 hover:text-emerald-900 border border-slate-200 rounded-xl transition-colors cursor-pointer shadow-xs"
            title="Refresh queue"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin text-emerald-700" : ""}`} />
          </button>

          <Link
            to="/upload"
            className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-md shadow-emerald-900/20 transition-all cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            <span>Process New Document</span>
          </Link>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1 text-xs font-mono">
        <button
          onClick={() => setStatusFilter("all")}
          className={`px-3 py-1.5 rounded-xl transition-all font-semibold flex items-center gap-1.5 cursor-pointer border ${
            statusFilter === "all"
              ? "bg-slate-900 text-white border-slate-900"
              : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <span>All Tasks</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === "all" ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-600"}`}>
            {tasks.length}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("pending_approval")}
          className={`px-3 py-1.5 rounded-xl transition-all font-semibold flex items-center gap-1.5 cursor-pointer border ${
            statusFilter === "pending_approval"
              ? "bg-amber-500 text-slate-900 border-amber-600 font-bold"
              : "bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100"
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5 text-amber-700" />
          <span>Awaiting Approval</span>
          {pendingApprovalCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-600 text-white font-bold animate-pulse">
              {pendingApprovalCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setStatusFilter("done")}
          className={`px-3 py-1.5 rounded-xl transition-all font-semibold flex items-center gap-1.5 cursor-pointer border ${
            statusFilter === "done"
              ? "bg-emerald-700 text-white border-emerald-700"
              : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          <span>Completed</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === "done" ? "bg-emerald-800 text-white" : "bg-slate-100 text-slate-600"}`}>
            {doneCount}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("running")}
          className={`px-3 py-1.5 rounded-xl transition-all font-semibold flex items-center gap-1.5 cursor-pointer border ${
            statusFilter === "running"
              ? "bg-sky-600 text-white border-sky-600"
              : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Clock className="h-3.5 w-3.5 text-sky-600" />
          <span>Running / Pending</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === "running" ? "bg-sky-700 text-white" : "bg-slate-100 text-slate-600"}`}>
            {runningCount}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("failed_rejected")}
          className={`px-3 py-1.5 rounded-xl transition-all font-semibold flex items-center gap-1.5 cursor-pointer border ${
            statusFilter === "failed_rejected"
              ? "bg-rose-700 text-white border-rose-700"
              : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <span>Failed / Rejected</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === "failed_rejected" ? "bg-rose-800 text-white" : "bg-slate-100 text-slate-600"}`}>
            {failedOrRejectedCount}
          </span>
        </button>
      </div>

      {/* Table Container */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-mono uppercase tracking-wider text-slate-600">
              <th className="px-6 py-3.5 font-bold">Task ID</th>
              <th className="px-6 py-3.5 font-bold">Agent Mode</th>
              <th className="px-6 py-3.5 font-bold">Goal / Input Reference</th>
              <th className="px-6 py-3.5 font-bold">Status</th>
              <th className="px-6 py-3.5 font-bold">Confidence</th>
              <th className="px-6 py-3.5 font-bold">Timestamp</th>
              <th className="px-6 py-3.5 text-right font-bold">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && tasks.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-16 text-center text-slate-500 font-mono text-xs">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="h-6 w-6 text-emerald-700 animate-spin" />
                    <span>Loading MRPL agent queue...</span>
                  </div>
                </td>
              </tr>
            ) : filteredTasks.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-16 text-center text-slate-500 font-sans">
                  <div className="max-w-md mx-auto flex flex-col items-center justify-center text-center">
                    <div className="h-12 w-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 mb-3 border border-slate-200">
                      <Inbox className="h-6 w-6" />
                    </div>
                    <h3 className="text-sm font-semibold text-slate-800 mb-1">No tasks in this view</h3>
                    <p className="text-xs text-slate-500 mb-4 leading-relaxed">
                      No matching tasks found for the selected filter.
                    </p>
                    <Link
                      to="/upload"
                      className="text-xs font-semibold text-emerald-900 hover:text-emerald-950 bg-emerald-50 border border-emerald-300 px-4 py-2 rounded-xl transition-colors"
                    >
                      + Start First Task
                    </Link>
                  </div>
                </td>
              </tr>
            ) : (
              filteredTasks.map((task) => (
                <tr
                  key={task.id}
                  onClick={() => navigate(`/task/${task.id}`)}
                  className={`transition-colors cursor-pointer group ${
                    task.status === "pending_approval"
                      ? "bg-amber-50/40 hover:bg-amber-50/80"
                      : "hover:bg-slate-50"
                  }`}
                >
                  {/* Task ID */}
                  <td className="px-6 py-4 font-mono text-xs text-slate-600">
                    <span className="font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
                      #{task.id.slice(0, 8)}
                    </span>
                  </td>

                  {/* Task Type */}
                  <td className="px-6 py-4">
                    <TaskTypeBadge type={task.task_type} size="sm" />
                  </td>

                  {/* Input / Goal Preview */}
                  <td className="px-6 py-4 max-w-xs">
                    <div className="text-xs text-slate-800 truncate font-sans font-medium">
                      {task.input_ref}
                    </div>
                    {task.source_task_id && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-800 font-mono mt-0.5">
                        <Link2 className="h-2.5 w-2.5" />
                        Chained from #{task.source_task_id.slice(0, 8)}
                      </span>
                    )}
                  </td>

                  {/* Status Badge */}
                  <td className="px-6 py-4">
                    <TaskStatusBadge status={task.status} size="sm" />
                  </td>

                  {/* Confidence Score */}
                  <td className="px-6 py-4">
                    {task.confidence_score !== null && task.confidence_score !== undefined ? (
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${
                          task.confidence_score >= 80
                            ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                            : task.confidence_score >= 50
                            ? "bg-amber-50 text-amber-900 border-amber-300"
                            : "bg-rose-50 text-rose-900 border-rose-300"
                        }`}
                      >
                        <span>{task.confidence_score}%</span>
                      </span>
                    ) : (
                      <span className="text-slate-400 font-mono text-xs">—</span>
                    )}
                  </td>

                  {/* Timestamp */}
                  <td className="px-6 py-4 text-xs font-mono text-slate-500">
                    {new Date(task.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </td>

                  {/* View Trace Action */}
                  <td className="px-6 py-4 text-right">
                    <span className="inline-flex items-center gap-1 text-emerald-700 group-hover:text-emerald-900 text-xs font-semibold group-hover:translate-x-0.5 transition-all">
                      <span>View Trace</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
