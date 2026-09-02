import React from "react";
import {
  Compass,
  Database,
  Terminal,
  Cpu,
  FileCheck,
  ScanText,
  FileSearch,
  Route,
  Wrench,
  Zap,
} from "lucide-react";

interface ToolBadgeProps {
  tool: string | null | undefined;
}

export const ToolBadge: React.FC<ToolBadgeProps> = ({ tool }) => {
  if (!tool) return null;

  switch (tool) {
    case "auto_router":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-300">
          <Route className="h-3 w-3 text-amber-700" />
          <span>auto_router</span>
        </span>
      );
    case "model_switcher":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-50 text-emerald-900 border border-emerald-300">
          <Zap className="h-3 w-3 text-emerald-700" />
          <span>model_switcher</span>
        </span>
      );
    case "agent_planner":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-200">
          <Compass className="h-3 w-3 text-purple-700" />
          <span>agent_planner</span>
        </span>
      );
    case "search_kb":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-teal-50 text-teal-900 border border-teal-200">
          <Database className="h-3 w-3 text-teal-700" />
          <span>search_kb (SOP RAG)</span>
        </span>
      );
    case "run_code":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-200">
          <Terminal className="h-3 w-3 text-amber-700" />
          <span>run_code (Sandbox)</span>
        </span>
      );
    case "generate_text":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-sky-50 text-sky-900 border border-sky-200">
          <Cpu className="h-3 w-3 text-sky-700" />
          <span>generate_text</span>
        </span>
      );
    case "direct_reasoning":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-50 text-emerald-900 border border-emerald-300">
          <Zap className="h-3 w-3 text-emerald-700" />
          <span>direct_reasoning</span>
        </span>
      );
    case "agent_synthesizer":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
          <FileCheck className="h-3 w-3 text-emerald-800" />
          <span>agent_synthesizer</span>
        </span>
      );
    case "docgen_docx":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
          <FileCheck className="h-3 w-3 text-emerald-800" />
          <span>docgen_docx (.docx)</span>
        </span>
      );
    case "ocr_classify":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-200">
          <FileSearch className="h-3 w-3 text-purple-700" />
          <span>ocr_classify</span>
        </span>
      );
    case "ocr_extract_fields":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-50 text-emerald-900 border border-emerald-300">
          <ScanText className="h-3 w-3 text-emerald-700" />
          <span>ocr_extract_fields</span>
        </span>
      );
    case "cross_doc_fetch":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-50 text-emerald-900 border border-emerald-300">
          <Database className="h-3 w-3 text-emerald-700" />
          <span>cross_doc_fetch</span>
        </span>
      );
    case "cross_doc_synthesizer":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
          <FileCheck className="h-3 w-3 text-emerald-800" />
          <span>cross_doc_synthesizer</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-700 border border-slate-300">
          <Wrench className="h-3 w-3 text-slate-500" />
          <span>{tool}</span>
        </span>
      );
  }
};
