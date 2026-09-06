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
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  BrainCircuit,
  Binary,
  FileEdit,
  CheckCircle2,
  Share2,
  TrendingUp,
  Scale,
  Users
} from "lucide-react";

interface ToolBadgeProps {
  tool: string | null | undefined;
}

export const ToolBadge: React.FC<ToolBadgeProps> = ({ tool }) => {
  if (!tool) return null;

  switch (tool) {
    case "rule_engine_check":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-50 text-emerald-900 border border-emerald-400 shadow-xs">
          <Scale className="h-3 w-3 text-emerald-700" />
          <span>Rule Engine (Deterministic)</span>
        </span>
      );
    case "compliance_ensemble":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-400 shadow-xs">
          <Users className="h-3 w-3 text-amber-700" />
          <span>Compliance Ensemble (3x)</span>
        </span>
      );
    case "agent_extractor":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-teal-50 text-teal-800 border border-teal-300 shadow-sm">
          <Binary className="h-3 w-3 text-teal-600" />
          <span>Extractor Agent</span>
        </span>
      );
    case "agent_compliance":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-300 shadow-sm">
          <ShieldCheck className="h-3 w-3 text-amber-700" />
          <span>Compliance Agent</span>
        </span>
      );
    case "agent_drafter":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-blue-50 text-blue-900 border border-blue-300 shadow-sm">
          <FileEdit className="h-3 w-3 text-blue-700" />
          <span>Drafting Agent</span>
        </span>
      );
    case "agent_verifier":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-300 shadow-sm">
          <CheckCircle2 className="h-3 w-3 text-purple-700" />
          <span>Verifier Agent</span>
        </span>
      );
    case "semantic_cache_hit":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-400 shadow-sm animate-pulse">
          <Zap className="h-3 w-3 text-emerald-700 fill-emerald-600" />
          <span>⚡ Semantic Cache Hit</span>
        </span>
      );
    case "model_escalation":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-orange-50 text-orange-900 border border-orange-300">
          <TrendingUp className="h-3 w-3 text-orange-700" />
          <span>model_escalation</span>
        </span>
      );
    case "equipment_graph_event":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-indigo-50 text-indigo-900 border border-indigo-300">
          <Share2 className="h-3 w-3 text-indigo-700" />
          <span>equipment_graph_event</span>
        </span>
      );
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
    case "corrective_rag_grade":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-cyan-50 text-cyan-900 border border-cyan-300">
          <ShieldCheck className="h-3 w-3 text-cyan-700" />
          <span>corrective_rag_grade</span>
        </span>
      );
    case "self_critique":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-indigo-50 text-indigo-900 border border-indigo-300">
          <ShieldAlert className="h-3 w-3 text-indigo-700" />
          <span>self_critique</span>
        </span>
      );
    case "human_approval":
    case "human_approval_gate":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-blue-50 text-blue-900 border border-blue-300">
          <UserCheck className="h-3 w-3 text-blue-700" />
          <span>human_approval_gate</span>
        </span>
      );
    case "search_memory":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-teal-50 text-teal-900 border border-teal-300">
          <BrainCircuit className="h-3 w-3 text-teal-700" />
          <span>search_memory</span>
        </span>
      );
    case "memory_ingest":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-300">
          <Database className="h-3 w-3 text-purple-700" />
          <span>memory_ingest</span>
        </span>
      );
    case "run_code":
    case "code_sandbox":
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
