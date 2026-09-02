import React from "react";
import { Terminal, Loader2 } from "lucide-react";
import { StepItem } from "./StepItem";
import type { TaskStep } from "../api";

interface StepTimelineProps {
  steps: TaskStep[];
  isRunning?: boolean;
}

export const StepTimeline: React.FC<StepTimelineProps> = ({ steps, isRunning = false }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
      {/* Header */}
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
            <Terminal className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 font-sans tracking-wide">
              Agent Execution Trace
            </h3>
            <p className="text-[11px] text-emerald-800 font-mono font-medium">
              {steps.length} step{steps.length === 1 ? "" : "s"} recorded in on-premise ledger
            </p>
          </div>
        </div>

        {isRunning && (
          <div className="flex items-center gap-2 text-xs font-mono text-sky-800 bg-sky-50 border border-sky-300 px-3 py-1 rounded-full animate-pulse">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-600" />
            <span>Agent Reasoning & Tool Execution...</span>
          </div>
        )}
      </div>

      {/* Timeline Body */}
      <div className="p-6">
        {steps.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center text-center">
            {isRunning ? (
              <>
                <Loader2 className="h-8 w-8 text-sky-600 animate-spin mb-3" />
                <p className="text-sm font-medium text-slate-800">Initializing MRPL Sovereign Agent Loop...</p>
                <p className="text-xs text-slate-500 mt-1 font-mono">Formulating execution plan with local models</p>
              </>
            ) : (
              <p className="text-sm text-slate-500 font-mono">No steps recorded for this task.</p>
            )}
          </div>
        ) : (
          <div className="relative">
            {/* Continuous Vertical Line */}
            <div className="absolute top-4 bottom-4 left-[15px] w-0.5 bg-gradient-to-b from-emerald-600 via-slate-300 to-slate-200 pointer-events-none" />

            {/* Steps Container */}
            <div className="space-y-6">
              {steps.map((step, idx) => (
                <StepItem
                  key={step.id || `step-${step.step_number}-${idx}`}
                  step={step}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
