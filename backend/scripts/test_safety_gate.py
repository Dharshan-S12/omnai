import os
import sys
import json
import asyncio
import httpx
from uuid import UUID

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def run_safety_gate_test():
    print("=====================================================================")
    print("      SAFETY & QUALITY GATE + HUMAN APPROVAL TEST (PHASE 11)        ")
    print("=====================================================================\n")

    import uuid
    from app.database import engine, Base, AsyncSessionLocal
    from app.models import Task, TaskStep, TaskStatus, TaskType
    from app.agent.loop import run_agent
    from app.main import app
    from httpx import ASGITransport
    from sqlalchemy.future import select

    # 0. Initialize DB schema
    print("[0] Ensuring Database Tables & Columns...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(" -> Database initialized.\n")

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # ----------------------------------------------------
        # TEST 1: DocGen Task -> Corrective Grading -> Critique -> Pending Approval
        # ----------------------------------------------------
        task1_id = uuid.uuid4()
        print(f"[1] Creating DocGen Task (ID: {task1_id})...")
        prompt1 = "Generate a formal vibration compliance memo for Equipment TRB-1105 adhering to SOP-MNT-042 inspection rules"

        async with AsyncSessionLocal() as db:
            t1 = Task(
                id=task1_id,
                task_type=TaskType.doc_gen,
                input_ref=prompt1,
                status=TaskStatus.pending
            )
            db.add(t1)
            await db.commit()

        print("[2] Running Sovereign Agent Loop for Task #1...")
        await run_agent(task_id=task1_id, task_type="doc_gen", input_text=prompt1)

        # Inspect Task Status & Steps
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Task).where(Task.id == task1_id))
            task1 = res.scalars().first()
            assert task1 is not None

            steps_res = await db.execute(
                select(TaskStep).where(TaskStep.task_id == task1_id).order_by(TaskStep.step_number)
            )
            steps1 = steps_res.scalars().all()

        print(f"\n[3] Verifying Safety & Quality Steps for Task #1:")
        print(f" -> Task Status: {task1.status.value} (Expected: 'pending_approval')")
        print(f" -> Confidence Score: {task1.confidence_score}%")
        assert task1.status == TaskStatus.pending_approval, f"Error: Status is {task1.status}, expected pending_approval!"
        assert task1.confidence_score is not None and 0.0 <= task1.confidence_score <= 100.0, "Error: Invalid confidence score!"

        tools_called = [s.tool_called for s in steps1 if s.tool_called]
        print(f" -> Tools Called in Timeline: {tools_called}")

        assert "human_approval_gate" in tools_called, "Error: Missing human_approval_gate step!"
        assert (
            "verifier_safety_grounding" in tools_called
            or "semantic_cache_hit" in tools_called
            or "rule_engine_check" in tools_called
        ), "Error: Missing safety verification or semantic cache step!"

        for s in steps1:
            if s.tool_called in ["rule_engine_check", "verifier_safety_grounding", "semantic_cache_hit", "human_approval_gate"]:
                print(f"    * {s.tool_called}: {s.description}")

        # ----------------------------------------------------
        # TEST 2: Attempt Output Download before Approval -> Expect 403
        # ----------------------------------------------------
        print(f"\n[4] Testing Download Lock (GET /tasks/{task1_id}/output/docx)...")
        docx_res = await client.get(f"/tasks/{task1_id}/output/docx")
        print(f" -> Status Code: {docx_res.status_code} (Expected: 403 Forbidden)")
        assert docx_res.status_code == 403, "Error: Download was not locked for pending_approval task!"

        txt_res = await client.get(f"/tasks/{task1_id}/output")
        print(f" -> Text Output Status Code: {txt_res.status_code} (Expected: 403 Forbidden)")
        assert txt_res.status_code == 403, "Error: Text output was not locked!"

        # ----------------------------------------------------
        # TEST 2B: Operator Role attempts approval -> Expect 403 Forbidden
        # ----------------------------------------------------
        print(f"\n[4B] Testing Operator Role Gate on Approval endpoint...")
        op_res = await client.post(
            f"/tasks/{task1_id}/approve",
            json={"approved": True, "reviewer_name": "Operator Joe"},
            headers={"X-User-Role": "operator"}
        )
        print(f" -> Operator Approval Status: {op_res.status_code} (Expected: 403 Forbidden)")
        assert op_res.status_code == 403, "Error: Operator was not blocked from approving!"

        # ----------------------------------------------------
        # TEST 3: Supervisor Approves Document -> Status becomes "done", Download unlocked
        # ----------------------------------------------------
        print(f"\n[5] Calling POST /tasks/{task1_id}/approve as supervisor (approved=True)...")
        approve_payload = {
            "approved": True,
            "reviewer_name": "Chief Reliability Engineer",
            "reviewer_notes": "SOP-MNT-042 guidelines verified. Approved for release."
        }
        appr_res = await client.post(
            f"/tasks/{task1_id}/approve",
            json=approve_payload,
            headers={"X-User-Role": "supervisor"}
        )
        print(f" -> Status Code: {appr_res.status_code}")
        assert appr_res.status_code == 200, f"Error approving task: {appr_res.text}"
        appr_data = appr_res.json()
        print(f" -> Updated Task Status: {appr_data['status']} (Expected: 'done')")
        assert appr_data["status"] == "done", "Error: Task status did not update to done!"

        # Check unlocked download
        print(f"\n[6] Verifying Unlocked Download (GET /tasks/{task1_id}/output/docx)...")
        unlocked_docx = await client.get(f"/tasks/{task1_id}/output/docx")
        print(f" -> Unlocked Download Status Code: {unlocked_docx.status_code} (Expected: 200 OK)")
        assert unlocked_docx.status_code == 200, "Error: Download did not unlock after approval!"

        # ----------------------------------------------------
        # TEST 4: Rejection Flow for another task
        # ----------------------------------------------------
        task2_id = uuid.uuid4()
        print(f"\n[7] Creating and Rejecting Task #2 (ID: {task2_id})...")
        prompt2 = "Draft a procurement request for replacement turbine seals"

        async with AsyncSessionLocal() as db:
            t2 = Task(
                id=task2_id,
                task_type=TaskType.doc_gen,
                input_ref=prompt2,
                status=TaskStatus.pending
            )
            db.add(t2)
            await db.commit()

        await run_agent(task_id=task2_id, task_type="doc_gen", input_text=prompt2)

        reject_payload = {
            "approved": False,
            "reviewer_name": "Senior Plant Auditor",
            "reviewer_notes": "Procurement exceeds threshold limit without pre-authorization."
        }
        rej_res = await client.post(
            f"/tasks/{task2_id}/approve",
            json=reject_payload,
            headers={"X-User-Role": "supervisor"}
        )
        assert rej_res.status_code == 200
        rej_data = rej_res.json()
        print(f" -> Rejection Decision Status: {rej_data['status']} (Expected: 'rejected')")
        assert rej_data["status"] == "rejected", "Error: Task status did not update to rejected!"

        # Check rejected download remains 403
        rej_docx = await client.get(f"/tasks/{task2_id}/output/docx")
        print(f" -> Rejected Task Download Status: {rej_docx.status_code} (Expected: 403 Forbidden)")
        assert rej_docx.status_code == 403, "Error: Rejected task output should remain locked!"

    print("\n=====================================================================")
    print("    ALL PHASE 11 SAFETY, QUALITY & APPROVAL GATE TESTS PASSED!       ")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(run_safety_gate_test())
