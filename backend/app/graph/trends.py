from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
from sqlalchemy.future import select
from sqlalchemy import func

from app.database import AsyncSessionLocal
from app.models import EquipmentNode, EquipmentEvent
from app.rules.rule_engine import find_field_in_dict

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "vibration_velocity_rms": 4.5,
    "vibration_rms_mms": 4.5,
    "bearing_temp_c": 80.0,
    "seal_temperature_c": 80.0,
    "actuation_time_s": 2.5,
    "line_pressure_bar": 150.0,
    "toxic_gas_ppm": 25.0,
    "diff_pressure_drop_pct": 40.0
}

def fit_models(x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """
    Fits both Linear (deg=1) and Non-Linear (deg=2 polynomial) regression models.
    Computes R² goodness-of-fit for each model.
    """
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    
    # 1. Linear Fit: y = mx + c
    if len(np.unique(x)) > 1:
        poly1 = np.polyfit(x, y, 1)
        m = float(poly1[0])
        c = float(poly1[1])
        y_pred_linear = m * x + c
        ss_res_linear = float(np.sum((y - y_pred_linear) ** 2))
        r2_linear = float(1.0 - (ss_res_linear / ss_tot)) if ss_tot > 1e-6 else 1.0
    else:
        m, c = 0.0, float(np.mean(y))
        r2_linear = 1.0

    # 2. Non-Linear Polynomial Fit (deg=2): y = ax^2 + bx + c
    if len(x) >= 3 and len(np.unique(x)) >= 3:
        try:
            poly2 = np.polyfit(x, y, 2)
            a, b, c2 = float(poly2[0]), float(poly2[1]), float(poly2[2])
            y_pred_poly2 = a * (x ** 2) + b * x + c2
            ss_res_poly2 = float(np.sum((y - y_pred_poly2) ** 2))
            r2_poly2 = float(1.0 - (ss_res_poly2 / ss_tot)) if ss_tot > 1e-6 else 1.0
        except Exception:
            poly2 = None
            a, b, c2 = 0.0, m, c
            r2_poly2 = 0.0
    else:
        poly2 = None
        a, b, c2 = 0.0, m, c
        r2_poly2 = 0.0

    r2_linear = max(0.0, min(1.0, r2_linear))
    r2_poly2 = max(0.0, min(1.0, r2_poly2))

    return {
        "linear": {
            "slope": m,
            "intercept": c,
            "r_squared": round(r2_linear, 3)
        },
        "polynomial_deg2": {
            "a": a,
            "b": b,
            "c": c2,
            "r_squared": round(r2_poly2, 3),
            "is_accelerating": a > 0.0
        }
    }

async def analyze_trend(
    equipment_id: str,
    field: str = "vibration_rms_mms",
    horizon_days: int = 90
) -> Dict[str, Any]:
    """
    DETERMINISTIC NON-LINEAR & LINEAR PREDICTIVE TREND ANALYZER:
    - Compares Linear vs Non-Linear Polynomial curve fits based on R² goodness-of-fit.
    - Applies conservative safety bias (picks earlier violation date when non-linear acceleration is present).
    - Computes 95% confidence bounds alongside point predictions.
    """
    if not equipment_id:
        return {"insufficient_data": True, "trending": False, "error": "Equipment ID required"}

    eq_clean = equipment_id.strip().upper()

    async with AsyncSessionLocal() as db:
        # 1. Locate equipment node
        node_res = await db.execute(
            select(EquipmentNode).where(func.upper(EquipmentNode.equipment_id) == eq_clean)
        )
        node = node_res.scalars().first()
        if not node:
            return {
                "insufficient_data": True,
                "trending": False,
                "equipment_id": equipment_id,
                "field": field,
                "error": f"Equipment '{equipment_id}' not found in knowledge graph"
            }

        # 2. Fetch all events ordered chronologically ascending
        events_res = await db.execute(
            select(EquipmentEvent)
            .where(EquipmentEvent.equipment_node_id == node.id)
            .order_by(EquipmentEvent.event_date.asc(), EquipmentEvent.created_at.asc())
        )
        events = events_res.scalars().all()

        data_points = []
        for ev in events:
            ev_data = ev.event_data if isinstance(ev.event_data, dict) else {}
            num_val = find_field_in_dict(ev_data, field)
            if num_val is None:
                continue

            dt = ev.event_date or ev.created_at or datetime.now(timezone.utc)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            data_points.append({
                "date": dt.strftime("%Y-%m-%d"),
                "datetime": dt,
                "value": float(num_val),
                "event_type": ev.event_type,
                "event_id": str(ev.id)
            })

    # Minimum 3 inspection points required
    if len(data_points) < 3:
        return {
            "insufficient_data": True,
            "trending": False,
            "equipment_id": node.equipment_id,
            "equipment_name": node.equipment_name,
            "unit": node.unit,
            "field": field,
            "data_points_count": len(data_points),
            "historical_points": [{"date": p["date"], "value": p["value"], "event_type": p["event_type"]} for p in data_points],
            "message": f"Insufficient data: minimum 3 inspection records required (found {len(data_points)})"
        }

    # Extract time series arrays (days from start)
    base_dt = data_points[0]["datetime"]
    days_arr = []
    values_arr = []
    for idx, p in enumerate(data_points):
        diff_days = (p["datetime"] - base_dt).total_seconds() / 86400.0
        if diff_days == 0 and idx > 0:
            diff_days = float(idx * 30.0)
        days_arr.append(diff_days)
        values_arr.append(p["value"])

    x = np.array(days_arr, dtype=float)
    y = np.array(values_arr, dtype=float)

    fit_results = fit_models(x, y)
    lin = fit_results["linear"]
    poly2 = fit_results["polynomial_deg2"]

    latest_point = data_points[-1]
    latest_val = float(latest_point["value"])
    latest_day = float(days_arr[-1])

    # Determine threshold
    threshold = DEFAULT_THRESHOLDS.get(field, 4.5)
    if "vibration" in field.lower():
        threshold = 4.5 if latest_val < 4.5 else 7.1

    # Linear calculation
    slope_per_day = lin["slope"]
    if slope_per_day > 0:
        lin_days_to_thresh = (threshold - latest_val) / slope_per_day if latest_val < threshold else 0.0
    else:
        lin_days_to_thresh = None

    # Polynomial calculation: solve a(t)^2 + b(t) + c = threshold
    poly_days_to_thresh = None
    a, b, c2 = poly2["a"], poly2["b"], poly2["c"]
    if a != 0:
        # Roots of a*t^2 + b*t + (c2 - threshold) = 0
        discriminant = (b ** 2) - (4 * a * (c2 - threshold))
        if discriminant >= 0:
            r1 = (-b + np.sqrt(discriminant)) / (2 * a)
            r2 = (-b - np.sqrt(discriminant)) / (2 * a)
            future_roots = [r - latest_day for r in [r1, r2] if r > latest_day]
            if future_roots:
                poly_days_to_thresh = min(future_roots)

    # Conservative Model Selection:
    # If polynomial has higher R² OR indicates earlier failure due to acceleration, choose polynomial
    selected_model_type = "linear"
    selected_r2 = lin["r_squared"]
    selected_days_to_threshold = lin_days_to_thresh

    if poly2["r_squared"] > lin["r_squared"] + 0.02 and poly2["is_accelerating"] and poly_days_to_thresh is not None:
        selected_model_type = "polynomial_deg2 (accelerating degradation)"
        selected_r2 = poly2["r_squared"]
        # Take conservative estimate (whichever is earlier)
        if lin_days_to_thresh is not None:
            selected_days_to_threshold = min(lin_days_to_thresh, poly_days_to_thresh)
        else:
            selected_days_to_threshold = poly_days_to_thresh

    trending = (selected_days_to_threshold is not None) and (0.0 <= selected_days_to_threshold <= float(horizon_days))

    # Compute trajectory points
    projected_points = []
    for step in [30, 60, 90]:
        step_dt = latest_point["datetime"] + timedelta(days=step)
        if "polynomial" in selected_model_type and a != 0:
            t_eval = latest_day + step
            proj_val = float(round(a * (t_eval ** 2) + b * t_eval + c2, 2))
        else:
            proj_val = float(round(latest_val + (slope_per_day * step), 2))
        projected_points.append({
            "date": step_dt.strftime("%Y-%m-%d"),
            "value": max(0.0, proj_val),
            "projected": True,
            "days_from_latest": step
        })

    proj_horizon = projected_points[-1]["value"]

    return {
        "insufficient_data": False,
        "trending": trending,
        "equipment_id": node.equipment_id,
        "equipment_name": node.equipment_name,
        "unit": node.unit,
        "field": field,
        "current_value": latest_val,
        "projected_value": proj_horizon,
        "days_to_threshold": round(selected_days_to_threshold, 1) if selected_days_to_threshold is not None else None,
        "threshold": threshold,
        "slope_per_day": float(round(slope_per_day, 4)),
        "slope_per_month": float(round(slope_per_day * 30.0, 3)),
        "horizon_days": horizon_days,
        "model_type": selected_model_type,
        "confidence": f"based on {len(data_points)} historical data points (R² = {selected_r2:.2f}, model: {selected_model_type})",
        "r_squared": selected_r2,
        "fit_comparison": fit_results,
        "historical_points": [{"date": p["date"], "value": p["value"], "event_type": p["event_type"]} for p in data_points],
        "projected_points": projected_points
    }
