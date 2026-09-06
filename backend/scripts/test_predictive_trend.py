import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, AsyncSessionLocal
from app.models import EquipmentNode, EquipmentEvent
from app.graph.trends import analyze_trend
from app.graph.query import query_equipment_by_criteria

async def test_predictive_trend_analysis():
    print("=====================================================================")
    print("   TEST: Predictive Deterministic Trend Detection (Numpy / Graph)    ")
    print("=====================================================================")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Clean or Setup TRB-1105 in Knowledge Graph with sequential historical trend
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        # Clear existing TRB-1105 events to guarantee exact test dataset
        from sqlalchemy.future import select
        res = await db.execute(select(EquipmentNode).where(EquipmentNode.equipment_id == "TRB-1105"))
        node = res.scalars().first()
        if not node:
            node = EquipmentNode(
                id=uuid.uuid4(),
                equipment_id="TRB-1105",
                equipment_name="High-Pressure Gas Turbine TRB-1105",
                unit="HCU",
                equipment_type="turbine"
            )
            db.add(node)
            await db.commit()
        else:
            await db.execute(delete(EquipmentEvent).where(EquipmentEvent.equipment_node_id == node.id))
            await db.commit()

        # Add 3 sequential inspection events across 60 days showing worsening vibration:
        # Event 1 (60 days ago): 2.1 mm/s (Normal - Zone A)
        # Event 2 (30 days ago): 3.5 mm/s (Alert - Zone B)
        # Event 3 (Today): 5.8 mm/s (Action Required - Zone C)
        now = datetime.utcnow()
        dates_and_values = [
            (now - timedelta(days=60), 2.1, "Zone A - Normal"),
            (now - timedelta(days=30), 3.5, "Zone B - Alert"),
            (now, 5.8, "Zone C - Action Required")
        ]

        for dt, vib, zone in dates_and_values:
            ev = EquipmentEvent(
                id=uuid.uuid4(),
                equipment_node_id=node.id,
                event_type="inspection",
                event_date=dt,
                created_at=dt,
                event_data={
                    "equipment_id": "TRB-1105",
                    "unit": "HCU",
                    "vibration_rms_mms": vib,
                    "bearing_temp_c": 72.0,
                    "status": "NON_COMPLIANT" if vib > 4.5 else "COMPLIANT",
                    "findings": f"Observed vibration {vib} mm/s classified as {zone}"
                }
            )
            db.add(ev)

        # Setup another equipment with only 1 event (Insufficient data)
        pmp_res = await db.execute(select(EquipmentNode).where(EquipmentNode.equipment_id == "PMP-901"))
        pmp_node = pmp_res.scalars().first()
        if not pmp_node:
            pmp_node = EquipmentNode(
                id=uuid.uuid4(),
                equipment_id="PMP-901",
                equipment_name="Boiler Feed Pump PMP-901",
                unit="CDU",
                equipment_type="pump"
            )
            db.add(pmp_node)
            await db.commit()
        else:
            await db.execute(delete(EquipmentEvent).where(EquipmentEvent.equipment_node_id == pmp_node.id))
            await db.commit()

        db.add(EquipmentEvent(
            id=uuid.uuid4(),
            equipment_node_id=pmp_node.id,
            event_type="inspection",
            event_date=now,
            event_data={"equipment_id": "PMP-901", "vibration_rms_mms": 2.0}
        ))
        await db.commit()

    print(" [PASS] Seeded historical time-series data for TRB-1105 (2.1 -> 3.5 -> 5.8 mm/s)")

    # 2. Run analyze_trend for TRB-1105
    trend = await analyze_trend(equipment_id="TRB-1105", field="vibration_rms_mms", horizon_days=90)
    print("\n -> TRB-1105 Trend Analysis Result:")
    print(f"    - Trending Toward Violation: {trend['trending']}")
    print(f"    - Current Value: {trend['current_value']} mm/s")
    print(f"    - Slope per Day: {trend['slope_per_day']} mm/s/day ({trend['slope_per_month']} mm/s/month)")
    print(f"    - Projected Value (90d): {trend['projected_value']} mm/s")
    print(f"    - Days to Target Threshold ({trend['threshold']} mm/s): {trend['days_to_threshold']} days")
    print(f"    - Confidence: {trend['confidence']}")
    print(f"    - Historical Points Count: {len(trend['historical_points'])}")
    print(f"    - Projected Trajectory Points: {len(trend['projected_points'])}")

    assert trend["insufficient_data"] is False
    assert trend["trending"] is True
    assert trend["slope_per_day"] > 0, "Expected positive worsening slope"
    assert trend["current_value"] == 5.8
    assert len(trend["historical_points"]) == 3

    print(" [PASS] Deterministic numpy linear regression accurately identified positive worsening trend")

    # 3. Test Insufficient Data branch
    trend_pmp = await analyze_trend(equipment_id="PMP-901", field="vibration_rms_mms")
    assert trend_pmp["insufficient_data"] is True
    assert trend_pmp["trending"] is False
    assert trend_pmp["data_points_count"] == 1
    print(f" [PASS] PMP-901 (<3 data points) correctly returned insufficient_data=True")

    # 4. Test Graph Query with trending_toward_violation filter
    trending_matches = await query_equipment_by_criteria(trending_toward_violation=True)
    matched_ids = [m["equipment_id"] for m in trending_matches]
    print(f"\n -> Equipment Graph Query with filter `trending_toward_violation: true` -> Matched: {matched_ids}")
    assert "TRB-1105" in matched_ids
    assert "PMP-901" not in matched_ids
    print(" [PASS] Graph query filter `trending_toward_violation: true` correctly matched TRB-1105")

    print("\n=====================================================================")
    print("   ALL PREDICTIVE TREND DETECTION TESTS PASSED!                      ")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(test_predictive_trend_analysis())
