import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Activity,
  RefreshCw,
  TrendingUp,
  Clock,
  ShieldAlert,
  BarChart3
} from "lucide-react";
import { fetchEquipmentDetail, fetchEquipmentTrend } from "../api";
import type { EquipmentDetail, EquipmentTrendData } from "../api";

export const EquipmentDetailView: React.FC = () => {
  const { equipment_id } = useParams<{ equipment_id: string }>();
  const [detail, setDetail] = useState<EquipmentDetail | null>(null);
  const [trend, setTrend] = useState<EquipmentTrendData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!equipment_id) return;
    try {
      setLoading(true);
      setError(null);
      const [detailData, trendData] = await Promise.all([
        fetchEquipmentDetail(equipment_id),
        fetchEquipmentTrend(equipment_id).catch(() => null)
      ]);
      setDetail(detailData);
      setTrend(trendData);
    } catch (err: any) {
      setError(err.message || "Failed to load equipment timeline");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [equipment_id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center space-y-4">
        <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Equipment History Unavailable</h2>
        <p className="text-sm text-slate-500">{error || "Equipment not found in knowledge graph"}</p>
        <Link
          to="/equipment"
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg font-semibold text-sm shadow hover:bg-indigo-700 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Equipment Graph</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-16">
      {/* Back button */}
      <div>
        <Link
          to="/equipment"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-indigo-600 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Knowledge Graph</span>
        </Link>
      </div>

      {/* Equipment Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3.5 bg-indigo-50 border border-indigo-200 rounded-xl text-indigo-700">
              <Cpu className="h-8 w-8" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold text-slate-900 font-mono tracking-tight">
                  {detail.equipment_id}
                </h1>
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Unit: {detail.unit || "HCU"}
                </span>
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-slate-100 text-slate-700">
                  {detail.equipment_type || "equipment"}
                </span>
                {trend?.trending && (
                  <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200 inline-flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    <span>Trending Toward Violation</span>
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-600 font-medium mt-1">
                {detail.equipment_name || `${detail.equipment_type?.toUpperCase()} Asset in Refinery Topology`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-right border-t sm:border-t-0 pt-3 sm:pt-0 w-full sm:w-auto justify-between sm:justify-end">
            <div>
              <span className="text-xs font-mono uppercase text-slate-400">Total Events</span>
              <p className="text-xl font-bold text-slate-900 font-mono">{detail.events_count}</p>
            </div>
            <div>
              <span className="text-xs font-mono uppercase text-slate-400">Registered</span>
              <p className="text-sm font-semibold text-slate-700 font-mono">
                {detail.created_at ? new Date(detail.created_at).toLocaleDateString() : "Active"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* --------------------------------------------------------- */}
      {/* PREDICTIVE TREND DETECTION & TRAJECTORY MINI-CHART */}
      {/* --------------------------------------------------------- */}
      {trend && !trend.insufficient_data && (
        <div className={`rounded-xl border p-6 shadow-sm ${
          trend.trending ? "bg-rose-50/40 border-rose-200" : "bg-white border-slate-200"
        }`}>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-200/80">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {trend.trending ? (
                  <ShieldAlert className="h-5 w-5 text-rose-600" />
                ) : (
                  <TrendingUp className="h-5 w-5 text-indigo-600" />
                )}
                <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                  <span>Proactive Predictive Trend Analysis</span>
                  <span className="text-xs font-mono font-normal text-slate-500">
                    ({trend.field})
                  </span>
                </h2>
              </div>
              <p className="text-xs text-slate-600">
                Pure deterministic linear regression over historical graph inspection points ({trend.confidence})
              </p>
            </div>

            {trend.trending && trend.days_to_threshold !== null && (
              <div className="bg-rose-100/80 border border-rose-300 rounded-xl px-4 py-2 flex items-center gap-3 shrink-0">
                <div className="p-2 bg-rose-600 text-white rounded-lg">
                  <Clock className="h-4 w-4" />
                </div>
                <div>
                  <span className="text-[10px] font-mono uppercase text-rose-800 font-bold block">
                    Projected Breach Horizon
                  </span>
                  <p className="text-sm font-bold font-mono text-rose-950">
                    {trend.days_to_threshold === 0 ? "Threshold Currently Exceeded" : `~${trend.days_to_threshold} Days to Violation`}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Metric KPI summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Current Value</span>
              <p className="text-base font-bold font-mono text-slate-900 mt-0.5">
                {trend.current_value} mm/s
              </p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Rate of Change</span>
              <p className={`text-base font-bold font-mono mt-0.5 ${
                (trend.slope_per_day || 0) > 0 ? "text-rose-600" : "text-emerald-700"
              }`}>
                {(trend.slope_per_day || 0) > 0 ? "+" : ""}{trend.slope_per_day} mm/s/day
              </p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Threshold Limit</span>
              <p className="text-base font-bold font-mono text-slate-900 mt-0.5">
                {trend.threshold} mm/s
              </p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Projected (90d)</span>
              <p className={`text-base font-bold font-mono mt-0.5 ${
                (trend.projected_value || 0) >= (trend.threshold || 4.5) ? "text-rose-700" : "text-slate-900"
              }`}>
                {trend.projected_value} mm/s
              </p>
            </div>
          </div>

          {/* SVG Mini Trend Trajectory Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between text-xs font-mono text-slate-500 mb-2">
              <span className="font-bold text-slate-700 flex items-center gap-1.5">
                <BarChart3 className="h-3.5 w-3.5 text-indigo-600" />
                <span>Historical Trajectory & Linear Regression Projection</span>
              </span>
              <div className="flex items-center gap-4 text-[11px]">
                <span className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-indigo-600" /> Historical
                </span>
                <span className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-rose-500" /> Projected
                </span>
                <span className="flex items-center gap-1">
                  <span className="h-0.5 w-3 bg-rose-400 border-t border-dashed border-rose-600" /> Threshold Limit ({trend.threshold} mm/s)
                </span>
              </div>
            </div>

            {/* SVG Visual Chart */}
            {(() => {
              const hist = trend.historical_points || [];
              const proj = trend.projected_points || [];
              const allPoints = [...hist, ...proj];
              if (allPoints.length === 0) return null;

              const maxVal = Math.max(
                trend.threshold || 7.1,
                trend.projected_value || 0,
                ...allPoints.map((p) => p.value)
              ) * 1.15;
              const minVal = 0;

              const width = 600;
              const height = 160;
              const padding = { top: 20, right: 30, bottom: 25, left: 40 };

              const getX = (idx: number, total: number) =>
                padding.left + (idx / Math.max(1, total - 1)) * (width - padding.left - padding.right);
              const getY = (val: number) =>
                height - padding.bottom - ((val - minVal) / Math.max(1, maxVal - minVal)) * (height - padding.top - padding.bottom);

              const histCoords = hist.map((p, i) => ({ x: getX(i, allPoints.length), y: getY(p.value), p }));
              const projCoords = proj.map((p, i) => ({ x: getX(hist.length + i, allPoints.length), y: getY(p.value), p }));

              const histPath = histCoords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ");
              const projPath = [
                histCoords[histCoords.length - 1],
                ...projCoords
              ].map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ");

              const thresholdY = getY(trend.threshold || 4.5);

              return (
                <div className="w-full overflow-x-auto">
                  <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-44 select-none">
                    {/* Grid lines */}
                    <line
                      x1={padding.left}
                      y1={padding.top}
                      x2={width - padding.right}
                      y2={padding.top}
                      stroke="#f1f5f9"
                      strokeWidth="1"
                    />
                    <line
                      x1={padding.left}
                      y1={height - padding.bottom}
                      x2={width - padding.right}
                      y2={height - padding.bottom}
                      stroke="#e2e8f0"
                      strokeWidth="1"
                    />

                    {/* Red Threshold Line */}
                    <line
                      x1={padding.left}
                      y1={thresholdY}
                      x2={width - padding.right}
                      y2={thresholdY}
                      stroke="#f43f5e"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={width - padding.right}
                      y={thresholdY - 4}
                      textAnchor="end"
                      className="text-[9px] font-mono fill-rose-600 font-bold"
                    >
                      Threshold Limit ({trend.threshold} mm/s)
                    </text>

                    {/* Historical Line */}
                    <path d={histPath} fill="none" stroke="#4f46e5" strokeWidth="2.5" />

                    {/* Projected Line (Dashed) */}
                    <path
                      d={projPath}
                      fill="none"
                      stroke="#f43f5e"
                      strokeWidth="2"
                      strokeDasharray="4 4"
                    />

                    {/* Historical Points */}
                    {histCoords.map((c, idx) => (
                      <g key={`hist-${idx}`}>
                        <circle cx={c.x} cy={c.y} r="4.5" fill="#ffffff" stroke="#4f46e5" strokeWidth="2.5" />
                        <text
                          x={c.x}
                          y={c.y - 8}
                          textAnchor="middle"
                          className="text-[10px] font-mono fill-slate-800 font-bold"
                        >
                          {c.p.value}
                        </text>
                        <text
                          x={c.x}
                          y={height - 8}
                          textAnchor="middle"
                          className="text-[9px] font-mono fill-slate-400"
                        >
                          {c.p.date.slice(5)}
                        </text>
                      </g>
                    ))}

                    {/* Projected Points */}
                    {projCoords.map((c, idx) => (
                      <g key={`proj-${idx}`}>
                        <circle cx={c.x} cy={c.y} r="4" fill="#ffffff" stroke="#f43f5e" strokeWidth="2" strokeDasharray="2 2" />
                        <text
                          x={c.x}
                          y={c.y - 8}
                          textAnchor="middle"
                          className="text-[9px] font-mono fill-rose-700 font-bold"
                        >
                          {c.p.value}
                        </text>
                        <text
                          x={c.x}
                          y={height - 8}
                          textAnchor="middle"
                          className="text-[9px] font-mono fill-rose-400 font-semibold"
                        >
                          +{c.p.days_from_latest}d
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Chronological Event Timeline */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Chronological Inspection & Compliance Event Timeline
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">{detail.events.length} Historical Node(s)</span>
        </div>

        <div className="relative pl-6 space-y-8 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          {detail.events.map((event) => {
            const data = event.event_data || {};
            const status = String(data.status || data.compliance_status || "").toUpperCase();
            const isNonCompliant =
              status.includes("NON") || status.includes("WARNING") || status.includes("FAIL");

            return (
              <div key={event.id} className="relative group">
                {/* Node icon */}
                <div
                  className={`absolute -left-6 top-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-white ${
                    isNonCompliant
                      ? "border-rose-500 text-rose-600"
                      : "border-emerald-500 text-emerald-600"
                  }`}
                >
                  {isNonCompliant ? (
                    <AlertTriangle className="h-3 w-3" />
                  ) : (
                    <CheckCircle2 className="h-3 w-3" />
                  )}
                </div>

                {/* Event Card */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 hover:border-indigo-300 transition shadow-xs">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-200/60 pb-3">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="text-xs font-mono font-bold text-slate-800">
                        {event.event_date || "Unknown Date"}
                      </span>
                      <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-white text-slate-700 border border-slate-300 font-semibold">
                        {event.event_type}
                      </span>
                      {status && (
                        <span
                          className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                            isNonCompliant
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : "bg-emerald-50 text-emerald-700 border-emerald-200"
                          }`}
                        >
                          {status}
                        </span>
                      )}
                    </div>

                    {event.source_task_id && (
                      <Link
                        to={`/tasks/${event.source_task_id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition"
                      >
                        <span>View Source Task #{event.source_task_id.slice(0, 8)}</span>
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    )}
                  </div>

                  {/* Measurements Grid */}
                  {(data.measurements || data.vibration_rms_mms || data.bearing_temp_c) && (
                    <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200/80 grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {data.vibration_rms_mms && (
                        <div>
                          <span className="text-[10px] font-mono text-slate-400 uppercase">Vibration RMS</span>
                          <p className="text-xs font-bold font-mono text-slate-800">
                            {data.vibration_rms_mms} mm/s
                          </p>
                        </div>
                      )}
                      {data.bearing_temp_c && (
                        <div>
                          <span className="text-[10px] font-mono text-slate-400 uppercase">Bearing Temp</span>
                          <p className="text-xs font-bold font-mono text-slate-800">
                            {data.bearing_temp_c} °C
                          </p>
                        </div>
                      )}
                      {data.inspector && (
                        <div>
                          <span className="text-[10px] font-mono text-slate-400 uppercase">Inspector</span>
                          <p className="text-xs font-bold text-slate-800">{data.inspector}</p>
                        </div>
                      )}
                      {data.sop_reference && (
                        <div>
                          <span className="text-[10px] font-mono text-slate-400 uppercase">SOP Reference</span>
                          <p className="text-xs font-bold text-slate-800 truncate">{data.sop_reference}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Findings / Notes */}
                  {(data.findings || data.summary_reason || data.task_prompt) && (
                    <div className="mt-3 text-xs text-slate-700 leading-relaxed font-sans bg-white/60 p-3 rounded-lg border border-slate-200/40">
                      <span className="font-semibold text-slate-800 block mb-0.5">Recorded Notes & Findings:</span>
                      {data.findings || data.summary_reason || data.task_prompt}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
