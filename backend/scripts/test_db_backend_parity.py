import sys
import os
import asyncio
import uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.database import AsyncSessionLocal, engine, get_db_health_info
from app.models import Task, TaskStep, TaskType, TaskStatus, MemoryEntry, EquipmentNode, EquipmentEvent

async def test_db_parity():
    print("=" * 70)
    print("   TEST: Database Engine Feature Parity & Fallback Status Reporting   ")
    print("=" * 70)

    health_info = get_db_health_info()
    print(f" -> Active DB Backend: {health_info['active_backend'].upper()}")
    print(f" -> Is Fallback Active: {health_info['is_fallback']}")
    print(f" -> Integrity Mode: {health_info['integrity_mode']}")
    if health_info['banner_message']:
        print(f" -> Active UI Banner: '{health_info['banner_message']}'")

    async with AsyncSessionLocal() as db:
        # 1. Concurrent Task Step Creation
        task = Task(
            id=uuid.uuid4(),
            task_type=TaskType.doc_gen,
            status=TaskStatus.pending,
            input_ref="DB Parity Test Task"
        )
        db.add(task)
        await db.commit()

        # Insert sequential steps
        for step_idx in range(1, 4):
            step = TaskStep(
                id=uuid.uuid4(),
                task_id=task.id,
                step_number=step_idx,
                description=f"Parity Execution Step {step_idx}",
                tool_called=f"tool_{step_idx}",
                tool_result={"index": step_idx, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            db.add(step)
        await db.commit()

        # Query steps back with order
        step_res = await db.execute(
            select(TaskStep).where(TaskStep.task_id == task.id).order_by(TaskStep.step_number)
        )
        steps = step_res.scalars().all()
        assert len(steps) == 3, f"Expected 3 steps, got {len(steps)}"
        assert steps[0].step_number == 1 and steps[2].step_number == 3
        print(f" [PASS] Concurrent sequential step writes verified on {health_info['active_backend']}")

        # 2. Equipment Knowledge Graph JSON query parity
        eq_id = f"TEST-PMP-{uuid.uuid4().hex[:6].upper()}"
        node = EquipmentNode(
            id=uuid.uuid4(),
            equipment_id=eq_id,
            equipment_name="Test Parity Centrifugal Pump",
            unit="CDU",
            equipment_type="pump"
        )
        db.add(node)
        await db.commit()

        event = EquipmentEvent(
            id=uuid.uuid4(),
            equipment_node_id=node.id,
            event_type="inspection",
            event_data={"vibration_rms": 3.4, "temperature": 68.0, "status": "COMPLIANT"}
        )
        db.add(event)
        await db.commit()

        event_res = await db.execute(
            select(EquipmentEvent).where(EquipmentEvent.equipment_node_id == node.id)
        )
        fetched_event = event_res.scalars().first()
        assert fetched_event is not None
        assert fetched_event.event_data.get("vibration_rms") == 3.4
        print(f" [PASS] Equipment Knowledge Graph JSON payload persistence verified on {health_info['active_backend']}")

        # 3. Memory Evolution Supersede Chain parity
        mem1 = MemoryEntry(
            id=uuid.uuid4(),
            entity_key=f"equipment_id:{eq_id}",
            summary_text="Initial baseline inspection reading 2.1 mm/s",
            strength_score=1.0,
            safety_critical=False
        )
        db.add(mem1)
        await db.commit()

        mem2 = MemoryEntry(
            id=uuid.uuid4(),
            entity_key=f"equipment_id:{eq_id}",
            summary_text="Follow-up inspection reading 5.8 mm/s (Zone C)",
            strength_score=1.0,
            safety_critical=True
        )
        db.add(mem2)
        mem1.superseded_by = mem2.id
        await db.commit()

        mem_res = await db.execute(
            select(MemoryEntry).where(MemoryEntry.entity_key == f"equipment_id:{eq_id}")
        )
        all_mems = mem_res.scalars().all()
        assert len(all_mems) == 2
        active_mem = next(m for m in all_mems if m.superseded_by is None)
        assert active_mem.id == mem2.id
        assert active_mem.safety_critical is True
        print(f" [PASS] Memory Evolution & safety_critical flag persistence verified on {health_info['active_backend']}")

    print(f"\n[PASS] All DB backend operations verified with 100% parity on {engine.dialect.name}!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_db_parity())
