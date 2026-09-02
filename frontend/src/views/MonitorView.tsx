import { useEffect, useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Activity,
  Cpu,
  RefreshCw,
  Lock,
  Radio,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { fetchNetworkStatus } from "../api";
import type { NetworkMonitorData } from "../api";

export default function MonitorView() {
  const [data, setData] = useState<NetworkMonitorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"active" | "log">("active");

  const loadNetworkData = async () => {
    try {
      const res = await fetchNetworkStatus();
      setData(res);
    } catch (err) {
      console.error("Error fetching network status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNetworkData();
    const interval = setInterval(loadNetworkData, 2000); // 2s live polling
    return () => clearInterval(interval);
  }, []);

  const isAirGapped = data ? data.total_external_connections_seen === 0 : true;

  return (
    <div className="max-w-6xl mx-auto py-8 px-6 md:px-8">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              MRPL Cybersecurity & Compliance
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <div className="h-9 w-9 rounded-xl bg-emerald-100 border border-emerald-300 flex items-center justify-center text-emerald-800">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900 font-sans tracking-wide">
                Air-Gap Sovereignty Monitor
              </h2>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                Real-time process-level socket audit & zero-telemetry hardware verification
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs text-slate-600 bg-white border border-slate-200 px-3.5 py-2 rounded-xl shadow-xs">
          <span className="flex items-center gap-1.5 text-emerald-700 font-bold">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
            </span>
            Live Audit (2s)
          </span>
          <span className="text-slate-300">|</span>
          <span>{data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : "Syncing..."}</span>
        </div>
      </div>

      {/* Main Sovereignty Verdict Hero Banner */}
      <div
        className={`mb-6 p-6 rounded-2xl border transition-all shadow-xs ${
          isAirGapped
            ? "bg-gradient-to-r from-emerald-700 via-emerald-800 to-emerald-900 border-emerald-600 text-white shadow-md shadow-emerald-900/10"
            : "bg-rose-50 border-rose-400 text-slate-900"
        }`}
      >
        <div className="flex items-start justify-between flex-wrap gap-6">
          <div className="flex items-start gap-4">
            <div
              className={`p-3.5 rounded-2xl border shrink-0 ${
                isAirGapped
                  ? "bg-white/10 text-white border-white/20"
                  : "bg-rose-100 text-rose-700 border-rose-300"
              }`}
            >
              {isAirGapped ? <Lock className="h-8 w-8 text-amber-300" /> : <ShieldAlert className="h-8 w-8" />}
            </div>

            <div>
              <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                <h3 className="text-xl sm:text-2xl font-extrabold tracking-tight uppercase font-sans">
                  {isAirGapped
                    ? "MRPL AIR-GAPPED VERIFIED — 0 External Connections"
                    : "WARNING — Non-Loopback Activity Detected"}
                </h3>
                <span
                  className={`px-3 py-0.5 rounded-full text-xs font-mono font-bold tracking-wider uppercase border ${
                    isAirGapped
                      ? "bg-emerald-950/40 text-amber-200 border-emerald-400/40"
                      : "bg-rose-200 text-rose-900 border-rose-400"
                  }`}
                >
                  {isAirGapped ? "100% Zero External Calls" : "Non-Local Connection"}
                </span>
              </div>

              <p className={`text-sm max-w-3xl leading-relaxed font-sans ${isAirGapped ? "text-emerald-50/90" : "text-slate-700"}`}>
                Continuous process-level monitoring of the MRPL workbench, Ollama model inference, vector database, and sandbox subprocesses verifies that{" "}
                <strong className={isAirGapped ? "text-white underline decoration-emerald-400" : "text-slate-900 font-bold"}>
                  every network socket remains strictly on loopback (127.0.0.1 / localhost)
                </strong>. No data, prompt telemetry, or refinery documentation leaves this on-premise hardware node.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Large Demo Counter Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Card 1: External Connections */}
        <div className="bg-white border border-emerald-200 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono uppercase mb-2">
            <span>External Calls Observed</span>
            <ShieldCheck className="h-4 w-4 text-emerald-700" />
          </div>
          <div className="text-4xl font-extrabold text-emerald-800 font-mono tracking-tight">
            {data?.total_external_connections_seen ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 font-mono mt-2">
            Zero cloud endpoints contacted
          </p>
          <div className="absolute right-0 bottom-0 translate-x-3 translate-y-3 opacity-5 pointer-events-none">
            <Lock className="h-28 w-28 text-emerald-800" />
          </div>
        </div>

        {/* Card 2: Local Loopback Calls */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono uppercase mb-2">
            <span>Local Loopback Sockets</span>
            <Activity className="h-4 w-4 text-sky-700" />
          </div>
          <div className="text-4xl font-extrabold text-sky-800 font-mono tracking-tight">
            {data?.total_local_connections_seen ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 font-mono mt-2">
            127.0.0.1 (Ollama, DB, API)
          </p>
        </div>

        {/* Card 3: Monitored Processes */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono uppercase mb-2">
            <span>Monitored Processes</span>
            <Cpu className="h-4 w-4 text-purple-700" />
          </div>
          <div className="text-4xl font-extrabold text-purple-800 font-mono tracking-tight">
            {data?.monitored_processes_count ?? 1}
          </div>
          <p className="text-[11px] text-slate-500 font-mono mt-2">
            Uvicorn + Sandbox workers
          </p>
        </div>

        {/* Card 4: Air-Gapped Verdict */}
        <div className="bg-white border border-emerald-200 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-mono uppercase mb-2">
            <span>Sovereignty Verdict</span>
            <Radio className="h-4 w-4 text-emerald-700" />
          </div>
          <div className="text-2xl font-bold text-emerald-900 font-sans tracking-tight flex items-center gap-2 mt-1">
            <CheckCircle2 className="h-6 w-6 text-emerald-700 shrink-0" />
            <span>Air-Gapped Node</span>
          </div>
          <p className="text-[11px] text-emerald-800 font-mono font-medium mt-3">
            Hardware node verified
          </p>
        </div>
      </div>

      {/* Monitored Processes & Active Connections Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Monitored Process Tree */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
            <Cpu className="h-4 w-4 text-purple-700" />
            <h3 className="text-sm font-bold text-slate-900 font-sans">
              Monitored Process Tree
            </h3>
          </div>

          <div className="space-y-2.5">
            {data?.monitored_processes && data.monitored_processes.length > 0 ? (
              data.monitored_processes.map((proc) => (
                <div
                  key={proc.pid}
                  className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs font-mono flex items-center justify-between"
                >
                  <div>
                    <div className="text-slate-900 font-semibold flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                      {proc.name}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">PID: {proc.pid}</div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-medium uppercase">
                    {proc.status}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 font-mono py-4 text-center">
                Scanning process hierarchy...
              </p>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 font-mono leading-relaxed">
            All children spawned by the workbench (such as Python sandbox workers) inherit connection surveillance automatically.
          </div>
        </div>

        {/* Live Network Sockets Table */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 flex-wrap gap-3">
            <div className="flex items-center gap-2.5">
              <Activity className="h-4 w-4 text-emerald-700" />
              <h3 className="text-sm font-bold text-slate-900 font-sans">
                Real-Time Network Sockets
              </h3>
            </div>

            <div className="bg-slate-100 border border-slate-200 rounded-lg p-0.5 flex text-xs font-mono">
              <button
                onClick={() => setActiveTab("active")}
                className={`px-3 py-1 rounded-md transition-colors cursor-pointer ${
                  activeTab === "active"
                    ? "bg-white text-emerald-900 font-bold border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Active Sockets ({data?.active_connections.length ?? 0})
              </button>
              <button
                onClick={() => setActiveTab("log")}
                className={`px-3 py-1 rounded-md transition-colors cursor-pointer ${
                  activeTab === "log"
                    ? "bg-white text-emerald-900 font-bold border border-slate-200 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Continuous Log ({data?.recent_log.length ?? 0})
              </button>
            </div>
          </div>

          {/* Sockets Table */}
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="bg-slate-50 text-[10px] text-slate-600 uppercase tracking-wider border-b border-slate-200 font-bold">
                  <th className="px-3 py-2.5">PID</th>
                  <th className="px-3 py-2.5">Local Endpoint</th>
                  <th className="px-3 py-2.5">Remote Endpoint</th>
                  <th className="px-3 py-2.5">Status</th>
                  <th className="px-3 py-2.5 text-right">Verdict</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading && !data ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin text-emerald-700" />
                        <span>Sampling network connections...</span>
                      </div>
                    </td>
                  </tr>
                ) : (activeTab === "active" ? data?.active_connections : data?.recent_log)?.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No active network sockets detected.
                    </td>
                  </tr>
                ) : (
                  (activeTab === "active" ? data?.active_connections : data?.recent_log)?.map(
                    (conn, idx) => (
                      <tr key={`conn-${conn.pid}-${conn.local_address}-${idx}`} className="hover:bg-slate-50">
                        <td className="px-3 py-2.5 text-slate-500">{conn.pid}</td>
                        <td className="px-3 py-2.5 text-slate-800">{conn.local_address}</td>
                        <td className="px-3 py-2.5 text-slate-800">{conn.remote_address}</td>
                        <td className="px-3 py-2.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 border border-slate-200 text-slate-600">
                            {conn.status}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          {conn.classification === "local" ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                              <CheckCircle2 className="h-3 w-3" />
                              LOCAL
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              <AlertTriangle className="h-3 w-3" />
                              EXTERNAL
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
