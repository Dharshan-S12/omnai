import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  UploadCloud,
  CheckCircle2,
  Loader2,
  ScanText,
  FileSpreadsheet,
  Terminal,
  Sparkles,
  ArrowRight,
  Link2,
  Files,
  Database,
  Flame,
} from "lucide-react";
import { uploadFile, createTask, fetchTasks } from "../api";
import type { TaskItem } from "../api";

export default function UploadView() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadedDoc, setUploadedDoc] = useState<{ id: string; filename: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form State
  const [taskType, setTaskType] = useState<string>("ocr");
  const [promptText, setPromptText] = useState<string>("");
  const [sourceTaskId, setSourceTaskId] = useState<string>("");

  // Completed OCR tasks for doc_gen chaining
  const [completedOcrTasks, setCompletedOcrTasks] = useState<TaskItem[]>([]);
  const [loadingOcrTasks, setLoadingOcrTasks] = useState(false);

  // Fetch recent completed OCR tasks for chaining
  useEffect(() => {
    const loadOcrTasks = async () => {
      setLoadingOcrTasks(true);
      try {
        const allTasks = await fetchTasks();
        const ocrDone = allTasks.filter(
          (t) => t.task_type === "ocr" && t.status === "done"
        );
        setCompletedOcrTasks(ocrDone);
      } catch (err) {
        console.error("Failed to load completed OCR tasks:", err);
      } finally {
        setLoadingOcrTasks(false);
      }
    };

    loadOcrTasks();
  }, []);

  // Update default prompt when task type changes
  useEffect(() => {
    if (taskType === "ocr") {
      setPromptText("Extract structured fields and technical measurements from this document.");
    } else if (taskType === "doc_gen") {
      setPromptText("Draft a formal pump inspection approval note referencing our SOP for this inspected pump.");
    } else if (taskType === "code_exec") {
      setPromptText("Calculate vibration amplitude RMS and verify if 2.1 mm/s is compliant with ISO zone A (< 2.8 mm/s).");
    } else if (taskType === "text_gen") {
      setPromptText("Summarize standard operating procedures for quarterly turbine vibration maintenance.");
    } else if (taskType === "cross_doc_query") {
      setPromptText("Summarize the key findings, equipment tags, and compliance issues across the last 5 inspection reports.");
    }
  }, [taskType]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
      setUploadedDoc(null);
    }
  }, []);

  const handleSubmitTask = async () => {
    try {
      setSubmitting(true);

      let inputRef = promptText.trim();

      // If task requires file upload and file is present
      if (taskType !== "cross_doc_query") {
        if (file && !uploadedDoc) {
          setUploading(true);
          const docRes = await uploadFile(file);
          setUploadedDoc({ id: docRes.id, filename: file.name });
          if (taskType === "ocr") {
            inputRef = docRes.id;
          }
        } else if (uploadedDoc && taskType === "ocr") {
          inputRef = uploadedDoc.id;
        }
      }

      const chainedSourceId = taskType === "doc_gen" && sourceTaskId ? sourceTaskId : null;

      const newTask = await createTask(taskType, inputRef, chainedSourceId);
      navigate(`/task/${newTask.id}`);
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to create task");
    } finally {
      setSubmitting(false);
      setUploading(false);
    }
  };

  const isCrossDoc = taskType === "cross_doc_query";

  return (
    <div className="max-w-4xl mx-auto py-8 px-6 md:px-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              MRPL Refinery Document Engine
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5 font-sans mt-1">
            <span>Process Document & Launch Task</span>
          </h2>
          <p className="text-sm text-slate-600 mt-0.5 font-sans">
            Upload PDF/images for Vision OCR, dispatch SOP-grounded Word generators, or query the on-premise ledger.
          </p>
        </div>

        <div className="hidden sm:flex items-center gap-2 bg-white border border-slate-200 px-3 py-1.5 rounded-xl text-xs font-mono text-slate-600 shadow-xs">
          <Flame className="h-4 w-4 text-emerald-700" />
          <span>MRPL Air-Gapped Safe</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Document Dropzone */}
        <div className="md:col-span-12">
          {isCrossDoc ? (
            <div className="border-2 border-dashed border-emerald-300 bg-emerald-50/50 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
              <div className="h-14 w-14 rounded-2xl bg-emerald-100 border border-emerald-300 text-emerald-800 flex items-center justify-center mb-3">
                <Database className="h-7 w-7" />
              </div>
              <p className="text-base font-semibold text-slate-900">Cross-Document Ledger Intelligence</p>
              <p className="text-xs text-slate-600 mt-1 max-w-lg leading-relaxed">
                This mode queries and synthesizes insights across completed tasks in your sovereign MRPL database ledger. No file upload is needed.
              </p>
            </div>
          ) : (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center transition-all bg-white ${
                isDragging
                  ? "border-emerald-600 bg-emerald-50 shadow-md"
                  : file
                  ? "border-emerald-500 bg-emerald-50/30"
                  : "border-slate-300 hover:border-emerald-500"
              }`}
            >
              {file ? (
                <div className="flex flex-col items-center text-center">
                  <div className="h-14 w-14 rounded-2xl bg-emerald-100 border border-emerald-300 text-emerald-800 flex items-center justify-center mb-3">
                    <CheckCircle2 className="h-7 w-7" />
                  </div>
                  <p className="text-base font-semibold text-slate-900">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1 font-mono">
                    {(file.size / 1024).toFixed(1)} KB • {file.type || "Document"}
                  </p>

                  <div className="mt-4 flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setFile(null);
                        setUploadedDoc(null);
                      }}
                      className="text-xs text-slate-600 hover:text-emerald-800 underline cursor-pointer"
                    >
                      Change document
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="h-14 w-14 rounded-2xl bg-slate-100 text-slate-600 flex items-center justify-center mb-3 border border-slate-200">
                    <UploadCloud className="h-7 w-7 text-emerald-700" />
                  </div>
                  <p className="text-sm font-semibold text-slate-800">
                    Drag & drop PDF document, scanned inspection report, or drawing
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Supports PDF (Text & Scanned OCR), PNG, JPG, DOCX (Air-gapped on localhost)
                  </p>
                  <div className="mt-4">
                    <input
                      type="file"
                      className="hidden"
                      id="file-upload"
                      accept=".pdf,.png,.jpg,.jpeg,.docx"
                      onChange={(e) => {
                        if (e.target.files?.[0]) {
                          setFile(e.target.files[0]);
                          setUploadedDoc(null);
                        }
                      }}
                    />
                    <label
                      htmlFor="file-upload"
                      className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl cursor-pointer transition-all text-xs font-semibold shadow-sm inline-block"
                    >
                      Browse Files
                    </label>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Task Configuration Panel */}
        <div className="md:col-span-12 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
            <span>Agent Task Configuration</span>
          </h3>

          <div className="space-y-5">
            {/* Task Type Selector (5-Agent Grid) */}
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-2 font-mono uppercase">
                Select Processing Agent Mode
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                <button
                  type="button"
                  onClick={() => setTaskType("ocr")}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    taskType === "ocr"
                      ? "bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:border-emerald-300"
                  }`}
                >
                  <ScanText className="h-5 w-5 text-emerald-700 mb-2" />
                  <div className="text-xs font-bold text-slate-900">PDF / Image OCR</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Classify & extract structured JSON</div>
                </button>

                <button
                  type="button"
                  onClick={() => setTaskType("cross_doc_query")}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    taskType === "cross_doc_query"
                      ? "bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:border-emerald-300"
                  }`}
                >
                  <Files className="h-5 w-5 text-emerald-700 mb-2" />
                  <div className="text-xs font-bold text-slate-900">Cross-Doc Query</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Synthesize across recent tasks</div>
                </button>

                <button
                  type="button"
                  onClick={() => setTaskType("doc_gen")}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    taskType === "doc_gen"
                      ? "bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:border-emerald-300"
                  }`}
                >
                  <FileSpreadsheet className="h-5 w-5 text-emerald-700 mb-2" />
                  <div className="text-xs font-bold text-slate-900">Word DocGen</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">SOP RAG + .docx export</div>
                </button>

                <button
                  type="button"
                  onClick={() => setTaskType("code_exec")}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    taskType === "code_exec"
                      ? "bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:border-emerald-300"
                  }`}
                >
                  <Terminal className="h-5 w-5 text-emerald-700 mb-2" />
                  <div className="text-xs font-bold text-slate-900">Code Sandbox</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Python execution & math</div>
                </button>

                <button
                  type="button"
                  onClick={() => setTaskType("text_gen")}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                    taskType === "text_gen"
                      ? "bg-emerald-50 border-emerald-600 text-emerald-900 shadow-sm"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:border-emerald-300"
                  }`}
                >
                  <Sparkles className="h-5 w-5 text-emerald-700 mb-2" />
                  <div className="text-xs font-bold text-slate-900">Text & Analysis</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Direct reasoning synthesis</div>
                </button>
              </div>
            </div>

            {/* Chaining Selector for doc_gen */}
            {taskType === "doc_gen" && (
              <div className="bg-emerald-50/50 border border-emerald-200 rounded-xl p-4 transition-all">
                <div className="flex items-center gap-2 text-emerald-900 text-xs font-bold uppercase font-mono mb-2">
                  <Link2 className="h-4 w-4" />
                  <span>Chain from Upstream OCR Output (Optional)</span>
                </div>
                <p className="text-xs text-slate-600 mb-3 font-sans">
                  Select a previously extracted OCR inspection or drawing to ground this document generator with its structured measurements.
                </p>

                <select
                  value={sourceTaskId}
                  onChange={(e) => setSourceTaskId(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-emerald-600 font-mono cursor-pointer"
                >
                  <option value="">-- Standalone (No OCR context attached) --</option>
                  {completedOcrTasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      Task #{t.id.slice(0, 8)} • OCR ({new Date(t.created_at).toLocaleTimeString()}) • {t.input_ref.slice(-30)}
                    </option>
                  ))}
                </select>

                {completedOcrTasks.length === 0 && !loadingOcrTasks && (
                  <p className="text-[11px] text-slate-500 mt-2 font-mono">
                    No completed OCR tasks found. Run an OCR task first to chain it!
                  </p>
                )}
              </div>
            )}

            {/* Task Prompt / Goal Textarea */}
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-2 font-mono uppercase">
                {taskType === "ocr"
                  ? "Document Identifier / Instructions"
                  : taskType === "cross_doc_query"
                  ? "Cross-Document Query Question"
                  : "Agent Goal / Prompt"}
              </label>
              <textarea
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                rows={3}
                placeholder={
                  taskType === "cross_doc_query"
                    ? "e.g. Summarize compliance status and peak vibration readings across the last 5 inspection tasks..."
                    : "Enter prompt or objective for the MRPL agent..."
                }
                className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-600 focus:bg-white font-sans leading-relaxed resize-none"
              />
            </div>

            {/* Submit Button */}
            <button
              type="button"
              onClick={handleSubmitTask}
              disabled={
                submitting ||
                uploading ||
                (taskType === "ocr" && !file && !promptText.trim()) ||
                (!promptText.trim() && taskType !== "ocr")
              }
              className="w-full bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-200 disabled:text-slate-400 text-white font-semibold py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-emerald-900/20 text-sm font-sans"
            >
              {submitting || uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{uploading ? "Uploading Document..." : "Dispatching MRPL Agent..."}</span>
                </>
              ) : (
                <>
                  <span>
                    {taskType === "cross_doc_query"
                      ? "Execute Cross-Document Query"
                      : "Launch Agent Task"}
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
