import React from "react";
import { Clock, Loader2, CheckCircle2, AlertCircle, ShieldAlert, XCircle } from "lucide-react";

interface TaskStatusBadgeProps {
  status: "pending" | "running" | "done" | "failed" | "pending_approval" | "rejected" | string;
  size?: "sm" | "md" | "lg";
}

export const TaskStatusBadge: React.FC<TaskStatusBadgeProps> = ({ status, size = "md" }) => {
  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-3 py-1 text-xs gap-1.5",
    lg: "px-4 py-1.5 text-sm gap-2",
  }[size];

  switch (status) {
    case "pending":
      return (
        <span
          className={`inline-flex items-center font-semibold rounded-full bg-slate-100 text-slate-600 border border-slate-300 ${sizeClasses}`}
        >
          <Clock className={size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} />
          <span>Pending</span>
        </span>
      );
    case "running":
      return (
        <span
          className={`inline-flex items-center font-bold rounded-full bg-sky-50 text-sky-800 border border-sky-300 shadow-xs animate-pulse ${sizeClasses}`}
        >
          <Loader2 className={`animate-spin ${size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} text-sky-700`} />
          <span>Running</span>
        </span>
      );
    case "pending_approval":
      return (
        <span
          className={`inline-flex items-center font-bold rounded-full bg-amber-50 text-amber-900 border border-amber-300 shadow-xs ${sizeClasses}`}
        >
          <ShieldAlert className={`${size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} text-amber-700`} />
          <span>Awaiting Approval</span>
        </span>
      );
    case "done":
      return (
        <span
          className={`inline-flex items-center font-bold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 ${sizeClasses}`}
        >
          <CheckCircle2 className={size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} />
          <span>Completed</span>
        </span>
      );
    case "rejected":
      return (
        <span
          className={`inline-flex items-center font-bold rounded-full bg-rose-50 text-rose-900 border border-rose-300 ${sizeClasses}`}
        >
          <XCircle className={`${size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} text-rose-700`} />
          <span>Rejected</span>
        </span>
      );
    case "failed":
      return (
        <span
          className={`inline-flex items-center font-bold rounded-full bg-rose-100 text-rose-800 border border-rose-300 ${sizeClasses}`}
        >
          <AlertCircle className={size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} />
          <span>Failed</span>
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center font-semibold rounded-full bg-slate-100 text-slate-700 border border-slate-300 ${sizeClasses}`}>
          {status}
        </span>
      );
  }
};
