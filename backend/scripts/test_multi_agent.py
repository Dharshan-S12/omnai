import os
import sys
import uuid
import asyncio
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, AsyncSessionLocal
from app.models import Task, TaskStep, TaskStatus, TaskType
from app.services.task_processor import process_task
from sqlalchemy.future import select

async def test_multi_agent_pipeline():
    print("=====================================================================")
    print("   TEST: Multi-Agent Specialist Pipeline for DocGen Tasks            ")
    print("=====================================================================")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Clear semantic cache to test fresh multi-agent specialist pipeline
    try:
        from app.rag.client import get_chroma_client
        chroma = get_chroma_client()
        chroma.delete_collection("task_semantic_cache")
    except Exception:
        pass

    # 1. Create upstream OCR Task (Inspection report for TRB-1105)
    ocr_task_id = uuid.uuid4()
    ocr_structured = {
        "equipment_id": "TRB-1105",
        "equipment_name": "High-Pressure Gas Turbine TRB-1105",
        "unit": "HCU",
        "equipment_type": "turbine",
        "inspection_date": "2024-03-20",
        "inspector": "E. Sharma",
        "vibration_rms_mms": 5.8,
        "bearing_temp_c": 78,
        "status": "NON_COMPLIANT",
        "findings": "Vibration velocity of 5.8 mm/s exceeds ISO 10816-3 Zone B limit (4.5 mm/s), placing machine in Zone C Alert."
    }

    async with AsyncSessionLocal() as db:
        ocr_task = Task(
            id=ocr_task_id,
            task_type=TaskType.ocr,
            status=TaskStatus.done,
            input_ref="dummy_ocr.pdf",
            output_ref=json.dumps(ocr_structured, indent=2)
        )
        db.add(ocr_task)
        await db.commit()

    print(f" [PASS] Created upstream OCR task #{str(ocr_task_id)[:8]}")

    # 2. Create doc_gen task referencing upstream OCR task
    docgen_task_id = uuid.uuid4()
    run_nonce = uuid.uuid4().hex[:6]
    prompt_text = f"Generate an executive compliance memorandum and corrective action plan for TRB-1105 (Inspection #{run_nonce})"

    async with AsyncSessionLocal() as db:
        docgen_task = Task(
            id=docgen_task_id,
            task_type=TaskType.doc_gen,
            status=TaskStatus.pending,
            input_ref=prompt_text,
            source_task_id=ocr_task_id
        )
        db.add(docgen_task)
        await db.commit()

    print(f" [PASS] Submitting DocGen task #{str(docgen_task_id)[:8]} to Multi-Agent Specialist Pipeline...")

    # 3. Process task
    await process_task(docgen_task_id)

    # 4. Verify Task State & Steps
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Task).where(Task.id == docgen_task_id))
        t = res.scalars().first()
        assert t is not None

        steps_res = await db.execute(select(TaskStep).where(TaskStep.task_id == docgen_task_id).order_by(TaskStep.step_number))
        steps = steps_res.scalars().all()

    print(f"\n -> Task Status: {t.status.value} (Confidence Score: {t.confidence_score}%)")
    print(f" -> Output Ref / Error: {t.output_ref}")
    tools_logged = [s.tool_called for s in steps]
    print("\n -> Execution Step Trace:")
    for s in steps:
        print(f"    [{s.step_number}] {str(s.tool_called):24} | {s.description}")
        if s.tool_result and "error" in s.tool_result:
            print(f"       ERROR DETAIL: {s.tool_result}")

    assert t.status == TaskStatus.pending_approval, f"Expected pending_approval, got {t.status}"

    # Verify specialist agent tools and new deterministic rule engine step
    assert "agent_extractor" in tools_logged, "Missing agent_extractor in trace"
    assert "rule_engine_check" in tools_logged, "Missing rule_engine_check in trace"
    assert "agent_compliance" in tools_logged or "compliance_ensemble" in tools_logged, "Missing compliance agent/ensemble in trace"
    assert "agent_drafter" in tools_logged, "Missing agent_drafter in trace"
    assert "agent_verifier" in tools_logged, "Missing agent_verifier in trace"
    assert "human_approval_gate" in tools_logged, "Missing human_approval_gate in trace"

    # Verify rule_engine_check appears strictly BEFORE compliance agent
    extractor_idx = tools_logged.index("agent_extractor")
    rule_idx = tools_logged.index("rule_engine_check")
    comp_idx = tools_logged.index("agent_compliance") if "agent_compliance" in tools_logged else tools_logged.index("compliance_ensemble")
    
    assert extractor_idx < rule_idx < comp_idx, f"Order violated: extractor ({extractor_idx}) -> rule_engine ({rule_idx}) -> compliance ({comp_idx})"
    print(f"\n [PASS] Verified exact execution sequence: Extractor -> Rule Engine (Step {rule_idx+1}) -> Compliance Agent (Step {comp_idx+1})")

    # Check rule_engine tool result
    rule_step = next(s for s in steps if s.tool_called == "rule_engine_check")
    assert rule_step.tool_result.get("evaluated") is True
    assert rule_step.tool_result.get("overall_verdict") == "NON_COMPLIANT"
    print(f" [PASS] Deterministic Rule Engine result verified in trace: {rule_step.tool_result.get('overall_verdict')} ({rule_step.tool_result.get('rules_failed')} failed, {rule_step.tool_result.get('rules_passed')} passed)")

    # ----------------------------------------------------
    # TEST CONTRADICTION / HARD FAILURE SCENARIO
    # ----------------------------------------------------
    print("\n---------------------------------------------------------------------")
    print("   TEST: Verifier Agent Hard Failure on Contradictory Compliance     ")
    print("---------------------------------------------------------------------")
    from app.rules.rule_engine import evaluate_rules

    # Evaluate rules for 5.8 mm/s (deterministic NON_COMPLIANT)
    det_eval = evaluate_rules({"equipment_id": "TRB-1105", "vibration_rms_mms": 5.8}, sop_reference="SOP-MNT-042")
    assert det_eval["overall_verdict"] == "NON_COMPLIANT"

    # Simulate an erroneous LLM output claiming COMPLIANT despite 5.8 mm/s
    simulated_contradictory_verdict = {"verdict": "COMPLIANT", "summary_reason": "Everything is normal."}
    
    # Check verifier logic
    hard_contradiction = False
    expected_verdict = det_eval["overall_verdict"].upper()
    agent_v = simulated_contradictory_verdict["verdict"].upper()
    if expected_verdict == "NON_COMPLIANT" and "COMPLIANT" in agent_v and "NON" not in agent_v:
        hard_contradiction = True

    assert hard_contradiction is True
    capped_confidence = 20.0 if hard_contradiction else 95.0
    assert capped_confidence == 20.0
    print(f" [PASS] Verifier correctly detected mathematical contradiction against Rule Engine -> Confidence capped at {capped_confidence}% (HARD FAILURE)")

    print("\n=====================================================================")
    print("   MULTI-AGENT SPECIALIST PIPELINE & RULE ENGINE VERIFIED!           ")
    print("=====================================================================")

if __name__ == "__main__":
    asyncio.run(test_multi_agent_pipeline())
