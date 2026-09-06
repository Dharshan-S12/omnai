import os
import re
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID

from app.models import Task, TaskStep, TaskStatus
from app.models.ollama_client import generate_text
from app.router.model_router import route_model
from app.docgen import generate_docx
from app.graph.ingest import record_equipment_event
from app.memory import ingest_memory

STORAGE_DIR = "./storage"
DISSENT_LOG_PATH = os.path.join(STORAGE_DIR, "dissent_records.jsonl")

async def log_step(
    db,
    task_id: UUID,
    step_number: int,
    description: str,
    tool_called: Optional[str] = None,
    tool_result: Optional[dict] = None
) -> TaskStep:
    step = TaskStep(
        id=uuid.uuid4(),
        task_id=task_id,
        step_number=step_number,
        description=description,
        tool_called=tool_called,
        tool_result=tool_result,
        created_at=datetime.now(timezone.utc)
    )
    db.add(step)
    await db.commit()
    return step

def log_ensemble_dissent_record(
    task_id: UUID,
    individual_runs: List[Dict[str, Any]],
    majority_verdict: str,
    trigger_reason: str
):
    """Persists detailed ensemble split votes to an append-only dissent ledger for audit."""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    dissent_entry = {
        "id": str(uuid.uuid4()),
        "task_id": str(task_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "majority_verdict": majority_verdict,
        "trigger_reason": trigger_reason,
        "runs": individual_runs
    }
    try:
        with open(DISSENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(dissent_entry) + "\n")
    except Exception as e:
        print(f"[Dissent Log Warning] Could not persist dissent record: {e}")

async def run_multi_agent_docgen_pipeline(
    db,
    task: Task,
    step_count: int,
    input_text: str,
    source_context: str,
    kept_chunks: List[Dict[str, Any]],
    total_retrieved_chunks: int,
    total_discarded_chunks: int,
    kept_chunk_distances: List[float]
) -> Tuple[str, float, int]:
    """
    Hardened Sequential 5-Agent Specialist Pipeline for doc_gen tasks:
    1. Extractor Agent (agent_extractor) -> Normalized facts
    2. Deterministic Rule Engine (rule_engine_check) -> Exact mathematical threshold computation (Authoritative Ground Truth)
    3. Compliance Agent / Diverse Ensemble (agent_compliance / compliance_ensemble) -> 3 distinct model configurations
    4. Drafting Agent (agent_drafter) -> Formal Executive Memorandum & .docx generation
    5. Verifier Agent (agent_verifier) -> Rule-based contradiction detection & explainable confidence breakdown
    """
    from app.rules.rule_engine import evaluate_rules

    # =========================================================================
    # STAGE 1: Extractor Agent (tool_called="agent_extractor")
    # =========================================================================
    try:
        step_count += 1
        extractor_decision = await route_model(task_type="text_gen", prompt=input_text, category_hint="fast_inference")

        extractor_system = (
            "You are the Extractor Agent in an industrial compliance pipeline.\n"
            "Extract, normalize, and consolidate all key technical parameters, equipment IDs, "
            "vibration RMS, temperatures, pressures, dates, and plant units from context.\n"
            "Output strictly a JSON object with keys: 'equipment_id', 'equipment_name', 'unit', "
            "'inspection_date', 'measurements' (dictionary), 'observed_condition', 'objective'."
        )

        extractor_prompt = (
            f"User Goal:\n{input_text}\n\n"
            f"Source Context & Inspection Records:\n{source_context or 'Direct instruction.'}\n\n"
            f"Extract structured facts as valid JSON:"
        )

        extractor_raw = await generate_text(
            prompt=extractor_prompt,
            system=extractor_system,
            model=extractor_decision.model_name,
            timeout_seconds=extractor_decision.timeout_seconds
        )

        extracted_facts = {}
        try:
            cleaned_json = extractor_raw.strip()
            if cleaned_json.startswith("```"):
                cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
                cleaned_json = re.sub(r"\s*```$", "", cleaned_json).strip()
            extracted_facts = json.loads(cleaned_json)
        except Exception:
            extracted_facts = {
                "equipment_id": "TRB-1105" if "TRB-1105" in input_text or "TRB-1105" in source_context else "Equipment",
                "unit": "HCU",
                "raw_text": extractor_raw[:300]
            }

        eq_id_display = extracted_facts.get("equipment_id") or "Equipment"
        await log_step(
            db=db,
            task_id=task.id,
            step_number=step_count,
            description=f"Stage 1 [Extractor Agent]: Consolidated parameters for {eq_id_display} (Status: SUCCESS)",
            tool_called="agent_extractor",
            tool_result={
                "stage": 1,
                "stage_status": "success",
                "agent": "Extractor Agent",
                "extracted_facts": extracted_facts,
                "model": extractor_decision.model_name
            }
        )
    except Exception as e:
        step_count += 1
        await log_step(
            db=db, task_id=task.id, step_number=step_count,
            description=f"Stage 1 [Extractor Agent] FAILED: {str(e)}",
            tool_called="agent_extractor",
            tool_result={"stage": 1, "stage_status": "failed", "error": str(e)}
        )
        task.status = TaskStatus.failed
        task.output_ref = f"Pipeline halted at Stage 1 (Extractor Agent): {str(e)}"
        await db.commit()
        raise RuntimeError(f"DocGen Stage 1 Failed: {e}")

    # =========================================================================
    # STAGE 2: Deterministic Rule Engine (tool_called="rule_engine_check")
    # Authoritative Numerical Ground Truth — ZERO LLM Variance
    # =========================================================================
    try:
        step_count += 1
        sop_candidate = None
        for chunk in kept_chunks:
            src = str(chunk.get("source", "")).upper()
            if "SOP-" in src or "ISO-" in src:
                match = re.search(r"(?:SOP|ISO)-[A-Z0-9]+-\d+", src)
                if match:
                    sop_candidate = match.group(0)
                    break

        rule_eval = evaluate_rules(extracted_fields=extracted_facts, sop_reference=sop_candidate)

        rule_ground_truth_context = ""
        if rule_eval.get("evaluated"):
            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=(
                    f"Stage 2 [Deterministic Rule Engine]: Evaluated {rule_eval['total_rules_evaluated']} threshold rule(s) -> "
                    f"Authoritative Verdict: '{rule_eval['overall_verdict']}' (Config v{rule_eval.get('config_version', '1.0')}) (Status: SUCCESS)"
                ),
                tool_called="rule_engine_check",
                tool_result={
                    "stage": 2,
                    "stage_status": "success",
                    "authoritative": True,
                    **rule_eval
                }
            )
            rule_ground_truth_context = (
                "### AUTHORITATIVE DETERMINISTIC RULE ENGINE GROUND TRUTH:\n"
                f"The following threshold comparisons are mathematically exact ground truth (Config v{rule_eval.get('config_version', '1.0')}, Checksum: {rule_eval.get('config_hash', '')[:8]}):\n"
                f"- Authoritative Overall Verdict: {rule_eval['overall_verdict']}\n"
                f"- Borderline Proximity (<10% to limit): {'YES' if rule_eval.get('is_borderline') else 'NO'}\n"
                f"- Evaluated Parameters:\n"
            )
            for r in rule_eval.get("rule_results", []):
                rule_ground_truth_context += (
                    f"  * {r['field_label']}: Observed {r['actual_value']} | Limit {r['operator']} {r['threshold']} | "
                    f"Status: {'PASS' if r['passed'] else 'FAIL'} | Classification: {r['zone_label']} | Standard: {r['sop_reference']}\n"
                )
            if rule_eval.get("sanitization_warnings"):
                rule_ground_truth_context += f"- Input Sanitization Alerts: {'; '.join(rule_eval['sanitization_warnings'])}\n"
            rule_ground_truth_context += (
                "\nCRITICAL SAFETY RULE: You are an advisory narrative agent. You CANNOT override or dispute these authoritative facts.\n\n"
            )
        else:
            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Stage 2 [Deterministic Rule Engine]: Skipped ({rule_eval.get('reason', 'no numerical rules found')}) (Status: SUCCESS)",
                tool_called="rule_engine_check",
                tool_result={"stage": 2, "stage_status": "success", **rule_eval}
            )
    except Exception as e:
        step_count += 1
        await log_step(
            db=db, task_id=task.id, step_number=step_count,
            description=f"Stage 2 [Rule Engine] FAILED: {str(e)}",
            tool_called="rule_engine_check",
            tool_result={"stage": 2, "stage_status": "failed", "error": str(e)}
        )
        task.status = TaskStatus.failed
        task.output_ref = f"Pipeline halted at Stage 2 (Rule Engine): {str(e)}"
        await db.commit()
        raise RuntimeError(f"DocGen Stage 2 Failed: {e}")

    # =========================================================================
    # STAGE 3: Compliance Agent & Diverse 3-Model Ensemble (tool_called="agent_compliance" / "compliance_ensemble")
    # =========================================================================
    try:
        step_count += 1
        sop_context_text = ""
        for idx, chunk in enumerate(kept_chunks):
            sop_context_text += f"[SOP Excerpt {idx+1} (Source: {chunk.get('source', 'SOP')})]:\n{chunk.get('text', '')}\n\n"
        if not sop_context_text:
            sop_context_text = "Standard ISO 10816-3 and MRPL plant safety guidelines."

        compliance_system = (
            "You are the Compliance Agent in an industrial advisory safety pipeline.\n"
            "Evaluate extracted facts against SOP reference rules and the authoritative deterministic rule engine truth.\n"
            "Your role is advisory. You MUST align your verdict with deterministic ground truth if rules were evaluated.\n"
            "Output strictly a JSON object: {'verdict': 'COMPLIANT'|'NON_COMPLIANT'|'NEEDS_REVIEW', "
            "'summary_reason': '...', 'threshold_evaluations': [], 'mandatory_actions': '...'}"
        )

        compliance_prompt = (
            f"{rule_ground_truth_context}"
            f"Technical Facts:\n{json.dumps(extracted_facts, indent=2)}\n\n"
            f"SOP Standards:\n{sop_context_text}\n\n"
            f"Evaluate compliance and produce structured verdict JSON:"
        )

        should_run_ensemble = (not rule_eval.get("evaluated")) or (rule_eval.get("is_borderline") is True)
        ensemble_disagreement = False
        ensemble_penalty = 0.0
        compliance_verdict = {}

        if should_run_ensemble:
            # 3 DISTINCT model configurations (different models / temperatures to avoid correlated errors)
            ensemble_configs = [
                {"model": "qwen2.5:7b-instruct", "temperature": 0.0, "desc": "Config A (7B @ temp 0.0 deterministic)"},
                {"model": "qwen2.5:7b-instruct", "temperature": 0.3, "desc": "Config B (7B @ temp 0.3 slight stochasticity)"},
                {"model": "qwen2.5:3b", "temperature": 0.7, "desc": "Config C (3B @ temp 0.7 high diversity check)"}
            ]

            ensemble_runs = []
            verdicts = []

            for cfg in ensemble_configs:
                try:
                    raw_run = await generate_text(
                        prompt=compliance_prompt,
                        system=compliance_system,
                        model=cfg["model"],
                        temperature=cfg["temperature"],
                        timeout_seconds=120
                    )
                except Exception:
                    # Fallback to 3B if 7B is unavailable
                    raw_run = await generate_text(
                        prompt=compliance_prompt,
                        system=compliance_system,
                        model="qwen2.5:3b",
                        temperature=cfg["temperature"],
                        timeout_seconds=90
                    )

                parsed_run = {}
                try:
                    c_json = raw_run.strip()
                    if c_json.startswith("```"):
                        c_json = re.sub(r"^```(?:json)?\s*", "", c_json)
                        c_json = re.sub(r"\s*```$", "", c_json).strip()
                    parsed_run = json.loads(c_json)
                except Exception:
                    v_str = "NON_COMPLIANT" if ("non-compliant" in raw_run.lower() or "non_compliant" in raw_run.lower()) else "COMPLIANT"
                    parsed_run = {"verdict": v_str, "summary_reason": raw_run[:200], "threshold_evaluations": []}

                v_val = str(parsed_run.get("verdict", "COMPLIANT")).upper().strip()
                verdicts.append(v_val)
                ensemble_runs.append({
                    "config": cfg["desc"],
                    "model": cfg["model"],
                    "temperature": cfg["temperature"],
                    "verdict": v_val,
                    "summary_reason": parsed_run.get("summary_reason", ""),
                    "raw_output": raw_run[:300],
                    "full_data": parsed_run
                })

            from collections import Counter
            vote_counts = Counter(verdicts)
            majority_verdict, count = vote_counts.most_common(1)[0]
            is_unanimous = (count == len(ensemble_configs))

            if not is_unanimous:
                ensemble_disagreement = True
                ensemble_penalty = 20.0
                # Log dissent record for offline calibration audit
                log_ensemble_dissent_record(
                    task_id=task.id,
                    individual_runs=ensemble_runs,
                    majority_verdict=majority_verdict,
                    trigger_reason="Borderline measurement" if rule_eval.get("is_borderline") else "Unruled document type"
                )

            rep_run = next((r for r in ensemble_runs if r["verdict"] == majority_verdict), ensemble_runs[0])
            compliance_verdict = rep_run["full_data"]
            compliance_verdict["verdict"] = majority_verdict

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=(
                    f"Stage 3 [Diverse Ensemble (3 Models)]: "
                    f"{'Unanimous consensus (3/3)' if is_unanimous else f'Ensemble Disagreement ({count}/3 majority) — DISSENT LOGGED'} -> '{majority_verdict}' (Status: SUCCESS)"
                ),
                tool_called="compliance_ensemble",
                tool_result={
                    "stage": 3,
                    "stage_status": "success",
                    "agent": "Compliance Agent (Diverse 3-Model Ensemble)",
                    "ensemble_configs": [c["desc"] for c in ensemble_configs],
                    "individual_runs": ensemble_runs,
                    "majority_verdict": majority_verdict,
                    "is_unanimous": is_unanimous,
                    "ensemble_disagreement": ensemble_disagreement,
                    "disagreement_penalty": ensemble_penalty,
                    "summary_reason": compliance_verdict.get("summary_reason", "")
                }
            )
        else:
            compliance_decision = await route_model(task_type="text_gen", prompt=input_text, category_hint="reasoning")
            compliance_raw = await generate_text(
                prompt=compliance_prompt,
                system=compliance_system,
                model=compliance_decision.model_name,
                timeout_seconds=compliance_decision.timeout_seconds,
                temperature=0.0
            )
            try:
                cleaned_cjson = compliance_raw.strip()
                if cleaned_cjson.startswith("```"):
                    cleaned_cjson = re.sub(r"^```(?:json)?\s*", "", cleaned_cjson)
                    cleaned_cjson = re.sub(r"\s*```$", "", cleaned_cjson).strip()
                compliance_verdict = json.loads(cleaned_cjson)
            except Exception:
                verdict_str = rule_eval.get("overall_verdict") or ("NON_COMPLIANT" if "non-compliant" in compliance_raw.lower() else "COMPLIANT")
                compliance_verdict = {
                    "verdict": verdict_str,
                    "summary_reason": compliance_raw[:250],
                    "threshold_evaluations": rule_eval.get("rule_results", [])
                }

            verdict_label = compliance_verdict.get("verdict", rule_eval.get("overall_verdict", "COMPLIANT"))
            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Stage 3 [Compliance Agent]: Rendered advisory verdict '{verdict_label}' (Status: SUCCESS)",
                tool_called="agent_compliance",
                tool_result={
                    "stage": 3,
                    "stage_status": "success",
                    "agent": "Compliance Agent",
                    "verdict": verdict_label,
                    "summary_reason": compliance_verdict.get("summary_reason", ""),
                    "model": compliance_decision.model_name
                }
            )

        # STRICT SAFETY OVERRIDE: If rule engine evaluated FAIL/NON_COMPLIANT, LLM can NEVER set verdict to COMPLIANT
        if rule_eval.get("evaluated") and rule_eval.get("overall_verdict") == "NON_COMPLIANT":
            compliance_verdict["verdict"] = "NON_COMPLIANT"
            compliance_verdict["authoritative_override"] = True

    except Exception as e:
        step_count += 1
        await log_step(
            db=db, task_id=task.id, step_number=step_count,
            description=f"Stage 3 [Compliance Agent] FAILED: {str(e)}",
            tool_called="agent_compliance",
            tool_result={"stage": 3, "stage_status": "failed", "error": str(e)}
        )
        task.status = TaskStatus.failed
        task.output_ref = f"Pipeline halted at Stage 3 (Compliance Agent): {str(e)}"
        await db.commit()
        raise RuntimeError(f"DocGen Stage 3 Failed: {e}")

    verdict_label = compliance_verdict.get("verdict", "COMPLIANT")

    # =========================================================================
    # STAGE 4: Drafting Agent (tool_called="agent_drafter")
    # =========================================================================
    try:
        step_count += 1
        drafter_decision = await route_model(task_type="doc_gen", prompt=input_text, category_hint="general")

        drafting_system = (
            "You are the Drafting Agent in an executive sovereign document workbench.\n"
            "Draft the complete, authoritative compliance memorandum formatted for executive review.\n"
            "You MUST adhere strictly to the deterministic rule engine ground truth and Compliance Agent verdict.\n"
            "Structure:\n"
            "# Executive Compliance Memorandum\n"
            "## 1. Equipment & Inspection Identification\n"
            "## 2. Technical Findings & Measurement Ledger\n"
            "## 3. SOP Compliance Evaluation & Citations\n"
            "## 4. Operational Verdict & Required Corrective Actions\n"
        )

        drafting_prompt = (
            f"User Goal:\n{input_text}\n\n"
            f"{rule_ground_truth_context}"
            f"Technical Facts:\n{json.dumps(extracted_facts, indent=2)}\n\n"
            f"Compliance Verdict:\n{json.dumps(compliance_verdict, indent=2)}\n\n"
            f"SOP Standards:\n{sop_context_text}\n\n"
            f"Draft the formal compliance memorandum:"
        )

        final_document_text = await generate_text(
            prompt=drafting_prompt,
            system=drafting_system,
            model=drafter_decision.model_name,
            timeout_seconds=drafter_decision.timeout_seconds
        )

        task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
        os.makedirs(task_storage_dir, exist_ok=True)
        output_file_path = os.path.join(task_storage_dir, "output.txt")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(final_document_text)

        doc_title_words = input_text.split()[:8]
        doc_title = " ".join(doc_title_words).strip(".:,; ") or f"Compliance Memo — {eq_id_display}"
        docx_file_path = os.path.join(task_storage_dir, "output.docx")
        generate_docx(title=doc_title, content=final_document_text, output_path=docx_file_path)

        if not os.path.exists(docx_file_path) or os.path.getsize(docx_file_path) == 0:
            raise IOError("Generated .docx file is missing or empty.")

        await log_step(
            db=db,
            task_id=task.id,
            step_number=step_count,
            description="Stage 4 [Drafting Agent]: Formatted executive compliance memorandum (.docx) (Status: SUCCESS)",
            tool_called="agent_drafter",
            tool_result={
                "stage": 4,
                "stage_status": "success",
                "agent": "Drafting Agent",
                "document_title": doc_title,
                "file_path": docx_file_path,
                "output_length": len(final_document_text),
                "file_size_bytes": os.path.getsize(docx_file_path),
                "model": drafter_decision.model_name
            }
        )
    except Exception as e:
        step_count += 1
        await log_step(
            db=db, task_id=task.id, step_number=step_count,
            description=f"Stage 4 [Drafting Agent] FAILED: {str(e)}",
            tool_called="agent_drafter",
            tool_result={"stage": 4, "stage_status": "failed", "error": str(e)}
        )
        task.status = TaskStatus.failed
        task.output_ref = f"Pipeline halted at Stage 4 (Drafting Agent): {str(e)}"
        await db.commit()
        raise RuntimeError(f"DocGen Stage 4 Failed: {e}")

    # =========================================================================
    # STAGE 5: Verifier Agent (tool_called="agent_verifier")
    # Rule-Based Contradiction Detection & Explainable Grounding Confidence Breakdown
    # =========================================================================
    try:
        step_count += 1
        deductions: List[Dict[str, Any]] = []
        claims_checked: List[Dict[str, Any]] = []
        hard_contradiction = False
        rule_contradiction_details = []

        # 1. Deterministic Rule-Based Contradiction Check (Regex against drafted text)
        if rule_eval.get("evaluated") and rule_eval.get("rule_results"):
            for r in rule_eval["rule_results"]:
                actual_zone = r.get("zone_label", "")
                actual_val = str(r.get("actual_value", ""))
                rule_pass = r.get("passed", True)

                # Check if draft claims Zone A when rule is Zone C/D
                if not rule_pass and re.search(r"\bZone\s*A\b", final_document_text, re.IGNORECASE):
                    hard_contradiction = True
                    rule_contradiction_details.append(f"Draft incorrectly claims Zone A while deterministic rule computed {actual_zone}")
                if not rule_pass and re.search(r"\b(fully compliant|within normal limits|passed inspection)\b", final_document_text, re.IGNORECASE) and not re.search(r"\bnon-compliant\b", final_document_text, re.IGNORECASE):
                    hard_contradiction = True
                    rule_contradiction_details.append(f"Draft claims compliant while parameter '{r['field']}' failed limit ({actual_val} vs {r['threshold']})")

                claims_checked.append({
                    "parameter": r["field"],
                    "computed_value": actual_val,
                    "expected_status": "PASS" if rule_pass else "FAIL",
                    "expected_zone": actual_zone,
                    "verified_in_text": actual_val in final_document_text
                })

        # 2. LLM Advisory Prose Verification
        verifier_decision = await route_model(task_type="text_gen", prompt=input_text, category_hint="reasoning")
        verifier_system = (
            "You are the Verifier Agent in an industrial compliance pipeline.\n"
            "Cross-check the drafted text against the authoritative rule engine facts and compliance narrative.\n"
            "Check for prose contradictions, missing actions, or ungrounded claims.\n"
            "Respond with JSON: {'agreement': true/false, 'verification_summary': '...', 'discrepancies': []}."
        )

        verifier_prompt = (
            f"{rule_ground_truth_context}"
            f"Compliance Verdict Reference:\n{json.dumps(compliance_verdict, indent=2)}\n\n"
            f"Drafted Document:\n{final_document_text}\n\n"
            f"Verify agreement:"
        )

        verifier_raw = await generate_text(
            prompt=verifier_prompt,
            system=verifier_system,
            model=verifier_decision.model_name,
            timeout_seconds=verifier_decision.timeout_seconds
        )

        verifier_data = {}
        try:
            cleaned_vjson = verifier_raw.strip()
            if cleaned_vjson.startswith("```"):
                cleaned_vjson = re.sub(r"^```(?:json)?\s*", "", cleaned_vjson)
                cleaned_vjson = re.sub(r"\s*```$", "", cleaned_vjson).strip()
            verifier_data = json.loads(cleaned_vjson)
        except Exception:
            agreement = "agreement" in verifier_raw.lower() and "false" not in verifier_raw.lower()
            verifier_data = {"agreement": agreement, "verification_summary": verifier_raw[:200], "discrepancies": []}

        llm_agrees = verifier_data.get("agreement") is True
        discrepancies = verifier_data.get("discrepancies", []) + rule_contradiction_details

        # 3. Calculate Explainable Grounding Confidence Breakdown
        if hard_contradiction:
            confidence_score = 20.0
            deductions.append({
                "factor": "hard_contradiction_against_deterministic_engine",
                "penalty": 80.0,
                "reason": f"Hard safety contradiction detected: {'; '.join(rule_contradiction_details)}"
            })
        else:
            if not llm_agrees or rule_contradiction_details:
                penalty_ver = 40.0
                deductions.append({
                    "factor": "verifier_discrepancy",
                    "penalty": penalty_ver,
                    "reason": f"Discrepancies identified during cross-verification ({len(discrepancies)} issues)"
                })
            else:
                penalty_ver = 0.0

            if ensemble_disagreement:
                deductions.append({
                    "factor": "ensemble_disagreement",
                    "penalty": ensemble_penalty,
                    "reason": "Diverse 3-model ensemble exhibited split vote (Dissent record logged for audit)"
                })

            if kept_chunk_distances:
                avg_dist = sum(kept_chunk_distances) / len(kept_chunk_distances)
                p_dist = round(min(20.0, avg_dist * 25.0), 1)
                if p_dist > 5.0:
                    deductions.append({
                        "factor": "vector_retrieval_distance",
                        "penalty": p_dist,
                        "reason": f"Average semantic distance of SOP excerpts ({avg_dist:.3f})"
                    })
            else:
                p_dist = 0.0

            if total_discarded_chunks > 0:
                deductions.append({
                    "factor": "irrelevant_chunks_discarded",
                    "penalty": 10.0,
                    "reason": f"Corrective RAG discarded {total_discarded_chunks} irrelevant context chunk(s)"
                })

            total_penalty = sum(d["penalty"] for d in deductions)
            raw_conf = max(10.0, min(99.0, 100.0 - total_penalty))
            confidence_score = round(raw_conf, 1)

        task.confidence_score = confidence_score

        is_overall_verified = (not hard_contradiction) and llm_agrees and (not ensemble_disagreement)

        step_desc = (
            f"Stage 5 [Verifier Agent]: "
            f"{'Complete agreement confirmed' if is_overall_verified else ('HARD CONTRADICTION FLAGGED' if hard_contradiction else 'Discrepancies flagged')} "
            f"(Confidence: {confidence_score}%) (Status: SUCCESS)"
        )

        await log_step(
            db=db,
            task_id=task.id,
            step_number=step_count,
            description=step_desc,
            tool_called="agent_verifier",
            tool_result={
                "stage": 5,
                "stage_status": "success",
                "agent": "Verifier Agent",
                "verified": is_overall_verified,
                "hard_contradiction": hard_contradiction,
                "confidence_score": confidence_score,
                "claims_checked": claims_checked,
                "deductions_breakdown": deductions,
                "discrepancies": discrepancies,
                "verification_summary": verifier_data.get("verification_summary", ""),
                "model": verifier_decision.model_name
            }
        )

    except Exception as e:
        step_count += 1
        await log_step(
            db=db, task_id=task.id, step_number=step_count,
            description=f"Stage 5 [Verifier Agent] FAILED: {str(e)}",
            tool_called="agent_verifier",
            tool_result={"stage": 5, "stage_status": "failed", "error": str(e)}
        )
        task.status = TaskStatus.failed
        task.output_ref = f"Pipeline halted at Stage 5 (Verifier Agent): {str(e)}"
        await db.commit()
        raise RuntimeError(f"DocGen Stage 5 Failed: {e}")

    # Ingest event to Equipment Knowledge Graph & Memory
    try:
        await record_equipment_event(
            task_id=task.id,
            structured_data={
                "equipment_id": extracted_facts.get("equipment_id") or eq_id_display,
                "equipment_name": extracted_facts.get("equipment_name"),
                "unit": extracted_facts.get("unit") or "HCU",
                "status": verdict_label,
                "compliance_verdict": compliance_verdict,
                "rule_engine_evaluation": rule_eval,
                "extracted_facts": extracted_facts,
                "findings": final_document_text[:500],
                "task_prompt": input_text,
                "confidence_score": confidence_score
            },
            event_type="approval_note"
        )
    except Exception as graph_err:
        print(f"Equipment graph recording notice in docgen: {graph_err}")

    try:
        # Tag safety_critical if non-compliant or violation
        is_safety_critical = (verdict_label == "NON_COMPLIANT") or (rule_eval.get("overall_verdict") == "NON_COMPLIANT")
        await ingest_memory(
            task_id=task.id,
            structured_output={
                "document_title": doc_title,
                "equipment_id": extracted_facts.get("equipment_id") or eq_id_display,
                "status": verdict_label,
                "safety_critical": is_safety_critical,
                "findings": final_document_text[:500],
                "task_prompt": input_text,
                "confidence_score": confidence_score
            },
            doc_type="doc_gen"
        )
    except Exception as mem_err:
        print(f"Memory ingestion notice in docgen: {mem_err}")

    return final_document_text, confidence_score, step_count
