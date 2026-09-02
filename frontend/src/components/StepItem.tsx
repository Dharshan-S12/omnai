import React, { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
import { ToolBadge } from "./ToolBadge";
import type { TaskStep } from "../api";

interface StepItemProps {
  step: TaskStep;
}

export const StepItem: React.FC<StepItemProps> = ({ step }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const hasResult = step.tool_result !== null && step.tool_result !== undefined;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!hasResult) return;
    navigator.clipboard.writeText(JSON.stringify(step.tool_result, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="relative flex items-start gap-4 group transition-all">
      {/* Timeline Node Icon */}
      <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-white border-2 border-emerald-700 text-emerald-800 font-mono text-xs font-bold shadow-xs shrink-0 mt-0.5 group-hover:border-emerald-600 transition-colors">
        {step.step_number}
      </div>

      {/* Step Content Card */}
      <div className="flex-1 bg-white hover:bg-slate-50/80 border border-slate-200 rounded-xl p-4 transition-all shadow-xs">
        <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs text-slate-500 font-semibold">Step {step.step_number}</span>
            <ToolBadge tool={step.tool_called} />
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            {formatTime(step.created_at)}
          </span>
        </div>

        <p className="text-slate-800 text-sm leading-relaxed mb-1 font-sans">
          {step.description}
        </p>

        {/* Expandable Tool Result JSON */}
        {hasResult && (
          <div className="mt-3 border border-slate-200 rounded-lg overflow-hidden bg-slate-50 transition-all">
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full px-3 py-2 flex items-center justify-between text-xs font-mono text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                {expanded ? (
                  <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
                )}
                <span>Tool Execution Output</span>
                <span className="text-[10px] text-slate-500 bg-white border border-slate-200 px-1.5 py-0.2 rounded">
                  {typeof step.tool_result === "object"
                    ? `${Object.keys(step.tool_result).length} keys`
                    : "raw data"}
                </span>
              </div>

              {expanded && (
                <button
                  onClick={handleCopy}
                  title="Copy JSON"
                  className="flex items-center gap-1 text-[11px] text-slate-600 hover:text-emerald-800 px-2 py-0.5 rounded hover:bg-slate-200 transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-600" />
                      <span className="text-emerald-700">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              )}
            </button>

            {expanded && (
              <pre className="p-3 text-xs font-mono text-emerald-950 bg-emerald-50/50 overflow-x-auto max-h-72 border-t border-slate-200 leading-relaxed">
                {JSON.stringify(step.tool_result, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
