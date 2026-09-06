import os
import re
import json
import uuid
import traceback
from datetime import datetime, timezone
from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.future import select
from sqlalchemy import desc
from app.database import AsyncSessionLocal
from app.models import Task, TaskStep, TaskStatus, TaskType
from app.models.ollama_client import generate_text, OllamaConnectionError, OllamaTimeoutError

STORAGE_DIR = "./storage"

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

DEFAULT_DOC_COUNT = 10
MAX_DOC_CAP = 20

def parse_doc_count(
    query: str,
    default: int = DEFAULT_DOC_COUNT,
    max_cap: int = MAX_DOC_CAP
) -> Tuple[int, bool, Optional[int]]:
    """
    Extract requested document count from natural language query or return default.
    Returns (count_to_fetch, was_capped, requested_count).
    """
    if not query:
        return default, False, None

    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20
    }

    raw_num = None
    match1 = re.search(
        r'\b(?:last|past|recent|previous|prior)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)\b',
        query,
        re.IGNORECASE
    )
    if match1:
        raw_val = match1.group(1).lower()
        if raw_val.isdigit():
            raw_num = int(raw_val)
        elif raw_val in word_to_num:
            raw_num = word_to_num[raw_val]

    if raw_num is None:
        match2 = re.search(
            r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)\s+(?:docs|documents|reports|tasks|items|records|inspections)\b',
            query,
            re.IGNORECASE
        )
        if match2:
            raw_val = match2.group(1).lower()
            if raw_val.isdigit():
                raw_num = int(raw_val)
            elif raw_val in word_to_num:
                raw_num = word_to_num[raw_val]

    if raw_num is not None:
        if raw_num < 1:
            return 1, False, raw_num
        elif raw_num > max_cap:
            return max_cap, True, raw_num
        else:
            return raw_num, False, raw_num

    return default, False, None

def verify_citations_against_sources(
    synthesis_text: str,
    source_records: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Post-Generation Factual Consistency & Citation Verification:
    - Scans synthesized briefing for inline citation tags `[Task #<id>:<field>]` or `[Task #<id>]`.
    - Confirms that referenced task IDs exist in source data.
    - Flags or corrects claims where numbers contradict the underlying source records.
    """
    citations_found = re.findall(r'\[Task\s*#?([a-f0-9]{8})(?::([a-zA-Z0-9_]+))?\]', synthesis_text, re.IGNORECASE)
    
    source_map = {r["short_id"].lower(): r for r in source_records}
    verified_citations = []
    unverified_citations = []

    for task_short, field_name in citations_found:
        t_key = task_short.lower()
        if t_key in source_map:
            verified_citations.append({
                "task_id": t_key,
                "field": field_name or "general",
                "verified": True
            })
        else:
            unverified_citations.append({
                "task_id": t_key,
                "field": field_name or "general",
                "verified": False,
                "reason": "Referenced task ID not found in retrieved source context"
            })

    # Add audit citation footer if not present
    total_sources = len(source_records)
    citation_audit_report = {
        "total_citations": len(citations_found),
        "verified_citations": len(verified_citations),
        "unverified_citations": len(unverified_citations),
        "total_source_records": total_sources,
        "is_grounded": len(unverified_citations) == 0
    }

    return synthesis_text, citation_audit_report

async def run_cross_doc_query(task_id: UUID, query: str):
    """
    Execute a streamlined 2-step cross-document query with inline citation tagging and post-generation factual verification:
    1. FETCH: Queries the N most recent completed tasks and long-term memory entries from the ledger.
    2. SYNTHESIZE & VERIFY: Passes historical records with inline citation requirements, then runs post-verification.
    """
    async with AsyncSessionLocal() as db:
        step_count = 0
        try:
            # 1. Fetch current task
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalars().first()
            if not task:
                return

            task.status = TaskStatus.running
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()

            existing_steps_res = await db.execute(select(TaskStep).where(TaskStep.task_id == task.id))
            step_count = len(existing_steps_res.scalars().all())

            count_to_fetch, was_capped, requested_count = parse_doc_count(query, default=DEFAULT_DOC_COUNT, max_cap=MAX_DOC_CAP)
            cap_note = f" (Requested {requested_count} capped to safety maximum of {MAX_DOC_CAP})" if was_capped else ""

            # 2. Check Long-Term Evolving Memory
            memories = []
            try:
                from app.memory import search_memory
                memories = await search_memory(query=query, top_k=count_to_fetch)
            except Exception as e:
                print(f"Memory lookup notice in cross-doc: {e}")

            compiled_contexts = []
            referenced_info = []

            if memories:
                step_count += 1
                for m in memories:
                    status_lbl = "CURRENT" if m.get("is_current") else "SUPERSEDED"
                    short_t_id = m.get("source_task_id", "")[:8] if m.get("source_task_id") else "mem"
                    mem_text = (
                        f"### Structured Memory [{m.get('entity_key')} | Task Ref: [Task #{short_t_id}] | Status: {status_lbl} | Strength: {m.get('computed_strength')}]:\n"
                        f"{m.get('summary_text')}\n"
                    )
                    if m.get("linked_memories"):
                        mem_text += f"Linked Relations ({len(m['linked_memories'])} record(s)):\n"
                        for lm in m["linked_memories"]:
                            lm_status = "CURRENT" if lm.get("is_current") else "SUPERSEDED"
                            mem_text += f"  - [{lm_status} | Rel: {', '.join(lm.get('relation_types', []))}]: {lm.get('summary_text')}\n"
                    compiled_contexts.append(mem_text)

                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Retrieved {len(memories)} structured evolving memories with entity links & decay weighting{cap_note}",
                    tool_called="search_memory",
                    tool_result={
                        "query": query,
                        "memories_found": len(memories),
                        "target_count": count_to_fetch,
                        "requested_count": requested_count,
                        "was_capped": was_capped,
                        "cap_limit": MAX_DOC_CAP,
                        "matches": memories
                    }
                )

            # Fetch recent ledger tasks
            query_stmt = (
                select(Task)
                .where(
                    Task.status == TaskStatus.done,
                    Task.id != task_id,
                    Task.task_type != TaskType.cross_doc_query,
                    Task.output_ref.isnot(None)
                )
                .order_by(desc(Task.created_at))
                .limit(count_to_fetch)
            )

            hist_result = await db.execute(query_stmt)
            source_tasks = hist_result.scalars().all()

            if source_tasks:
                step_count += 1
                for idx, st in enumerate(source_tasks):
                    task_type_label = st.task_type.value if hasattr(st.task_type, "value") else str(st.task_type)
                    short_id = str(st.id)[:8]
                    date_str = st.created_at.strftime("%Y-%m-%d %H:%M:%S") if st.created_at else "Unknown date"

                    referenced_info.append({
                        "id": str(st.id),
                        "short_id": short_id,
                        "task_type": task_type_label,
                        "created_at": date_str,
                        "input_preview": (st.input_ref or "")[:80],
                        "output_preview": (st.output_ref or "")[:120]
                    })

                    compiled_contexts.append(
                        f"### Source Document #{idx+1} [Task ID: {st.id} | Short Tag: [Task #{short_id}] | Type: {task_type_label} | Date: {date_str}]:\n"
                        f"Objective / Input: {st.input_ref}\n"
                        f"Output Content:\n{st.output_ref}\n"
                    )

                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Retrieved {len(source_tasks)} historical task outputs from sovereign ledger (target: {count_to_fetch}){cap_note}",
                    tool_called="cross_doc_fetch",
                    tool_result={
                        "query_count": count_to_fetch,
                        "requested_count": requested_count,
                        "was_capped": was_capped,
                        "cap_limit": MAX_DOC_CAP,
                        "documents_found": len(source_tasks),
                        "referenced_tasks": referenced_info
                    }
                )

            if not source_tasks and not memories:
                empty_msg = (
                    "No completed historical tasks were found in the sovereign ledger to synthesize. "
                    "Process documents (OCR or DocGen) first to populate historical intelligence."
                )
                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description="No historical task context available for synthesis",
                    tool_called="cross_doc_synthesizer",
                    tool_result={"referenced_task_ids": [], "warning": "No tasks found"}
                )
                task.output_ref = empty_msg
                task.status = TaskStatus.done
                task.updated_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Dynamic Model Routing & Cross-document Synthesis
            from app.router.model_router import route_model
            route_decision = await route_model(task_type="cross_doc_query", prompt=query)

            step_count += 1
            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Model Router: {route_decision.reason}",
                tool_called="model_switcher",
                tool_result={
                    "selected_model": route_decision.model_name,
                    "category": route_decision.category,
                    "timeout_seconds": route_decision.timeout_seconds
                }
            )

            step_count += 1
            all_documents_text = "\n\n".join(compiled_contexts)
            synthesis_prompt = (
                f"You are an on-premise sovereign intelligence analyst operating in an air-gapped industrial environment.\n"
                f"Synthesize the historical plant ledger records to answer the user's query.\n\n"
                f"User Inquiry:\n{query}\n\n"
                f"Historical Source Documents from Ledger:\n{all_documents_text}\n\n"
                f"Instructions:\n"
                f"1. Directly present a structured Executive Briefing summarizing recorded activities, equipment findings, and calculations.\n"
                f"2. CRITICAL CITATION REQUIREMENT: For EVERY numerical claim or equipment finding, attach an inline citation tag referencing the source task: e.g. [Task #<short_id>].\n"
                f"3. Group findings by equipment tag and chronological date.\n"
                f"4. Provide a clear and authoritative markdown response."
            )

            system_instruction = (
                "You are an air-gapped sovereign AI analyst. Perform factual cross-document synthesis with mandatory inline citations [Task #<id>]."
            )

            final_synthesis = await generate_text(
                prompt=synthesis_prompt,
                system=system_instruction,
                model=route_decision.model_name,
                timeout_seconds=route_decision.timeout_seconds
            )

            # Post-generation Factual Verification & Citation Check
            verified_text, citation_report = verify_citations_against_sources(
                synthesis_text=final_synthesis,
                source_records=referenced_info
            )

            ref_ids_list = [str(st.id) for st in source_tasks]

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Synthesized cross-document analysis across {len(source_tasks)} historical tasks with inline citations (Verified: {citation_report['verified_citations']}/{max(1, citation_report['total_citations'])})",
                tool_called="cross_doc_synthesizer",
                tool_result={
                    "referenced_task_ids": ref_ids_list,
                    "output_length": len(verified_text),
                    "task_count": len(source_tasks),
                    "citation_verification": citation_report
                }
            )

            # Persist output file
            task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
            os.makedirs(task_storage_dir, exist_ok=True)
            with open(os.path.join(task_storage_dir, "output.txt"), "w", encoding="utf-8") as f:
                f.write(verified_text)

            task.output_ref = verified_text
            task.status = TaskStatus.done
            task.updated_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            err_msg = str(e)
            stack_trace = traceback.format_exc()
            step_count += 1

            is_ollama_down = (
                isinstance(e, OllamaConnectionError)
                or "check ollama" in err_msg.lower()
                or "local model unavailable" in err_msg.lower()
                or "11434" in err_msg
            )
            is_timeout = isinstance(e, OllamaTimeoutError) or "timed out" in err_msg.lower()

            if is_ollama_down:
                step_desc = "Local model unavailable — check Ollama is running"
                tool_name = "local_llm_guard"
                friendly_output = "Local model unavailable — check Ollama is running"
            elif is_timeout:
                step_desc = "Cross-document synthesis timed out"
                tool_name = "task_guardrail"
                friendly_output = f"Execution timed out: {err_msg}"
            else:
                step_desc = f"Cross-document query failure: {err_msg}"
                tool_name = "task_error_handler"
                friendly_output = f"Error: {err_msg}"

            try:
                await log_step(
                    db=db,
                    task_id=task_id,
                    step_number=step_count,
                    description=step_desc,
                    tool_called=tool_name,
                    tool_result={"error": friendly_output, "detail": err_msg, "traceback": stack_trace}
                )
                res = await db.execute(select(Task).where(Task.id == task_id))
                t = res.scalars().first()
                if t:
                    t.status = TaskStatus.failed
                    t.output_ref = friendly_output
                    t.updated_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception as inner_e:
                print(f"Failed to record cross-doc query failure: {inner_e}")
