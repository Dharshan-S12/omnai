import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Share2,
  Filter,
  Search,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Cpu,
  Layers,
  TrendingUp
} from "lucide-react";
import { queryEquipmentGraph, fetchAllEquipment } from "../api";
import type { EquipmentSummary, GraphQueryResult } from "../api";

export const EquipmentGraphView: React.FC = () => {
  const [equipmentList, setEquipmentList] = useState<EquipmentSummary[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  const [unit, setUnit] = useState<string>("ALL");
  const [eventType, setEventType] = useState<string>("ALL");
  const [complianceStatus, setComplianceStatus] = useState<string>("ALL");
  const [trendingOnly, setTrendingOnly] = useState<boolean>(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryResults, setQueryResults] = useState<GraphQueryResult | null>(null);

  const loadEquipment = async () => {
    try {
      setLoadingList(true);
      const data = await fetchAllEquipment();
      setEquipmentList(data);
    } catch (err) {
      console.error("Failed to load equipment list:", err);
    } finally {
      setLoadingList(false);
    }
  };

  const handleRunQuery = async (
    overrideUnit?: string,
    overrideStatus?: string,
    overrideType?: string,
    overrideTrending?: boolean
  ) => {
    const targetUnit = overrideUnit !== undefined ? overrideUnit : unit;
    const targetStatus = overrideStatus !== undefined ? overrideStatus : complianceStatus;
    const targetType = overrideType !== undefined ? overrideType : eventType;
    const targetTrending = overrideTrending !== undefined ? overrideTrending : trendingOnly;

    try {
      setIsQuerying(true);
      const res = await queryEquipmentGraph({
        unit: targetUnit === "ALL" ? undefined : targetUnit,
        compliance_status: targetStatus === "ALL" ? undefined : targetStatus,
        event_type: targetType === "ALL" ? undefined : targetType,
        trending_toward_violation: targetTrending ? true : undefined,
      });
      setQueryResults(res);
    } catch (err) {
      console.error("Failed to query equipment graph:", err);
    } finally {
      setIsQuerying(false);
    }
  };

  useEffect(() => {
    loadEquipment();
    handleRunQuery("ALL", "ALL", "ALL", false);
  }, []);

  const totalNonCompliant = equipmentList.filter(
    (e) => e.latest_status && (e.latest_status.includes("NON") || e.latest_status.includes("WARNING"))
  ).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-700">
              <Share2 className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 font-sans tracking-tight">
                Sovereign Equipment Knowledge Graph
              </h1>
              <p className="text-sm text-slate-500 font-medium">
                Structured refinery topology, chronological event ledger & compliance graph
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={() => {
            loadEquipment();
            handleRunQuery();
          }}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-sm font-semibold rounded-lg shadow-sm transition"
        >
          <RefreshCw className={`h-4 w-4 ${loadingList || isQuerying ? "animate-spin" : ""}`} />
          <span>Refresh Graph</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-blue-50 text-blue-700 rounded-xl border border-blue-100">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">Tracked Equipment</p>
            <p className="text-2xl font-bold text-slate-900 mt-0.5">{equipmentList.length}</p>
            <p className="text-xs text-slate-400 mt-0.5">Turbines, Pumps, Valves, Compressors</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">Refinery Units</p>
            <p className="text-2xl font-bold text-slate-900 mt-0.5">
              {Array.from(new Set(equipmentList.map((e) => e.unit).filter(Boolean))).length || 1}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">HCU, CDU, VGO, FCCU</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-rose-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-100">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-rose-600 font-mono">Active Non-Compliances</p>
            <p className="text-2xl font-bold text-rose-700 mt-0.5">{totalNonCompliant}</p>
            <p className="text-xs text-rose-500 mt-0.5">ISO Zone C / Alert thresholds</p>
          </div>
        </div>
      </div>

      {/* Query Builder */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-indigo-600" />
            <h2 className="font-bold text-slate-900 text-sm tracking-tight uppercase font-mono">
              Knowledge Graph Structured Query Builder
            </h2>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400 font-mono">Demo Presets:</span>
            <button
              onClick={() => {
                setUnit("HCU");
                setComplianceStatus("NON_COMPLIANT");
                setEventType("ALL");
                setTrendingOnly(false);
                handleRunQuery("HCU", "NON_COMPLIANT", "ALL", false);
              }}
              className="text-xs px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded border border-indigo-200 transition"
            >
              Non-Compliant in HCU
            </button>
            <button
              onClick={() => {
                setUnit("ALL");
                setComplianceStatus("ALL");
                setEventType("ALL");
                setTrendingOnly(true);
                handleRunQuery("ALL", "ALL", "ALL", true);
              }}
              className="text-xs px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold rounded border border-rose-200 transition flex items-center gap-1"
            >
              <span>⚠️ Trending Toward Violation</span>
            </button>
            <button
              onClick={() => {
                setUnit("ALL");
                setComplianceStatus("ALL");
                setEventType("ALL");
                setTrendingOnly(false);
                handleRunQuery("ALL", "ALL", "ALL", false);
              }}
              className="text-xs px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded border border-slate-200 transition"
            >
              All Events
            </button>
          </div>
        </div>

        <div className="p-5 grid grid-cols-1 sm:grid-cols-5 gap-4 items-end">
          <div>
            <label className="block text-xs font-bold text-slate-600 font-mono uppercase mb-1.5">
              Refinery Unit
            </label>
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm rounded-lg px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Units</option>
              <option value="HCU">HCU (Hydrocracker Unit)</option>
              <option value="CDU">CDU (Crude Distillation)</option>
              <option value="VGO">VGO (Vacuum Gas Oil)</option>
              <option value="FCCU">FCCU (Fluid Catalytic Cracker)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-600 font-mono uppercase mb-1.5">
              Event Type
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm rounded-lg px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Event Types</option>
              <option value="inspection">Inspection Reports (OCR)</option>
              <option value="approval_note">Executive Approval Notes</option>
              <option value="compliance_check">SOP Compliance Checks</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-600 font-mono uppercase mb-1.5">
              Compliance Status
            </label>
            <select
              value={complianceStatus}
              onChange={(e) => setComplianceStatus(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm rounded-lg px-3 py-2 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="NON_COMPLIANT">Non-Compliant / Warning Only</option>
              <option value="COMPLIANT">Compliant Only</option>
            </select>
          </div>

          <div className="pb-1">
            <label className="flex items-center gap-2 cursor-pointer select-none bg-slate-50 border border-slate-300 px-3 py-2.5 rounded-lg hover:bg-slate-100 transition">
              <input
                type="checkbox"
                checked={trendingOnly}
                onChange={(e) => setTrendingOnly(e.target.checked)}
                className="h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
              />
              <span className="text-xs font-bold font-mono text-slate-700">
                Trending Toward Violation
              </span>
            </label>
          </div>

          <button
            onClick={() => handleRunQuery()}
            disabled={isQuerying}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-lg shadow transition disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            <span>{isQuerying ? "Querying Graph..." : "Execute Graph Query"}</span>
          </button>
        </div>
      </div>

      {/* Query Results Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              Query Results ({queryResults?.total_equipment_matched ?? 0} Equipment Nodes Matched)
            </h3>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Criteria: Unit [{queryResults?.query.unit || "ALL"}] • Status [{queryResults?.query.compliance_status || "ALL"}] • Event Type [{queryResults?.query.event_type || "ALL"}]
            </p>
          </div>
        </div>

        {queryResults && queryResults.results.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {queryResults.results.map((item) => (
              <div key={item.id} className="p-5 hover:bg-slate-50 transition flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="space-y-1.5 max-w-2xl">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="text-base font-bold font-mono text-slate-900 tracking-tight">
                      {item.equipment_id}
                    </span>
                    <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                      Unit: {item.unit || "HCU"}
                    </span>
                    <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {item.equipment_type || "equipment"}
                    </span>
                    {item.trend_analysis?.trending && (
                      <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200 inline-flex items-center gap-1">
                        <TrendingUp className="h-3 w-3 text-rose-600" />
                        <span>
                          Trending: Breach in ~{item.trend_analysis.days_to_threshold !== null ? `${item.trend_analysis.days_to_threshold}d` : "horizon"}
                        </span>
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700 font-medium">
                    {item.equipment_name || `${item.equipment_id} Industrial Asset`}
                  </p>

                  {/* Event summary previews */}
                  {item.events.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {item.events.slice(0, 2).map((ev) => {
                        const isNonComp =
                          ev.event_data?.status?.includes("NON") ||
                          ev.event_data?.compliance_status?.includes("NON") ||
                          ev.event_data?.status?.includes("WARNING");
                        return (
                          <div key={ev.id} className="flex items-center gap-2 text-xs text-slate-600">
                            <span className="font-mono text-slate-400">{ev.event_date || "Recent"}:</span>
                            <span
                              className={`inline-flex items-center px-1.5 py-0.2 rounded font-mono font-bold text-[10px] ${
                                isNonComp
                                  ? "bg-rose-50 text-rose-700 border border-rose-200"
                                  : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              }`}
                            >
                              {ev.event_data?.status || ev.event_type}
                            </span>
                            <span className="truncate max-w-md text-slate-500 font-medium">
                              {ev.event_data?.findings || ev.event_data?.summary_reason || "Recorded event entry"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right hidden sm:block">
                    <span className="text-xs font-mono text-slate-400">Total Events</span>
                    <p className="text-sm font-bold text-slate-800 font-mono">{item.matching_events_count} event(s)</p>
                  </div>
                  <Link
                    to={`/equipment/${encodeURIComponent(item.equipment_id)}`}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-indigo-200 hover:border-indigo-300 text-indigo-700 hover:bg-indigo-50 font-semibold text-xs rounded-lg shadow-sm transition"
                  >
                    <span>Timeline & History</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500">
            <Share2 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="font-semibold text-slate-700">No equipment matching this query criteria</p>
            <p className="text-xs text-slate-400 mt-1">Try selecting 'All Units' or 'All Statuses' in the query builder.</p>
          </div>
        )}
      </div>

      {/* Full Equipment Register */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 font-mono flex items-center gap-2">
            <Layers className="h-4 w-4 text-slate-500" />
            All Tracked Equipment Assets ({equipmentList.length})
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 p-5">
          {equipmentList.map((eq) => (
            <Link
              key={eq.id}
              to={`/equipment/${encodeURIComponent(eq.equipment_id)}`}
              className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition group shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start">
                  <span className="font-mono font-bold text-slate-900 group-hover:text-indigo-700 transition">
                    {eq.equipment_id}
                  </span>
                  <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                    {eq.unit || "HCU"}
                  </span>
                </div>
                <p className="text-xs text-slate-600 font-medium mt-1">
                  {eq.equipment_name || `${eq.equipment_type?.toUpperCase()} Asset`}
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center text-xs">
                <span className="text-slate-400 font-mono">{eq.events_count} event(s)</span>
                <span className="text-indigo-600 font-semibold group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                  View Timeline &rarr;
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};
