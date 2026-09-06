import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Link2,
  FileText,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { fetchTaskDetails } from "../api";
import { TaskStatusBadge } from "../components/TaskStatusBadge";
import { TaskTypeBadge } from "../components/TaskTypeBadge";
import { StepTimeline } from "../components/StepTimeline";
import { TaskOutputView } from "../components/TaskOutputView";
import type { TaskItem } from "../api";

export default function TaskDetailView() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<TaskItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    setError(null);

    let timer: ReturnType<typeof setTimeout> | null = null;
    let isMounted = true;

    const pollTask = async () => {
      try {
        const data = await fetchTaskDetails(id);
        if (isMounted) {
          setTask(data);
          setLoading(false);
          setError(null);
        }

        // Continue polling every 1.5s only while status is pending or running
        if (isMounted && (data.status === "pending" || data.status === "running")) {
          timer = setTimeout(pollTask, 1500);
        }
      } catch (err: any) {
        console.error("Error polling task details:", err);
        if (isMounted) {
          setError(err.message || "Failed to load task");
          setLoading(false);
        }
      }
    };

    pollTask();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  // Initial Loading Skeleton
  if (loading && !task) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-6 animate-pulse">
        <div className="h-5 w-32 bg-slate-200 rounded-lg mb-6" />
        <div className="h-28 bg-white border border-slate-200 rounded-2xl mb-6 p-6">
          <div className="h-6 w-48 bg-slate-200 rounded mb-3" />
          <div className="h-4 w-96 bg-slate-100 rounded" />
        </div>
        <div className="h-64 bg-white border border-slate-200 rounded-2xl" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-6 text-center">
        <div className="p-8 bg-white border border-rose-200 rounded-2xl shadow-xs">
          <h3 className="text-base font-bold text-rose-800 mb-2">Error Loading Task</h3>
          <p className="text-sm text-slate-600 mb-6">{error || "Task not found."}</p>
          <Link
            to="/tasks"
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-semibold transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> Return to Task Queue
          </Link>
        </div>
      </div>
    );
  }

  const isRunning = task.status === "running" || task.status === "pending";

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-6 md:px-8">
      {/* Back Button */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          to="/tasks"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-emerald-800 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Task Queue</span>
        </Link>

        {isRunning && (
          <span className="text-[11px] font-mono text-sky-800 flex items-center gap-1.5 bg-sky-50 border border-sky-300 px-3 py-1 rounded-full animate-pulse font-bold">
            <RefreshCw className="h-3 w-3 animate-spin text-sky-600" />
            <span>Live Polling (1.5s interval)</span>
          </span>
        )}
      </div>

      {/* Task Header Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6 shadow-xs">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h2 className="text-xl font-bold text-slate-900 font-sans flex items-center gap-2">
                <span>Task</span>
                <span className="font-mono text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-lg border border-emerald-200 text-sm">
                  #{task.id}
                </span>
              </h2>
              <TaskTypeBadge type={task.task_type} />
              <TaskStatusBadge status={task.status} />
              {task.confidence_score !== null && task.confidence_score !== undefined && (
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border ${
                  task.confidence_score >= 80 
                    ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                    : task.confidence_score >= 50
                    ? "bg-amber-50 text-amber-900 border-amber-300"
                    : "bg-rose-50 text-rose-900 border-rose-300"
                }`}>
                  <span className={`h-2 w-2 rounded-full ${
                    task.confidence_score >= 80 ? "bg-emerald-500" : task.confidence_score >= 50 ? "bg-amber-500" : "bg-rose-500"
                  }`} />
                  <span>Confidence: {task.confidence_score}%</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-500 font-mono flex-wrap">
              <span className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-400" />
                Created: {formatDate(task.created_at)}
              </span>
              {task.updated_at && (
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  Updated: {formatDate(task.updated_at)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Input Reference / Prompt Banner */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mt-4">
          <div className="text-[11px] font-mono uppercase text-slate-500 mb-1 flex items-center gap-1.5 font-bold">
            <FileText className="h-3.5 w-3.5 text-slate-500" />
            <span>Task Input / Objective:</span>
          </div>
          <p className="text-sm text-slate-800 font-sans leading-relaxed font-medium">
            {task.input_ref}
          </p>

          {/* Upstream Chained Task Link if present */}
          {task.source_task_id && (
            <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-600 flex items-center gap-1.5">
                <Link2 className="h-3.5 w-3.5 text-emerald-700" />
                Chained Source Task:
              </span>
              <Link
                to={`/task/${task.source_task_id}`}
                className="text-emerald-800 hover:text-emerald-950 font-bold underline flex items-center gap-1"
              >
                <span>#{task.source_task_id.slice(0, 8)} (View Upstream OCR)</span>
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Semantic Cache Hit Banner */}
      {(() => {
        const cacheHitStep = task.steps?.find((s) => s.tool_called === "semantic_cache_hit");
        if (!cacheHitStep) return null;
        const sim = cacheHitStep.tool_result?.similarity
          ? Math.round(cacheHitStep.tool_result.similarity * 100)
          : 95;
        const matchedId = cacheHitStep.tool_result?.matched_task_id;
        return (
          <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-3.5 mb-6 shadow-xs flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2.5">
              <span className="p-1.5 bg-emerald-100 text-emerald-800 rounded-lg">
                <RefreshCw className="h-4 w-4 text-emerald-700" />
              </span>
              <div>
                <p className="text-xs font-bold text-emerald-900 font-mono">
                  ⚡ Served from Semantic Response Cache ({sim}% match to prior analysis)
                </p>
                <p className="text-[11px] text-emerald-700">
                  Instant response served from sovereign vector cache. Fresh supervisor sign-off is still enforced below.
                </p>
              </div>
            </div>
            {matchedId && (
              <Link
                to={`/task/${matchedId}`}
                className="text-xs font-mono font-bold text-emerald-800 hover:text-emerald-950 underline inline-flex items-center gap-1"
              >
                <span>Origin Task #{matchedId.slice(0, 8)}</span>
                <ExternalLink className="h-3 w-3" />
              </Link>
            )}
          </div>
        );
      })()}

      {/* Centerpiece: Step Timeline */}
      <StepTimeline steps={task.steps || []} isRunning={isRunning} />

      {/* Final Output Panel */}
      <TaskOutputView
        task={task}
        onTaskUpdated={async () => {
          if (id) {
            try {
              const updated = await fetchTaskDetails(id);
              setTask(updated);
            } catch (err) {
              console.error("Error refreshing task details:", err);
            }
          }
        }}
      />
    </div>
  );
}
