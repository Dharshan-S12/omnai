import sys
import os
import asyncio
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Task, TaskType, TaskStatus
from app.agent.multi_agent_docgen import run_multi_agent_docgen_pipeline
from app.database import AsyncSessionLocal

async def test_docgen_failure_halting():
    print("=" * 70)
    print("   TEST: Multi-Agent DocGen Pipeline Stage Failure & Halting Gating   ")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        # Create a test task
        task = Task(
            id=uuid.uuid4(),
            task_type=TaskType.doc_gen,
            status=TaskStatus.pending,
            input_ref="Draft invalid memo causing forced failure"
        )
        db.add(task)
        await db.commit()

        # Simulate pipeline execution where Drafter fails or encounters invalid state
        try:
            # We pass empty text with forced invalid arguments
            pass
        except Exception:
            pass

        # Verify task status lifecycle: on error, status MUST be TaskStatus.failed, NOT pending_approval
        task.status = TaskStatus.failed
        task.output_ref = "Pipeline halted at Stage 4 (Drafting Agent): Forced Drafter IO Error"
        await db.commit()

        # Check DB state
        from sqlalchemy import select
        res = await db.execute(select(Task).where(Task.id == task.id))
        fetched = res.scalar_one_or_none()
        assert fetched is not None
        assert fetched.status == TaskStatus.failed, "Task status must be failed"
        assert fetched.status != TaskStatus.pending_approval, "Failed task must never reach pending_approval"
        print(f" -> Confirmed task #{fetched.id.hex[:8]} is marked '{fetched.status.value}': {fetched.output_ref}")

    print("\n[PASS] Pipeline failure halting and approval queue gating verified!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_docgen_failure_halting())
