import { useEffect, useState } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import {
  UploadCloud,
  ListOrdered,
  Sparkles,
  Radio,
  Lock,
  Cpu,
  AlertCircle,
  Database,
  Layers,
  Gauge
} from "lucide-react";
import { fetchTasks, fetchNetworkStatus, fetchHealthStatus } from "../api";
import type { HealthStatus } from "../api";

export default function Layout() {
  const location = useLocation();
  const [runningCount, setRunningCount] = useState<number>(0);
  const [externalCalls, setExternalCalls] = useState<number>(0);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const tasks = await fetchTasks();
        const active = tasks.filter((t) => t.status === "running" || t.status === "pending").length;
        setRunningCount(active);
      } catch {
        // quiet fallback
      }

      try {
        const net = await fetchNetworkStatus();
        setExternalCalls(net.total_external_connections_seen);
      } catch {
        // quiet fallback
      }

      try {
        const h = await fetchHealthStatus();
        setHealth(h);
      } catch {
        setHealth({
          status: "degraded",
          db: "unreachable",
          ollama_status: "unreachable",
        });
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 2500);
    return () => clearInterval(interval);
  }, []);

  const isOmniActive = location.pathname === "/" || location.pathname === "/chat";
  const isUploadActive = location.pathname === "/upload";
  const isTasksActive = location.pathname === "/tasks" || location.pathname.startsWith("/task/");
  const isMonitorActive = location.pathname === "/monitor";

  const isOllamaConnected = health?.ollama_status === "connected";

  return (
    <div className="flex flex-col h-screen w-full bg-slate-50 text-slate-900 font-sans antialiased overflow-hidden">
      {/* Top MRPL Corporate Branding & Industrial Status Bar */}
      <header className="bg-white border-b border-slate-200/90 px-5 py-2.5 flex items-center justify-between shadow-xs shrink-0 z-20">
        <div className="flex items-center gap-4">
          {/* MRPL Official Logo with OmniAI Badge */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-emerald-800 via-emerald-700 to-emerald-950 flex items-center justify-center text-white shadow-md shadow-emerald-900/15 border border-emerald-600/30">
              <span className="font-extrabold text-sm tracking-tighter text-amber-300 font-mono">M</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-base tracking-tight text-slate-900 font-sans">
                  MRPL
                </span>
                <span className="text-[11px] font-black tracking-wide text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200 uppercase font-mono">
                  OmniAI™
                </span>
                <span className="text-[10px] text-slate-500 font-medium hidden sm:inline-block">
                  ONGC Group CPSE
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                Mangalore Refinery and Petrochemicals Limited <span className="text-slate-300">•</span> Sovereign Industrial Node
              </p>
            </div>
          </div>
        </div>

        {/* Live Refinery Telemetry & Air-Gap Compliance Ticker */}
        <div className="flex items-center gap-3">
          {/* Active Refinery Plant Node */}
          <div className="hidden lg:flex items-center gap-2 bg-slate-100/80 border border-slate-200 px-3 py-1.5 rounded-lg text-slate-600 font-mono text-[11px]">
            <Gauge className="h-3.5 w-3.5 text-emerald-700" />
            <span>Kuthethoor Refinery Complex</span>
          </div>

          {/* Air-Gap Security Pill */}
          <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg font-mono text-[11px] text-emerald-900 font-bold shadow-xs">
            <Lock className="h-3.5 w-3.5 text-emerald-700" />
            <span>{externalCalls} Ext Sockets</span>
            <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse ml-0.5" />
          </div>
        </div>
      </header>

      {/* Main Container: Sidebar + Active Canvas */}
      <div className="flex flex-1 overflow-hidden">
        {/* Bespoke MRPL Sidebar Navigation */}
        <aside className="w-64 border-r border-slate-200 bg-white flex flex-col shrink-0 shadow-xs z-10">
          {/* Sidebar Section Title */}
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500">
              Cognitive Workspaces
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">
              v2.4 Sovereign
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 p-3 flex flex-col gap-1 overflow-y-auto">
            <Link
              to="/chat"
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isOmniActive
                  ? "bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-900/15"
                  : "text-slate-700 hover:text-emerald-900 hover:bg-emerald-50/80 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <Sparkles className={`h-4 w-4 ${isOmniActive ? "text-amber-300" : "text-emerald-700"}`} />
                <span>Omni AI Studio</span>
              </div>
              <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                isOmniActive ? "bg-emerald-900/60 text-amber-200" : "bg-emerald-100 text-emerald-800"
              }`}>
                PRIMARY
              </span>
            </Link>

            <Link
              to="/upload"
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isUploadActive
                  ? "bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-900/15"
                  : "text-slate-700 hover:text-emerald-900 hover:bg-emerald-50/80 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <UploadCloud className={`h-4 w-4 ${isUploadActive ? "text-white" : "text-emerald-700"}`} />
                <span>Document Vision Studio</span>
              </div>
            </Link>

            <Link
              to="/tasks"
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isTasksActive
                  ? "bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-900/15"
                  : "text-slate-700 hover:text-emerald-900 hover:bg-emerald-50/80 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <ListOrdered className={`h-4 w-4 ${isTasksActive ? "text-white" : "text-emerald-700"}`} />
                <span>Task Execution Ledger</span>
              </div>
              {runningCount > 0 && (
                <span className="h-5 px-2 rounded-full bg-amber-500 text-white font-mono text-[11px] font-bold flex items-center justify-center animate-pulse">
                  {runningCount}
                </span>
              )}
            </Link>

            <Link
              to="/monitor"
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isMonitorActive
                  ? "bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-900/15"
                  : "text-slate-700 hover:text-emerald-900 hover:bg-emerald-50/80 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <Radio className={`h-4 w-4 ${isMonitorActive ? "text-amber-300" : "text-emerald-700"}`} />
                <span>Air-Gap SOC Monitor</span>
              </div>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                isMonitorActive ? "bg-emerald-900/60 text-emerald-100" : "bg-emerald-100 text-emerald-800"
              }`}>
                0 Ext
              </span>
            </Link>

            {/* Specialized OmniAI Engines Directory */}
            <div className="mt-4 pt-3 border-t border-slate-100">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 px-3 block mb-2">
                Omni AI Intelligence Cores
              </span>
              <div className="space-y-1 text-xs text-slate-600 px-3">
                <div className="flex items-center justify-between py-1 font-mono text-[11px]">
                  <span className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                    OmniVision
                  </span>
                  <span className="text-slate-500">qwen2.5vl:7b</span>
                </div>
                <div className="flex items-center justify-between py-1 font-mono text-[11px]">
                  <span className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                    OmniCode
                  </span>
                  <span className="text-slate-500">coder:3b</span>
                </div>
                <div className="flex items-center justify-between py-1 font-mono text-[11px]">
                  <span className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-500" />
                    OmniReason
                  </span>
                  <span className="text-slate-500">qwen2.5:3b</span>
                </div>
                <div className="flex items-center justify-between py-1 font-mono text-[11px]">
                  <span className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                    OmniDoc
                  </span>
                  <span className="text-slate-500">7b-instruct</span>
                </div>
              </div>
            </div>
          </nav>

          {/* System Hardware & PostgreSQL DB Footer */}
          <div className="p-3 border-t border-slate-200 text-xs font-mono space-y-2 bg-slate-50/70">
            {/* Ollama Local Engine Status */}
            <div
              className={`p-2.5 rounded-xl border flex flex-col gap-1 transition-all ${
                isOllamaConnected
                  ? "bg-white border-emerald-200 text-slate-800 shadow-xs"
                  : "bg-amber-50 border-amber-300 text-amber-900"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-bold text-[11px] text-slate-800">
                  <Cpu className={`h-3.5 w-3.5 ${isOllamaConnected ? "text-emerald-700" : "text-amber-600"}`} />
                  <span>Ollama Core Fleet</span>
                </div>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                    isOllamaConnected
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-amber-200 text-amber-900 border border-amber-400"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      isOllamaConnected ? "bg-emerald-600" : "bg-amber-500"
                    }`}
                  />
                  {isOllamaConnected ? "Online" : "Offline"}
                </span>
              </div>
              {!isOllamaConnected && (
                <div className="text-[10px] text-amber-800 font-sans flex items-center gap-1 mt-0.5">
                  <AlertCircle className="h-3 w-3 shrink-0 text-amber-700" />
                  <span>Check local Ollama on port 11434</span>
                </div>
              )}
            </div>

            {/* Database & On-Prem Sovereign Specs */}
            <div className="bg-white border border-slate-200 rounded-xl p-2.5 space-y-1 text-[11px]">
              <div className="flex items-center justify-between text-slate-600">
                <span className="flex items-center gap-1.5 font-medium">
                  <Database className="h-3 w-3 text-emerald-700" />
                  Task Ledger DB
                </span>
                <span className="font-bold text-emerald-800 font-mono">Port 5433</span>
              </div>
              <div className="flex items-center justify-between text-slate-600">
                <span className="flex items-center gap-1.5 font-medium">
                  <Layers className="h-3 w-3 text-emerald-700" />
                  Air-Gapped Node
                </span>
                <span className="font-bold text-emerald-800 font-mono">0 Telemetry</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto bg-slate-50 industrial-grid-subtle">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
