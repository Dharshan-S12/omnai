import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Send,
  Paperclip,
  X,
  Sparkles,
  FileText,
  Calculator,
  Files,
  FileCheck,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  Gauge,
  Zap,
  RotateCcw,
  Sliders,
  ShieldCheck,
} from "lucide-react";
import {
  createAutoTask,
  uploadFile,
  fetchTaskDetails,
} from "../api";
import type { TaskItem } from "../api";
import { TaskOutputView } from "../components/TaskOutputView";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachedFile?: {
    name: string;
    path: string;
  };
  taskId?: string;
  taskData?: TaskItem;
  timestamp: string;
}

const REFINERY_PRESETS = [
  {
    icon: <FileText className="h-4 w-4 text-emerald-700" />,
    unit: "CDU / Pump House Unit 3",
    title: "Vibration & ISO Compliance Extraction",
    prompt: "Extract structured vibration measurements from this report and verify ISO Zone A operating compliance",
    core: "OmniVision + Rule Engine"
  },
  {
    icon: <Calculator className="h-4 w-4 text-amber-700" />,
    unit: "Process Engineering",
    title: "Thermal & Vibration Numerical Analysis",
    prompt: "Calculate RMS vibration velocity from peak 2.1 mm/s and determine if within 2.8 mm/s ISO threshold",
    core: "OmniCode (Python Sandbox)"
  },
  {
    icon: <Files className="h-4 w-4 text-teal-700" />,
    unit: "Historical Operations Ledger",
    title: "Cross-Unit Anomaly & Ledger Query",
    prompt: "Synthesize latest equipment inspection findings and recurring maintenance issues across recorded tasks",
    core: "OmniLedger Intelligence"
  },
  {
    icon: <FileCheck className="h-4 w-4 text-purple-700" />,
    unit: "Operations & Safety",
    title: "Executive Plant SOP Generation (.docx)",
    prompt: "Draft a formal standard operating procedure document (.docx) for centrifugal pump emergency shutdown",
    core: "OmniDoc Generator"
  }
];

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = localStorage.getItem("mrpl_omni_chat_history");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [inputValue, setInputValue] = useState("");
  const [attachedFile, setAttachedFile] = useState<{ name: string; path: string } | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Persist messages to localStorage
  useEffect(() => {
    localStorage.setItem("mrpl_omni_chat_history", JSON.stringify(messages));
  }, [messages]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Poll running tasks in messages
  useEffect(() => {
    const activeTasks = messages.filter(
      (m) => m.role === "assistant" && m.taskId && m.taskData?.status && ["pending", "running"].includes(m.taskData.status)
    );

    if (activeTasks.length === 0) return;

    const interval = setInterval(async () => {
      for (const msg of activeTasks) {
        if (!msg.taskId) continue;
        try {
          const updated = await fetchTaskDetails(msg.taskId);
          setMessages((prev) =>
            prev.map((m) =>
              m.taskId === msg.taskId
                ? { ...m, taskData: updated, content: updated.output_ref || m.content }
                : m
            )
          );
        } catch {
          // quiet fallback
        }
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [messages]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const res = await uploadFile(file);
      setAttachedFile({
        name: file.name,
        path: res.storage_path || res.id,
      });
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSendMessage = async (promptToSend?: string) => {
    const text = (promptToSend || inputValue).trim();
    if (!text && !attachedFile) return;

    const userMessageId = `user_${Date.now()}`;
    const assistantMessageId = `asst_${Date.now()}`;

    const userMsg: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: text || `[Document Attached for Vision Extraction: ${attachedFile?.name}]`,
      attachedFile: attachedFile ? { ...attachedFile } : undefined,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setInputValue("");
    const fileToSend = attachedFile?.path;
    setAttachedFile(null);
    setIsProcessing(true);

    // Placeholder assistant message
    const placeholderAssistantMsg: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "Routing intent to specialized OmniAI model...",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg, placeholderAssistantMsg]);

    try {
      const createdTask = await createAutoTask(text, fileToSend);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                taskId: createdTask.id,
                taskData: createdTask,
                content: createdTask.output_ref || "Task dispatched to sovereign engine...",
              }
            : m
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                content: `Error executing task: ${err.message}`,
                taskData: {
                  id: "error",
                  task_type: "text_gen",
                  status: "failed",
                  input_ref: text,
                  output_ref: err.message,
                  created_at: new Date().toISOString(),
                },
              }
            : m
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearHistory = () => {
    if (confirm("Start a new OmniAI intelligence session? History will be cleared.")) {
      setMessages([]);
      localStorage.removeItem("mrpl_omni_chat_history");
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900">
      {/* Studio Header Bar */}
      <div className="px-6 py-3 border-b border-slate-200 bg-white shadow-xs flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-xl bg-emerald-800 flex items-center justify-center text-white shadow-xs">
            <Sparkles className="h-4 w-4 text-amber-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-900 font-sans tracking-tight">
                OmniAI Sovereign Studio
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 font-bold flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
                Air-Gapped Multi-Core Router
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">
              Autonomous Document Vision, Numerical Sandbox & Refinery Ledger Intelligence
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden xl:flex items-center gap-2 text-xs font-mono text-slate-600 bg-slate-100 border border-slate-200 px-3 py-1 rounded-lg">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" />
            <span>0 Cloud Telemetry</span>
          </div>

          {messages.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-emerald-900 bg-slate-100 hover:bg-emerald-50 border border-slate-200 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset Canvas</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Intelligence Canvas Stream */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.length === 0 ? (
          /* Bespoke Launchpad Empty State */
          <div className="max-w-4xl mx-auto mt-4 space-y-6">
            {/* Refinery Hero Banner */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm relative overflow-hidden">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div className="max-w-2xl">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-mono font-bold mb-2.5">
                    <Gauge className="h-3 w-3" />
                    <span>MRPL Refinery Intelligent Operations</span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 font-sans tracking-tight">
                    MRPL OmniAI™ Sovereign Intelligence
                  </h3>
                  <p className="text-sm text-slate-600 mt-1 leading-relaxed font-sans">
                    Universal on-premise cognitive workspace for refinery engineers. Drop inspection PDFs, execute sandboxed Python calculations, query cross-unit task ledgers, or generate compliance Word documents.
                  </p>
                </div>

                <div className="hidden md:flex flex-col items-end gap-1 font-mono text-[11px] text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="text-emerald-800 font-bold">Node: Kuthethoor Refineries</span>
                  <span>Active Engine: 5 Local Models</span>
                  <span className="text-emerald-700 font-semibold">100% Zero-Trust Air-Gapped</span>
                </div>
              </div>
            </div>

            {/* Specialized Refinery Operational Starters */}
            <div>
              <div className="flex items-center justify-between mb-3 px-1">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">
                  Refinery Operational Presets
                </span>
                <span className="text-xs text-slate-400 font-mono">Click to execute instantly</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {REFINERY_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(preset.prompt)}
                    className="p-4 rounded-2xl bg-white hover:bg-emerald-50/40 border border-slate-200 hover:border-emerald-600/40 transition-all text-left flex flex-col justify-between group cursor-pointer shadow-xs hover:shadow-md"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-lg bg-slate-50 border border-slate-200 group-hover:bg-emerald-100 group-hover:border-emerald-300 transition-colors">
                            {preset.icon}
                          </div>
                          <span className="text-[11px] font-mono text-slate-500 font-bold uppercase">
                            {preset.unit}
                          </span>
                        </div>
                        <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-emerald-700 group-hover:translate-x-0.5 transition-all" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900 font-sans group-hover:text-emerald-900 transition-colors">
                        {preset.title}
                      </h4>
                      <p className="text-xs text-slate-600 line-clamp-2 mt-1 font-sans leading-relaxed">
                        "{preset.prompt}"
                      </p>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[10px] font-mono">
                      <span className="text-emerald-800 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        {preset.core}
                      </span>
                      <span className="text-slate-400 group-hover:text-slate-600 transition-colors">
                        Auto-Routed
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Conversation Canvas */
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {/* Assistant Emblem */}
                {msg.role === "assistant" && (
                  <div className="h-8 w-8 rounded-xl bg-emerald-800 flex items-center justify-center text-white shrink-0 mt-1 shadow-xs border border-emerald-600/30">
                    <Sparkles className="h-4 w-4 text-amber-300" />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`max-w-3xl rounded-2xl transition-all ${
                    msg.role === "user"
                      ? "bg-emerald-800 text-white p-4 shadow-sm"
                      : "bg-white border border-slate-200 p-5 text-slate-900 shadow-card w-full"
                  }`}
                >
                  {msg.role === "user" ? (
                    <div>
                      {msg.attachedFile && (
                        <div className="mb-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-900/90 border border-emerald-600 text-xs font-mono text-emerald-100">
                          <FileText className="h-3.5 w-3.5" />
                          <span>{msg.attachedFile.name}</span>
                        </div>
                      )}
                      <p className="text-sm leading-relaxed whitespace-pre-wrap font-sans font-medium">{msg.content}</p>
                      <span className="text-[10px] font-mono text-emerald-200 block text-right mt-1.5">
                        {msg.timestamp}
                      </span>
                    </div>
                  ) : (
                    /* Assistant View */
                    <div className="space-y-4">
                      {/* Top Routing Status Pill */}
                      {msg.taskData ? (
                        <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold font-sans text-slate-900 flex items-center gap-1.5">
                              <Zap className="h-3.5 w-3.5 text-emerald-700" />
                              <span>MRPL OmniAI Engine</span>
                            </span>

                            {/* Task Type Badge */}
                            <span className="text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">
                              Core: {msg.taskData.task_type.replace(/_/g, " ")}
                            </span>

                            {/* Live Status Badge */}
                            {msg.taskData.status === "running" ? (
                              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-sky-50 border border-sky-300 text-sky-800 flex items-center gap-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-sky-600 animate-pulse" />
                                Processing Trace...
                              </span>
                            ) : msg.taskData.status === "done" ? (
                              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 border border-emerald-300 text-emerald-900 flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3 text-emerald-700" />
                                Executed
                              </span>
                            ) : msg.taskData.status === "failed" ? (
                              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-50 border border-rose-300 text-rose-800 flex items-center gap-1">
                                <AlertCircle className="h-3 w-3 text-rose-600" />
                                Stopped
                              </span>
                            ) : (
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                                Pending...
                              </span>
                            )}
                          </div>

                          {/* Link to Full Task Trace */}
                          {msg.taskId && msg.taskId !== "error" && (
                            <Link
                              to={`/task/${msg.taskId}`}
                              className="text-[11px] font-mono text-slate-500 hover:text-emerald-800 flex items-center gap-1 transition-colors"
                              title="Inspect full execution trace"
                            >
                              <span>Trace #{msg.taskId.slice(0, 8)}</span>
                              <ExternalLink className="h-3 w-3" />
                            </Link>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                          <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse" />
                          <span>{msg.content}</span>
                        </div>
                      )}

                      {/* Execution Steps Stream Sequence */}
                      {msg.taskData?.steps && msg.taskData.steps.length > 0 && (
                        <div className="p-3 bg-slate-50/80 border border-slate-200 rounded-xl space-y-1.5">
                          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 block mb-1">
                            OmniAI Execution Trace ({msg.taskData.steps.length} steps):
                          </span>
                          <div className="space-y-1">
                            {msg.taskData.steps.map((st) => (
                              <div
                                key={st.id || st.step_number}
                                className="text-xs font-mono text-slate-700 flex items-start gap-2"
                              >
                                <span className="text-emerald-800 font-bold shrink-0">
                                  #{st.step_number}
                                </span>
                                <span className="text-slate-800 leading-snug flex-1">
                                  {st.description}
                                </span>
                                {st.tool_called && (
                                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-white border border-slate-200 text-slate-600 shrink-0 font-bold">
                                    {st.tool_called}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Render Rich Output Component when Done */}
                      {msg.taskData && (
                        <div className="pt-1">
                          <TaskOutputView task={msg.taskData} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Docked OmniAI Command Composer */}
      <div className="p-4 border-t border-slate-200 bg-white shadow-xs shrink-0">
        <div className="max-w-4xl mx-auto space-y-2.5">
          {/* File Attachment Tag */}
          {attachedFile && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-300 text-xs font-mono text-emerald-900 shadow-xs">
              <FileText className="h-4 w-4 text-emerald-700" />
              <span className="font-semibold">Attached: {attachedFile.name}</span>
              <button
                onClick={() => setAttachedFile(null)}
                className="hover:text-rose-600 transition-colors cursor-pointer p-0.5 ml-1"
                title="Remove attachment"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* Composer Box */}
          <div className="flex items-end gap-2 bg-slate-50 border border-slate-300 focus-within:border-emerald-700 focus-within:bg-white focus-within:ring-2 focus-within:ring-emerald-700/15 rounded-2xl p-2 transition-all shadow-card">
            {/* Attachment Button */}
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg,.txt,.docx"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || isProcessing}
              className={`p-2.5 rounded-xl text-slate-500 hover:text-emerald-900 hover:bg-slate-200 transition-colors cursor-pointer shrink-0 ${
                attachedFile ? "text-emerald-900 bg-emerald-100" : ""
              }`}
              title="Attach Document / PDF / Image for Vision OCR"
            >
              <Paperclip className="h-5 w-5" />
            </button>

            {/* Textarea */}
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask OmniAI: Calculate math, query refinery ledgers, draft Word SOPs, or attach documents..."
              rows={1}
              className="flex-1 max-h-32 min-h-[44px] bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none resize-none py-2.5 px-2 font-sans"
            />

            {/* Send Button */}
            <button
              onClick={() => handleSendMessage()}
              disabled={(!inputValue.trim() && !attachedFile) || isProcessing}
              className={`p-2.5 rounded-xl transition-all shrink-0 cursor-pointer ${
                (inputValue.trim() || attachedFile) && !isProcessing
                  ? "bg-emerald-800 hover:bg-emerald-900 text-white shadow-md shadow-emerald-950/20 hover:scale-105 active:scale-95"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }`}
              title="Send to OmniAI Dispatcher"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 px-1">
            <span>Press <strong>Enter</strong> to dispatch • <strong>Shift+Enter</strong> for newline</span>
            <span className="text-emerald-800 font-bold flex items-center gap-1">
              <Sliders className="h-3 w-3" />
              OmniAI Autonomous Routing Active
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
