import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Scale,
  Users
} from "lucide-react";
import { ToolBadge } from "./ToolBadge";
import type { TaskStep } from "../api";

interface StepItemProps {
  step: TaskStep;
  showRawTrace?: boolean;
}

export const StepItem: React.FC<StepItemProps> = ({ step, showRawTrace = false }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const hasResult = step.tool_result !== null && step.tool_result !== undefined;
  const isRuleEngine = step.tool_called === "rule_engine_check" && step.tool_result?.evaluated;
  const isEnsemble = step.tool_called === "compliance_ensemble" && Array.isArray(step.tool_result?.individual_verdicts);
  const isVerifier = step.tool_called === "verifier_safety_grounding" && step.tool_result?.safety_grounding_confidence !== undefined;

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

        {/* --------------------------------------------------------- */}
        {/* CUSTOM RICH UI: DETERMINISTIC RULE ENGINE PASS/FAIL TABLE */}
        {/* --------------------------------------------------------- */}
        {isRuleEngine && (
          <div className="mt-3 bg-white border border-emerald-200 rounded-xl overflow-hidden shadow-xs">
            {/* Header Banner */}
            <div className="bg-emerald-50/70 px-4 py-3 border-b border-emerald-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div className="flex items-center gap-2">
                <Scale className="h-4 w-4 text-emerald-700" />
                <span className="text-xs font-bold font-mono text-emerald-950 uppercase tracking-tight">
                  Deterministic Rule Evaluation Ledger
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white text-emerald-800 border border-emerald-300 font-semibold">
                  Standard: {step.tool_result.sop_reference || "Refinery SOP"}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {step.tool_result.is_borderline && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                    <AlertTriangle className="h-3 w-3 text-amber-700" />
                    <span>Borderline Proximity (≤10%)</span>
                  </span>
                )}
                <span
                  className={`inline-flex items-center gap-1 text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${
                    step.tool_result.overall_verdict === "NON_COMPLIANT"
                      ? "bg-rose-50 text-rose-700 border-rose-300"
                      : step.tool_result.overall_verdict === "NEEDS_REVIEW"
                      ? "bg-amber-50 text-amber-800 border-amber-300"
                      : "bg-emerald-100 text-emerald-900 border-emerald-300"
                  }`}
                >
                  {step.tool_result.overall_verdict === "NON_COMPLIANT" ? (
                    <XCircle className="h-3.5 w-3.5 text-rose-600" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  )}
                  <span>{step.tool_result.overall_verdict}</span>
                </span>
              </div>
            </div>

            {/* Structured Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-sans">
                <thead className="bg-slate-50 text-slate-600 font-mono uppercase text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2.5 font-bold">Parameter / Field</th>
                    <th className="px-3 py-2.5 font-bold">Observed Value</th>
                    <th className="px-3 py-2.5 font-bold">Operator & Threshold</th>
                    <th className="px-3 py-2.5 font-bold">Classification / Zone</th>
                    <th className="px-4 py-2.5 font-bold text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                  {step.tool_result.rule_results?.map((r: any, idx: number) => (
                    <tr key={idx} className={r.passed ? "hover:bg-slate-50/60" : "bg-rose-50/30 hover:bg-rose-50/50"}>
                      <td className="px-4 py-2.5">
                        <div className="font-semibold text-slate-900">{r.field_label || r.field}</div>
                        <div className="text-[10px] font-mono text-slate-400">{r.field} ({r.sop_reference})</div>
                      </td>
                      <td className="px-3 py-2.5 font-mono font-bold text-slate-900">
                        {r.actual_value}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-slate-600">
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-800 font-bold">
                          {r.operator} {r.threshold}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-xs">
                        <span className="text-slate-800 font-medium">{r.zone_label}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        {r.passed ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            <Check className="h-3 w-3 text-emerald-600" />
                            <span>PASS</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                            <XCircle className="h-3 w-3 text-rose-600" />
                            <span>FAIL</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Footer Note */}
            <div className="px-4 py-2 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-500">
              <span>Pure deterministic comparison in Python (<span className="font-semibold text-slate-700">Zero LLM variance</span>)</span>
              <span>
                {step.tool_result.rules_passed} Passed • {step.tool_result.rules_failed} Failed
              </span>
            </div>
          </div>
        )}

        {/* --------------------------------------------------------- */}
        {/* CUSTOM RICH UI: SELF-CONSISTENCY COMPLIANCE ENSEMBLE CARD */}
        {/* --------------------------------------------------------- */}
        {isEnsemble && (
          <div className="mt-3 bg-white border border-amber-200 rounded-xl overflow-hidden shadow-xs p-4 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-amber-700" />
                <span className="text-xs font-bold font-mono text-amber-950 uppercase">
                  Diverse Multi-Model Ensemble Voting (3 Configurations)
                </span>
              </div>
              <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${
                step.tool_result.is_unanimous
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-amber-50 text-amber-800 border-amber-300"
              }`}>
                {step.tool_result.is_unanimous ? "Unanimous Consensus (3/3)" : "Dissent Logged (Majority Split)"}
              </span>
            </div>

            {/* 3 Runs Pills */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {step.tool_result.individual_verdicts?.map((v: string, idx: number) => {
                const isNonComp = v.includes("NON");
                const configLabel = idx === 0 ? "Qwen 7B (T=0.0)" : idx === 1 ? "Qwen 7B (T=0.3)" : "Qwen 3B (T=0.7)";
                return (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-lg border flex flex-col justify-between ${
                      isNonComp ? "bg-rose-50/50 border-rose-200" : "bg-emerald-50/50 border-emerald-200"
                    }`}
                  >
                    <span className="text-[10px] font-mono uppercase text-slate-500 font-bold">
                      Config #{idx + 1}: {configLabel}
                    </span>
                    <span className={`text-xs font-mono font-bold mt-1 ${isNonComp ? "text-rose-700" : "text-emerald-800"}`}>
                      {v}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600 flex-wrap gap-1">
              <span className="font-semibold text-slate-800">
                Consensus Outcome: <span className="font-mono text-amber-900 font-bold">{step.tool_result.majority_verdict}</span>
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                {step.tool_result.trigger_reason}
              </span>
            </div>
          </div>
        )}

        {/* --------------------------------------------------------- */}
        {/* CUSTOM RICH UI: VERIFIER EXPLAINABLE GROUNDING BREAKDOWN  */}
        {/* --------------------------------------------------------- */}
        {isVerifier && (
          <div className="mt-3 bg-white border border-emerald-200 rounded-xl overflow-hidden shadow-xs p-4 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Scale className="h-4 w-4 text-emerald-700" />
                <span className="text-xs font-bold font-mono text-emerald-950 uppercase">
                  Safety Grounding Verification Breakdown
                </span>
              </div>
              <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${
                step.tool_result.safety_grounding_confidence >= 80
                  ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                  : step.tool_result.safety_grounding_confidence >= 50
                  ? "bg-amber-50 text-amber-900 border-amber-300"
                  : "bg-rose-50 text-rose-900 border-rose-300"
              }`}>
                Grounding Score: {step.tool_result.safety_grounding_confidence}%
              </span>
            </div>

            {/* Grounding Deductions List */}
            {step.tool_result.grounding_breakdown?.deductions && step.tool_result.grounding_breakdown.deductions.length > 0 ? (
              <div className="bg-amber-50/60 border border-amber-200 rounded-lg p-3 space-y-2">
                <span className="text-[11px] font-mono font-bold text-amber-900 block uppercase">
                  Grounding Deductions Identified:
                </span>
                <div className="space-y-1.5">
                  {step.tool_result.grounding_breakdown.deductions.map((ded: string, dIdx: number) => (
                    <div key={dIdx} className="text-xs text-amber-950 flex items-start gap-2">
                      <span className="text-amber-700 font-bold">•</span>
                      <span>{ded}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-emerald-50/50 border border-emerald-200 rounded-lg p-2.5 text-xs text-emerald-900 font-mono flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Zero grounding deductions. All statements align with deterministic rule engine records.</span>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-mono flex-wrap gap-2">
              <span>Rule Engine Verdict: <strong className="text-slate-800">{step.tool_result.rule_engine_verdict || "COMPLIANT"}</strong></span>
              <span>Evaluator Model: <strong>{step.tool_result.model || "qwen2.5:7b-instruct"}</strong></span>
            </div>
          </div>
        )}

        {/* Expandable Tool Result JSON (Filtered when showRawTrace is false) */}
        {hasResult && showRawTrace && (
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
                <span>Raw Tool Execution Output</span>
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
