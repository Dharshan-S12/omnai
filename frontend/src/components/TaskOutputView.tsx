import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileCheck,
  Download,
  ScanText,
  Terminal,
  Copy,
  Check,
  AlertTriangle,
  Code2,
  Table as TableIcon,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Cpu,
  Clock,
  Files,
  ExternalLink,
  FileText,
} from "lucide-react";
import { getDocxDownloadUrl, getTextDownloadUrl } from "../api";
import type { TaskItem } from "../api";

interface TaskOutputViewProps {
  task: TaskItem;
}

export const TaskOutputView: React.FC<TaskOutputViewProps> = ({ task }) => {
  const [copied, setCopied] = useState(false);
  const [ocrTab, setOcrTab] = useState<"structured" | "raw">("structured");
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ----------------------------------------------------
  // 0. FAILED TASK CARD
  // ----------------------------------------------------
  if (task.status === "failed") {
    const rawError = task.output_ref || "Unknown execution error";
    const isOllamaDown =
      rawError.toLowerCase().includes("ollama") ||
      rawError.toLowerCase().includes("local model unavailable") ||
      rawError.includes("11434") ||
      rawError.toLowerCase().includes("connection refused");
    const isTimeout =
      rawError.toLowerCase().includes("timed out") ||
      rawError.toLowerCase().includes("timeout");

    let title = "Task Execution Stopped";
    let explanation = "An unexpected error occurred during autonomous step execution.";
    let recoveryHint = "Inspect the timeline steps above to identify the failing sub-process.";
    let icon = <AlertTriangle className="h-6 w-6 text-rose-600 shrink-0" />;

    if (isOllamaDown) {
      title = "Local AI Model Service Unavailable";
      explanation =
        "The workbench cannot reach the on-premise Ollama instance on http://127.0.0.1:11434. The model may not be started.";
      recoveryHint =
        "Recoverable: Start Ollama (ollama run qwen2.5:7b-instruct) and re-run the task.";
      icon = <Cpu className="h-6 w-6 text-amber-600 shrink-0" />;
    } else if (isTimeout) {
      title = "Task Execution Timed Out";
      explanation =
        "The operation exceeded the maximum safety timeout. Sandboxed subprocesses or model inference took longer than permitted.";
      recoveryHint =
        "Recoverable: Simplify the prompt, reduce data scope, or re-run to allow faster execution.";
      icon = <Clock className="h-6 w-6 text-amber-600 shrink-0" />;
    }

    return (
      <div className="mt-4 bg-white border-2 border-rose-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-start gap-4 mb-4">
          <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200">
            {icon}
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold font-sans text-slate-900 flex items-center gap-2">
              {title}
            </h3>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">{explanation}</p>
            <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-mono text-emerald-800 font-medium">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
              <span>{recoveryHint}</span>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-100">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="flex items-center justify-between w-full text-xs font-mono text-slate-500 hover:text-slate-800 transition-colors cursor-pointer py-1"
          >
            <div className="flex items-center gap-1.5">
              {showTechnicalDetails ? (
                <ChevronDown className="h-3.5 w-3.5" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" />
              )}
              <span>Diagnostic Technical Details</span>
            </div>
            <span className="text-[10px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              {showTechnicalDetails ? "Hide Details" : "Show Diagnostics"}
            </span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-3 relative">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs text-rose-300 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-64">
                {rawError}
              </div>
              <button
                onClick={() => handleCopy(rawError)}
                className="absolute top-2 right-2 p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[11px] font-mono transition-colors flex items-center gap-1 cursor-pointer"
                title="Copy Error"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (task.status !== "done" || !task.output_ref) {
    return null;
  }

  // ----------------------------------------------------
  // 1. OCR Output Renderer (With Dynamic MRPL Tables & Metadata)
  // ----------------------------------------------------
  if (task.task_type === "ocr") {
    let parsedData: any = null;
    let isParseError = false;

    try {
      parsedData = JSON.parse(task.output_ref);
      if (parsedData && (parsedData.parse_error || !parsedData.document_type)) {
        isParseError = Boolean(parsedData.parse_error);
      }
    } catch {
      parsedData = null;
      isParseError = true;
    }

    const hasStructuredFields =
      parsedData &&
      !isParseError &&
      (parsedData.metadata ||
        parsedData.tables ||
        parsedData.document_title ||
        parsedData.equipment_id ||
        parsedData.inspection_date ||
        parsedData.inspector_name ||
        parsedData.compliance_status ||
        parsedData.drawing_number ||
        parsedData.vendor_name ||
        parsedData.measurements ||
        parsedData.findings ||
        parsedData.notes ||
        parsedData.key_components ||
        parsedData.key_figures ||
        parsedData.key_points);

    const isPdfProcessed = parsedData?.processing_path;
    const isTextPath = parsedData?.processing_path === "text_extraction";

    return (
      <div className="mt-4 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
              <ScanText className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold text-slate-900 font-sans">
                  Structured OCR Field Extraction
                </h3>
                {isPdfProcessed && (
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                    isTextPath
                      ? "bg-sky-50 border-sky-300 text-sky-800"
                      : "bg-emerald-50 border-emerald-300 text-emerald-800"
                  }`}>
                    {isTextPath ? "PDF Text Layer (pypdf)" : "PDF Vision OCR (qwen2.5vl:7b)"}
                  </span>
                )}
                {parsedData?.page_count && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-600">
                    {parsedData.page_count} / {parsedData.total_pages || parsedData.page_count} Pages
                    {parsedData.truncated ? " (Truncated)" : ""}
                  </span>
                )}
              </div>
              <p className="text-xs text-emerald-800 font-mono mt-0.5 font-medium">
                Category: {parsedData?.document_type || "MRPL Refinery Document"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="bg-slate-100 border border-slate-200 rounded-lg p-0.5 flex text-xs">
              <button
                onClick={() => setOcrTab("structured")}
                className={`px-3 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
                  ocrTab === "structured"
                    ? "bg-white text-emerald-900 border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <TableIcon className="h-3.5 w-3.5" />
                Structured View
              </button>
              <button
                onClick={() => setOcrTab("raw")}
                className={`px-3 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
                  ocrTab === "raw"
                    ? "bg-white text-emerald-900 border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Code2 className="h-3.5 w-3.5" />
                Raw JSON
              </button>
            </div>

            <button
              onClick={() => handleCopy(task.output_ref || "")}
              className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors cursor-pointer border border-slate-200"
              title="Copy Output"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {ocrTab === "raw" || !parsedData ? (
          <pre className="p-4 bg-slate-900 border border-slate-800 rounded-xl font-mono text-xs text-emerald-300 overflow-x-auto leading-relaxed">
            {task.output_ref}
          </pre>
        ) : !hasStructuredFields && !parsedData.metadata && !parsedData.tables && !parsedData.document_title ? (
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-between text-xs font-mono">
              <span className="text-emerald-900 font-semibold flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-emerald-700" />
                <span>Extracted Document Text</span>
              </span>
              <span className="text-[10px] text-slate-500">Preserved Raw</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-sm text-slate-800 font-sans leading-relaxed whitespace-pre-wrap">
              {parsedData.raw_text || JSON.stringify(parsedData, null, 2)}
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Document Header Title if present */}
            {parsedData.document_title && (
              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between flex-wrap gap-2">
                <div>
                  <span className="text-[10px] font-mono text-emerald-800 uppercase font-bold block">Document Header</span>
                  <h4 className="text-sm md:text-base font-bold text-slate-900 font-sans">{parsedData.document_title}</h4>
                </div>
                {parsedData.compliance_status && (
                  <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider border ${
                    String(parsedData.compliance_status).toUpperCase().includes("COMPLIANT") && !String(parsedData.compliance_status).toUpperCase().includes("NON")
                      ? "bg-emerald-100 border-emerald-300 text-emerald-800"
                      : String(parsedData.compliance_status).toUpperCase().includes("NON")
                      ? "bg-rose-100 border-rose-300 text-rose-800"
                      : "bg-amber-100 border-amber-300 text-amber-800"
                  }`}>
                    {parsedData.compliance_status}
                  </span>
                )}
              </div>
            )}

            {/* Dynamic Metadata Grid */}
            {(() => {
              const metaEntries: [string, any][] = [];

              if (parsedData.metadata && typeof parsedData.metadata === "object") {
                Object.entries(parsedData.metadata).forEach(([k, v]) => {
                  if (v !== null && v !== undefined && v !== "" && v !== "null") {
                    metaEntries.push([k, v]);
                  }
                });
              }

              const directKeys: [string, string][] = [
                ["equipment_id", "Equipment ID"],
                ["inspection_date", "Inspection Date"],
                ["inspector_name", "Inspector / Engineer"],
                ["drawing_number", "Drawing Number"],
                ["vendor_name", "Vendor / Supplier"],
                ["report_period", "Report Period"],
                ["subject", "Subject"],
                ["from", "From"],
                ["to", "To"],
              ];

              directKeys.forEach(([key, label]) => {
                if (parsedData[key] && !metaEntries.some(([k]) => k.toLowerCase() === label.toLowerCase())) {
                  metaEntries.push([label, parsedData[key]]);
                }
              });

              if (metaEntries.length === 0) return null;

              return (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {metaEntries.map(([key, val]) => (
                    <div key={key} className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl">
                      <span className="text-[10px] text-slate-500 font-mono block uppercase tracking-wider mb-0.5">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-semibold text-slate-800 font-mono break-words">
                        {String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              );
            })()}

            {/* Dynamic Tables Renderer */}
            {parsedData.tables && Array.isArray(parsedData.tables) && parsedData.tables.length > 0 && (
              <div className="space-y-4">
                {parsedData.tables.map((tbl: any, tIdx: number) => {
                  const headers: string[] = tbl.headers || [];
                  const rows: any[][] = tbl.rows || [];

                  return (
                    <div key={tIdx} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
                      {tbl.title && (
                        <div className="bg-emerald-50/80 px-4 py-2.5 text-xs font-bold text-emerald-950 flex items-center justify-between border-b border-emerald-200">
                          <span className="flex items-center gap-2">
                            <TableIcon className="h-3.5 w-3.5 text-emerald-700" />
                            <span>{tbl.title}</span>
                          </span>
                          <span className="text-[10px] font-mono text-emerald-800">{rows.length} row(s)</span>
                        </div>
                      )}
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          {headers.length > 0 && (
                            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-mono text-[11px] uppercase tracking-wider">
                              <tr>
                                {headers.map((h: string, hIdx: number) => (
                                  <th key={hIdx} className="px-4 py-2.5 font-bold text-slate-700">
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                          )}
                          <tbody className="divide-y divide-slate-100 font-mono">
                            {rows.map((row: any[], rIdx: number) => (
                              <tr key={rIdx} className="hover:bg-slate-50 transition-colors">
                                {row.map((cell: any, cIdx: number) => {
                                  const cellStr = String(cell ?? "");
                                  const isNormal = cellStr.toLowerCase() === "normal" || cellStr.toLowerCase() === "compliant";
                                  const isWarning = cellStr.toLowerCase().includes("warn") || cellStr.toLowerCase().includes("fail");

                                  return (
                                    <td key={cIdx} className="px-4 py-2.5 text-slate-800">
                                      {isNormal ? (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 border border-emerald-300 text-[11px] font-bold text-emerald-800">
                                          {cellStr}
                                        </span>
                                      ) : isWarning ? (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-100 border border-rose-300 text-[11px] font-bold text-rose-800">
                                          {cellStr}
                                        </span>
                                      ) : (
                                        cellStr
                                      )}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Dynamic Key Figures / Measurements Sub-table */}
            {parsedData.measurements && typeof parsedData.measurements === "object" && Object.keys(parsedData.measurements).length > 0 && (
              (() => {
                const validMeasurements = Object.entries(parsedData.measurements).filter(
                  ([_, val]) => val !== null && val !== undefined && val !== "null" && val !== ""
                );
                if (validMeasurements.length === 0) return null;

                return (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
                    <div className="bg-slate-100 px-4 py-2 text-xs font-bold text-slate-800 flex items-center justify-between border-b border-slate-200">
                      <span>Recorded Operating Parameters</span>
                      <span className="text-[10px] font-mono text-slate-500">Metric Parameters</span>
                    </div>
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-mono">
                        <tr>
                          <th className="px-4 py-2 font-medium">Metric Parameter</th>
                          <th className="px-4 py-2 font-medium">Recorded Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono">
                        {validMeasurements.map(([key, val]) => (
                          <tr key={key} className="hover:bg-slate-50">
                            <td className="px-4 py-2.5 text-slate-600 capitalize">{key.replace(/_/g, " ")}</td>
                            <td className="px-4 py-2.5 text-emerald-800 font-bold">{String(val)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()
            )}

            {/* Compliance Requirements Note Banner */}
            {parsedData.compliance_notes && (
              <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl">
                <span className="text-xs font-bold text-emerald-900 font-mono uppercase block mb-1">
                  Compliance Criteria & Logic Evaluation
                </span>
                <p className="text-sm text-slate-700 leading-relaxed font-sans">
                  {parsedData.compliance_notes}
                </p>
              </div>
            )}

            {/* Findings / Notes block */}
            {(parsedData.findings_and_summary || parsedData.findings || parsedData.notes || parsedData.summary) && (
              <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl">
                <span className="text-xs font-bold text-slate-700 font-mono uppercase block mb-1.5">
                  Findings & Technical Observations
                </span>
                <p className="text-sm text-slate-800 leading-relaxed font-sans">
                  {parsedData.findings_and_summary || parsedData.findings || parsedData.notes || parsedData.summary}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // ----------------------------------------------------
  // 2. cross_doc_query Output Renderer
  // ----------------------------------------------------
  if (task.task_type === "cross_doc_query") {
    const fetchStep = task.steps?.find((s) => s.tool_called === "cross_doc_fetch");
    const referencedTasks: Array<{
      id: string;
      short_id?: string;
      task_type: string;
      created_at: string;
      input_preview?: string;
    }> = fetchStep?.tool_result?.referenced_tasks || [];

    return (
      <div className="mt-4 bg-white border border-emerald-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
              <Files className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 font-sans flex items-center gap-2">
                Cross-Document Ledger Intelligence
              </h3>
              <p className="text-xs text-emerald-800 font-mono font-medium">
                Synthesized analysis across MRPL on-premise tasks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleCopy(task.output_ref || "")}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? "Copied" : "Copy Analysis"}</span>
            </button>

            <a
              href={getTextDownloadUrl(task.id)}
              download={`cross_doc_summary_${task.id.slice(0, 8)}.txt`}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download .txt</span>
            </a>
          </div>
        </div>

        {referencedTasks.length > 0 && (
          <div className="mb-5 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div className="text-xs font-mono font-bold text-slate-600 uppercase tracking-wider mb-2.5 flex items-center gap-2">
              <FileText className="h-3.5 w-3.5 text-emerald-700" />
              <span>Referenced Source Documents ({referencedTasks.length} tasks in scope):</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {referencedTasks.map((st) => (
                <Link
                  key={st.id}
                  to={`/task/${st.id}`}
                  className="group inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-emerald-600 hover:bg-emerald-50 text-xs font-mono text-slate-700 transition-all cursor-pointer shadow-xs"
                  title={`View Task ${st.id}: ${st.input_preview || ""}`}
                >
                  <span className="font-bold text-emerald-700 group-hover:underline">
                    #{st.short_id || st.id.slice(0, 8)}
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase">({st.task_type})</span>
                  <ExternalLink className="h-3 w-3 text-slate-400 group-hover:text-emerald-700 transition-colors" />
                </Link>
              ))}
            </div>
          </div>
        )}

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 overflow-hidden">
          <div className="text-xs font-mono text-slate-500 mb-3 uppercase tracking-wider font-bold">
            Synthesized Intelligence Summary
          </div>
          <div className="text-sm text-slate-800 font-sans leading-relaxed whitespace-pre-wrap">
            {task.output_ref}
          </div>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------
  // 3. doc_gen Output Renderer
  // ----------------------------------------------------
  if (task.task_type === "doc_gen") {
    return (
      <div className="mt-4 bg-white border border-emerald-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
              <FileCheck className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 font-sans flex items-center gap-2">
                Executive Word Document Generated
              </h3>
              <p className="text-xs text-emerald-800 font-mono font-medium">
                Formatted with MRPL SOP standards, styling, & confidentiality footer
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleCopy(task.output_ref || "")}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? "Copied" : "Copy Text"}</span>
            </button>

            <a
              href={getDocxDownloadUrl(task.id)}
              download={`document_${task.id.slice(0, 8)}.docx`}
              className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 text-white font-semibold py-2 px-5 rounded-xl shadow-md shadow-emerald-900/20 transition-all text-xs cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
            >
              <Download className="h-4 w-4" />
              <span>Download Word (.docx)</span>
            </a>
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 overflow-hidden">
          <div className="text-xs font-mono text-slate-500 mb-3 uppercase tracking-wider font-bold">
            Synthesized Document Preview
          </div>
          <div className="text-sm text-slate-800 font-sans leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto pr-2">
            {task.output_ref}
          </div>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------
  // 4. code_exec Output Renderer
  // ----------------------------------------------------
  if (task.task_type === "code_exec") {
    const isTimeout =
      task.output_ref.toLowerCase().includes("timed out") ||
      task.output_ref.toLowerCase().includes("timeout");

    return (
      <div className="mt-4 bg-white border border-amber-200 rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-amber-100 border border-amber-300 flex items-center justify-center text-amber-800">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 font-sans">Sandboxed Code Execution Results</h3>
                {isTimeout && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-100 border border-amber-300 text-amber-900 font-bold">
                    Timed Out (15s)
                  </span>
                )}
              </div>
              <p className="text-xs text-amber-800 font-mono font-medium">Isolated Python Execution & Statistical Analysis</p>
            </div>
          </div>

          <button
            onClick={() => handleCopy(task.output_ref || "")}
            className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors cursor-pointer border border-slate-200"
            title="Copy Output"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs text-amber-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {task.output_ref}
          </div>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------
  // 5. text_gen Output Renderer
  // ----------------------------------------------------
  return (
    <div className="mt-4 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 font-sans">Synthesized Text Output</h3>
            <p className="text-xs text-emerald-800 font-mono font-medium">Direct Domain Reasoning & Synthesis</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleCopy(task.output_ref || "")}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>

          <a
            href={getTextDownloadUrl(task.id)}
            download={`task_${task.id.slice(0, 8)}_output.txt`}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer border border-slate-200"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download .txt</span>
          </a>
        </div>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-sm text-slate-800 font-sans leading-relaxed whitespace-pre-wrap">
        {task.output_ref}
      </div>
    </div>
  );
};
