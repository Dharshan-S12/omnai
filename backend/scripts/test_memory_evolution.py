import os
import sys
import time
import json
import asyncio
import httpx
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

API_BASE_URL = "http://localhost:8000"
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "test_memory"))
REPORT_1_PATH = os.path.join(STORAGE_DIR, "trb1105_inspection_1.png")
REPORT_2_PATH = os.path.join(STORAGE_DIR, "trb1105_inspection_2.png")

def create_inspection_image(
    file_path: str,
    doc_ref: str,
    date_str: str,
    equipment_id: str,
    vibration_val: str,
    status_val: str,
    findings_val: str
):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    width, height = 900, 700
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # Outer border & header banner
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#1A365D", width=3)
    draw.rectangle([(25, 25), (width - 25, 90)], fill="#1A365D")
    draw.text((45, 42), f"SOVEREIGN INDUSTRIAL FACILITY - EQUIPMENT INSPECTION REPORT", fill="white")

    lines = [
        f"Document Reference: {doc_ref}",
        "Standard Applied: SOP-MNT-042 Routine Pump & Turbine Vibration Inspection",
        "--------------------------------------------------------------------------------",
        f"Equipment Tag ID: {equipment_id}",
        "Location: Refinery Unit 4, High Pressure Feed Train",
        f"Date of Inspection: {date_str}",
        "Inspector: E. Sharma, Lead Reliability Engineer",
        "--------------------------------------------------------------------------------",
        "RECORDED MEASUREMENTS & READINGS:",
        f"  - Vibration Velocity Peak RMS: {vibration_val}",
        "  - Peak Dominant Frequency: 120 Hz",
        "  - Bearing Temperature: 78 deg C",
        "--------------------------------------------------------------------------------",
        "COMPLIANCE EVALUATION & FINDINGS:",
        f"  - Compliance Status: {status_val}",
        f"  - Findings: {findings_val}",
        "--------------------------------------------------------------------------------",
        "Authorized By: Sovereign Reliability Directorate"
    ]

    y = 120
    for l in lines:
        if l.startswith("---"):
            draw.line([(45, y + 6), (width - 45, y + 6)], fill="#A0AEC0", width=1)
            y += 18
        elif any(l.startswith(k) for k in ["RECORDED", "COMPLIANCE", "Equipment Tag"]):
            draw.text((45, y), l, fill="#1A202C")
            y += 26
        else:
            draw.text((45, y), l, fill="#2D3748")
            y += 24

    image.save(file_path, "PNG")
    print(f"Generated synthetic inspection report: {file_path}")
    return file_path

async def run_memory_evolution_test():
    print("=====================================================================")
    print("       LONG-TERM EVOLVING MEMORY LAYER - PHASE 10 VERIFICATION       ")
    print("=====================================================================\n")

    from app.database import engine, Base, AsyncSessionLocal
    import app.models
    from app.models import Task, TaskStatus, TaskType, MemoryEntry, MemoryLink
    from app.memory import ingest_memory, search_memory, get_memory_history, compute_strength
    from sqlalchemy.future import select
    from sqlalchemy import desc

    # 0. Ensure Database Schema initialized
    print("[0] Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(" -> Database tables initialized.\n")

    # 1. Create Synthetic Inspection Reports
    print("[1] Creating Synthetic Inspection Reports for Equipment TRB-1105...")
    img1 = create_inspection_image(
        file_path=REPORT_1_PATH,
        doc_ref="RPT-INSP-2024-01-101",
        date_str="2024-01-15",
        equipment_id="TRB-1105",
        vibration_val="2.1 mm/s",
        status_val="Compliant (Zone A Normal)",
        findings_val="Baseline vibration within normal limits. Equipment satisfactory."
    )

    img2 = create_inspection_image(
        file_path=REPORT_2_PATH,
        doc_ref="RPT-INSP-2024-03-205",
        date_str="2024-03-20",
        equipment_id="TRB-1105",
        vibration_val="5.8 mm/s",
        status_val="Warning / Non-Compliant (Zone C Alert)",
        findings_val="Vibration increased significantly from 2.1 to 5.8 mm/s. High harmonic detected."
    )

    # 2. Ingest Inspection 1 (Baseline: 2.1 mm/s)
    print("\n[2] Ingesting Inspection #1 (Baseline 2.1 mm/s) into Memory Layer...")
    struct1 = {
        "document_title": "Turbine Inspection Report",
        "document_type": "inspection",
        "metadata": {
            "Equipment Tag ID": "TRB-1105",
            "Date of Inspection": "2024-01-15",
            "Inspector": "E. Sharma",
            "Standard Applied": "SOP-MNT-042 Routine Pump & Turbine Vibration Inspection"
        },
        "measurements": {
            "vibration_rms_mms": 2.1,
            "bearing_temp_c": 62
        },
        "compliance_status": "COMPLIANT",
        "findings": "Baseline vibration velocity 2.1 mm/s within ISO Zone A normal operating limits."
    }

    task1_id = app.models.uuid.uuid4()
    async with AsyncSessionLocal() as db:
        t1 = Task(id=task1_id, task_type=TaskType.ocr, input_ref=img1, status=TaskStatus.done, output_ref=json.dumps(struct1))
        db.add(t1)
        await db.commit()

    mem1 = await ingest_memory(task_id=task1_id, structured_output=struct1, doc_type="inspection")
    print(f" -> Memory #1 Ingested! ID: {mem1.id}")
    print(f"    Entity Key: {mem1.entity_key}")
    print(f"    Summary: {mem1.summary_text}")
    print(f"    Is Current: {mem1.superseded_by is None}")

    # 3. Ingest Inspection 2 (Evolution: 5.8 mm/s)
    print("\n[3] Ingesting Inspection #2 (Worse Vibration 5.8 mm/s) for SAME equipment...")
    struct2 = {
        "document_title": "Turbine Inspection Report",
        "document_type": "inspection",
        "metadata": {
            "Equipment Tag ID": "TRB-1105",
            "Date of Inspection": "2024-03-20",
            "Inspector": "E. Sharma",
            "Standard Applied": "SOP-MNT-042 Routine Pump & Turbine Vibration Inspection"
        },
        "measurements": {
            "vibration_rms_mms": 5.8,
            "bearing_temp_c": 78
        },
        "compliance_status": "WARNING_NON_COMPLIANT",
        "findings": "Vibration increased significantly from 2.1 mm/s to 5.8 mm/s in Zone C alert."
    }

    task2_id = app.models.uuid.uuid4()
    async with AsyncSessionLocal() as db:
        t2 = Task(id=task2_id, task_type=TaskType.ocr, input_ref=img2, status=TaskStatus.done, output_ref=json.dumps(struct2))
        db.add(t2)
        await db.commit()

    mem2 = await ingest_memory(task_id=task2_id, structured_output=struct2, doc_type="inspection")
    print(f" -> Memory #2 Ingested! ID: {mem2.id}")
    print(f"    Entity Key: {mem2.entity_key}")
    print(f"    Summary: {mem2.summary_text}")
    print(f"    Is Current: {mem2.superseded_by is None}")

    # 4. Confirm Database Evolution Chain & Links
    print("\n[4] Verifying Database Evolution Chain and Graph Links...")
    async with AsyncSessionLocal() as db:
        res1 = await db.execute(select(MemoryEntry).where(MemoryEntry.id == mem1.id))
        fresh_mem1 = res1.scalars().first()

        res2 = await db.execute(select(MemoryEntry).where(MemoryEntry.id == mem2.id))
        fresh_mem2 = res2.scalars().first()

        print(f" -> Memory #1 superseded_by: {fresh_mem1.superseded_by} (Expected: {fresh_mem2.id})")
        assert fresh_mem1.superseded_by == fresh_mem2.id, "Error: Memory #1 was not superseded by Memory #2!"

        links_res = await db.execute(
            select(MemoryLink).where(
                (MemoryLink.source_memory_id == fresh_mem2.id) | (MemoryLink.target_memory_id == fresh_mem2.id)
            )
        )
        links = links_res.scalars().all()
        print(f" -> Memory #2 Graph Links Found: {len(links)}")
        for l in links:
            print(f"    * Link: {l.source_memory_id} -> {l.target_memory_id} [Relation: {l.relation_type}]")

        has_equipment_link = any(l.relation_type == "same_equipment" for l in links)
        has_temporal_link = any(l.relation_type == "temporal_sequence" for l in links)
        print(f" -> Confirmed 'same_equipment' link: {has_equipment_link}")
        print(f" -> Confirmed 'temporal_sequence' link: {has_temporal_link}")
        assert has_equipment_link or has_temporal_link, "Error: Missing graph links between memory entries!"

    # 5. Call search_memory with query "vibration trend for TRB-1105"
    print("\n[5] Executing search_memory(query='vibration trend for TRB-1105')...")
    search_results = await search_memory(query="vibration trend for TRB-1105", top_k=5)
    print(f" -> Retrieved {len(search_results)} search results.")
    for idx, r in enumerate(search_results):
        print(f"\n Match #{idx+1}:")
        print(f"   Entity: {r['entity_key']}")
        print(f"   Summary: {r['summary_text']}")
        print(f"   Current Active: {r['is_current']}")
        print(f"   Similarity: {r['similarity']} | Computed Strength: {r['computed_strength']} | Combined Score: {r['combined_score']}")
        print(f"   Explainability Field: \"{r['explanation']}\"")
        print(f"   Linked Memories in Context: {len(r['linked_memories'])}")
        for lm in r['linked_memories']:
            print(f"     - [Linked {lm['entity_key']} | Rel: {lm['relation_types']} | Current: {lm['is_current']}]: {lm['summary_text']}")

    assert len(search_results) > 0, "Error: search_memory returned no results!"
    assert "explanation" in search_results[0] and search_results[0]["explanation"], "Error: Missing explanation field!"

    # 6. Call get_memory_history for equipment_id:TRB-1105
    print("\n[6] Calling get_memory_history(entity_key='equipment_id:TRB-1105')...")
    history = await get_memory_history(entity_key="equipment_id:TRB-1105")
    print(f" -> Entity: {history['entity_key']}")
    print(f" -> Total Historical Memories: {history['total_memories']}")
    print(f" -> Current Active Memory: {history['current_memory']['summary_text'] if history['current_memory'] else 'None'}")
    print(f" -> Chronological Evolution Chain:")
    for idx, item in enumerate(history['evolution_chain']):
        stat = "CURRENT" if item['is_current'] else f"SUPERSEDED by {item['superseded_by'][:8]}..."
        print(f"   [{idx+1}] ID: {item['id'][:8]} | Status: {stat} | Strength: {item['computed_strength']} | Created: {item['created_at']}")
        print(f"       Summary: {item['summary_text']}")

    assert history["total_memories"] >= 2, "Error: Evolution chain contains fewer than 2 memories!"
    assert history["current_memory"]["id"] == str(mem2.id), "Error: Current memory is not the latest inspection!"

    # 7. Check HTTP / ASGI REST API Endpoints
    print("\n[7] Testing REST API Endpoint GET /memory/equipment_id:TRB-1105 and POST /memory/search...")
    from app.main import app
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test GET /memory/equipment_id:TRB-1105
        resp = await client.get("/memory/equipment_id:TRB-1105")
        assert resp.status_code == 200, f"Error: GET /memory/ returned status {resp.status_code}: {resp.text}"
        api_data = resp.json()
        print(f" -> ASGI GET /memory/equipment_id:TRB-1105: 200 OK")
        print(f"    Total memories: {api_data['total_memories']}")
        print(f"    Current memory: {api_data['current_memory']['summary_text'][:80]}...")
        assert api_data["total_memories"] >= 2, "Error: Evolution chain in API response has fewer than 2 memories!"

        # Test POST /memory/search
        search_resp = await client.post("/memory/search", json={"query": "vibration trend TRB-1105", "top_k": 5})
        assert search_resp.status_code == 200, f"Error: POST /memory/search returned status {search_resp.status_code}"
        search_data = search_resp.json()
        print(f" -> ASGI POST /memory/search: 200 OK")
        print(f"    Search results returned: {search_data['count']}")
        assert search_data["count"] > 0, "Error: Memory search API returned 0 results!"

    # Also check Live HTTP if server is running
    try:
        async with httpx.AsyncClient(timeout=1.0) as live_client:
            live_resp = await live_client.get(f"{API_BASE_URL}/memory/equipment_id:TRB-1105")
            if live_resp.status_code == 200:
                print(f" -> Live HTTP :8000 server also verified: 200 OK")
    except Exception:
        pass

    print("\n=====================================================================")
    print("     ALL PHASE 10 LONG-TERM MEMORY EVOLUTION TESTS PASSED!          ")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(run_memory_evolution_test())
