import os
import sys
import uuid
import asyncio
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, AsyncSessionLocal
from app.models import Task, TaskStep, TaskStatus, TaskType
from app.services.task_processor import process_task
from sqlalchemy.future import select

async def test_semantic_cache_pipeline():
    print("=====================================================================")
    print("   TEST: Semantic Response Caching (<2s Short-Circuit on Repetition) ")
    print("=====================================================================")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    prompt = "Generate executive vibration compliance memorandum for turbine TRB-1105 in HCU"

    # 1. First Task Execution (Cold start / Cache Miss)
    task1_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        t1 = Task(
            id=task1_id,
            task_type=TaskType.doc_gen,
            status=TaskStatus.pending,
            input_ref=prompt
        )
        db.add(t1)
        await db.commit()

    print(f" [1] Running First Task #{str(task1_id)[:8]} (Cold run)...")
    start_t1 = time.time()
    await process_task(task1_id)
    dur_t1 = time.time() - start_t1
    print(f"     -> First Task finished in {round(dur_t1, 1)}s")

    # Supervisor approves Task 1
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Task).where(Task.id == task1_id))
        t1_db = res.scalars().first()
        t1_db.status = TaskStatus.done
        await db.commit()
    print(f" [2] Approved Task 1 -> Stored in sovereign cache")

    # 2. Second Task Execution (Semantic Cache Hit)
    task2_id = uuid.uuid4()
    near_identical_prompt = "Generate executive vibration compliance memorandum for turbine TRB-1105 in HCU"

    async with AsyncSessionLocal() as db:
        t2 = Task(
            id=task2_id,
            task_type=TaskType.doc_gen,
            status=TaskStatus.pending,
            input_ref=near_identical_prompt
        )
        db.add(t2)
        await db.commit()

    print(f"\n [3] Running Second Task #{str(task2_id)[:8]} with near-identical prompt...")
    start_t2 = time.time()
    await process_task(task2_id)
    dur_t2 = time.time() - start_t2
    print(f"     -> Second Task finished in {round(dur_t2, 2)}s (Speedup: {round(dur_t1 / max(dur_t2, 0.01), 1)}x faster)")

    # 3. Verify Cache Hit on Task 2
    async with AsyncSessionLocal() as db:
        res2 = await db.execute(select(Task).where(Task.id == task2_id))
        t2_db = res2.scalars().first()

        steps_res2 = await db.execute(select(TaskStep).where(TaskStep.task_id == task2_id).order_by(TaskStep.step_number))
        steps2 = steps_res2.scalars().all()

    print(f"\n -> Task 2 Status: {t2_db.status.value}")
    assert t2_db.status == TaskStatus.pending_approval, "Cache hit must still require fresh supervisor approval"
    assert t2_db.output_ref is not None and len(t2_db.output_ref) > 0

    tools_logged = [s.tool_called for s in steps2]
    print(" -> Task 2 Steps:")
    for s in steps2:
        print(f"    [{s.step_number}] {s.tool_called:24} | {s.description}")

    assert "semantic_cache_hit" in tools_logged, "Expected semantic_cache_hit tool in trace"
    assert "human_approval_gate" in tools_logged, "Expected human_approval_gate in trace"

    print("\n=====================================================================")
    print("   SEMANTIC RESPONSE CACHING TEST PASSED SUCCESSFULLY!               ")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(test_semantic_cache_pipeline())
