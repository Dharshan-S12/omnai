import React from "react";
import { ScanText, Sparkles, FileSpreadsheet, Terminal, Files } from "lucide-react";

interface TaskTypeBadgeProps {
  type: "ocr" | "text_gen" | "doc_gen" | "code_exec" | "cross_doc_query" | string;
  size?: "sm" | "md";
}

export const TaskTypeBadge: React.FC<TaskTypeBadgeProps> = ({ type, size = "md" }) => {
  const iconSize = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";
  const padding = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  switch (type) {
    case "ocr":
      return (
        <span className={`inline-flex items-center gap-1.5 font-bold rounded-lg bg-emerald-50 text-emerald-900 border border-emerald-200 ${padding}`}>
          <ScanText className={`${iconSize} text-emerald-700`} />
          <span>OCR Extraction</span>
        </span>
      );
    case "text_gen":
      return (
        <span className={`inline-flex items-center gap-1.5 font-bold rounded-lg bg-sky-50 text-sky-900 border border-sky-200 ${padding}`}>
          <Sparkles className={`${iconSize} text-sky-700`} />
          <span>Text & Reasoning</span>
        </span>
      );
    case "doc_gen":
      return (
        <span className={`inline-flex items-center gap-1.5 font-bold rounded-lg bg-emerald-100 text-emerald-900 border border-emerald-300 ${padding}`}>
          <FileSpreadsheet className={`${iconSize} text-emerald-800`} />
          <span>Word DocGen</span>
        </span>
      );
    case "code_exec":
      return (
        <span className={`inline-flex items-center gap-1.5 font-bold rounded-lg bg-amber-50 text-amber-900 border border-amber-200 ${padding}`}>
          <Terminal className={`${iconSize} text-amber-700`} />
          <span>Code Execution</span>
        </span>
      );
    case "cross_doc_query":
      return (
        <span className={`inline-flex items-center gap-1.5 font-bold rounded-lg bg-emerald-50 text-emerald-900 border border-emerald-200 ${padding}`}>
          <Files className={`${iconSize} text-emerald-700`} />
          <span>Cross-Doc Ledger</span>
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 font-medium rounded-lg bg-slate-100 text-slate-700 border border-slate-200 ${padding}`}>
          <span>{type}</span>
        </span>
      );
  }
};
