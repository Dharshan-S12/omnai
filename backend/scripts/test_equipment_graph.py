import os
import sys
import uuid
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graph import record_equipment_event, get_equipment_history, query_equipment_by_criteria, list_all_equipment
from app.database import engine, Base, AsyncSessionLocal

async def test_equipment_graph_pipeline():
    print("=====================================================================")
    print("   TEST: Equipment Knowledge Graph (Ingest, Query & Criteria Filter) ")
    print("=====================================================================")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    task_1 = uuid.uuid4()
    task_2 = uuid.uuid4()
    task_3 = uuid.uuid4()

    # 1. Ingest Event 1: Baseline inspection for TRB-1105
    data_1 = {
        "equipment_id": "TRB-1105",
        "equipment_name": "High-Pressure Gas Turbine TRB-1105",
        "unit": "HCU",
        "equipment_type": "turbine",
        "inspection_date": "2024-01-15",
        "inspector": "E. Sharma",
        "vibration_rms_mms": 2.1,
        "bearing_temp_c": 62,
        "status": "COMPLIANT",
        "findings": "Baseline vibration velocity 2.1 mm/s within ISO Zone A normal operating limits."
    }
    node_1 = await record_equipment_event(task_id=task_1, structured_data=data_1, event_type="inspection")
    assert node_1 is not None, "Failed to create EquipmentNode for TRB-1105"
    assert node_1.equipment_id == "TRB-1105"
    print(f" [PASS] Ingested Event 1 for {node_1.equipment_id} ({node_1.unit})")

    # 2. Ingest Event 2: Degraded inspection for TRB-1105 (Vibration 5.8 mm/s)
    data_2 = {
        "equipment_id": "TRB-1105",
        "equipment_name": "High-Pressure Gas Turbine TRB-1105",
        "unit": "HCU",
        "equipment_type": "turbine",
        "inspection_date": "2024-03-20",
        "inspector": "E. Sharma",
        "vibration_rms_mms": 5.8,
        "bearing_temp_c": 78,
        "status": "NON_COMPLIANT",
        "findings": "Vibration increased significantly from 2.1 to 5.8 mm/s in Zone C alert threshold."
    }
    node_2 = await record_equipment_event(task_id=task_2, structured_data=data_2, event_type="inspection")
    print(f" [PASS] Ingested Event 2 for {node_2.equipment_id} (Updated node)")

    # 3. Ingest Event 3: Non-compliant valve VLV-7788 in HCU
    data_3 = {
        "equipment_id": "VLV-7788",
        "equipment_name": "Emergency Isolation Valve VLV-7788",
        "unit": "HCU",
        "equipment_type": "valve",
        "inspection_date": "2024-04-10",
        "inspector": "R. Menon",
        "status": "NON_COMPLIANT",
        "findings": "Seat leakage detected exceeding allowable bubble count. Gasket replacement required."
    }
    node_3 = await record_equipment_event(task_id=task_3, structured_data=data_3, event_type="inspection")
    print(f" [PASS] Ingested Event 3 for {node_3.equipment_id}")

    # 4. Test get_equipment_history("TRB-1105")
    history = await get_equipment_history("TRB-1105")
    assert history is not None, "Failed to retrieve history for TRB-1105"
    print(f"\n -> TRB-1105 History Summary:")
    print(f"    - ID: {history['equipment_id']}")
    print(f"    - Unit: {history['unit']}")
    print(f"    - Type: {history['equipment_type']}")
    print(f"    - Total Events: {history['events_count']}")
    assert history["events_count"] >= 2, f"Expected at least 2 events, got {history['events_count']}"
    for ev in history["events"]:
        print(f"      * [{ev['event_date']} | {ev['event_type']}]: Status: {ev['event_data'].get('status')}")

    # 5. Test query_equipment_by_criteria(unit="HCU", compliance_status="NON_COMPLIANT")
    print("\n -> Querying Knowledge Graph: 'All non-compliant equipment in HCU'...")
    results = await query_equipment_by_criteria(unit="HCU", compliance_status="NON_COMPLIANT")
    matched_ids = [r["equipment_id"] for r in results]
    print(f"    - Total Matched: {len(results)} -> {matched_ids}")
    assert "TRB-1105" in matched_ids, "Expected TRB-1105 in non-compliant HCU results"
    assert "VLV-7788" in matched_ids, "Expected VLV-7788 in non-compliant HCU results"

    # 6. Test list_all_equipment()
    all_eq = await list_all_equipment()
    print(f"\n -> All Registered Equipment Assets: {len(all_eq)} items")
    for eq in all_eq:
        print(f"    - {eq['equipment_id']} ({eq['equipment_type']} in {eq['unit']}) -> {eq['events_count']} event(s), latest: {eq['latest_status']}")

    print("\n=====================================================================")
    print("   ALL EQUIPMENT GRAPH TESTS PASSED SUCCESSFULLY!                    ")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(test_equipment_graph_pipeline())
