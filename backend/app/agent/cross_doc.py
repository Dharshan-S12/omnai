import os
import re
import json
import uuid
import traceback
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional

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
        created_at=datetime.utcnow()
    )
    db.add(step)
    await db.commit()
    return step

def parse_doc_count(query: str, default: int = 5) -> int:
    """Extract requested document count from natural language query or return default."""
    if not query:
        return default
    # Look for "last 5", "past 3", "10 documents", etc.
    match = re.search(r'\b(?:last|past|recent)\s+(\d{1,2})\b', query, re.IGNORECASE)
    if match:
        try:
            return min(max(int(match.group(1)), 1), 20)
        except Exception:
            pass

    match2 = re.search(r'\b(\d{1,2})\s+(?:docs|documents|reports|tasks|items)\b', query, re.IGNORECASE)
    if match2:
        try:
            return min(max(int(match2.group(1)), 1), 20)
        except Exception:
            pass

    return default

async def run_cross_doc_query(task_id: UUID, query: str):
    """
    Execute a streamlined 2-step cross-document query:
    1. FETCH: Queries the N most recent completed tasks from the ledger.
    2. SYNTHESIZE: Passes all historical task outputs to local LLM for cross-document synthesis.
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
            task.updated_at = datetime.utcnow()
            await db.commit()

            # Initialize step_count based on existing steps (e.g. from Auto-Router)
            existing_steps_res = await db.execute(select(TaskStep).where(TaskStep.task_id == task.id))
            step_count = len(existing_steps_res.scalars().all())

            count_to_fetch = parse_doc_count(query, default=5)

            # 2. Step 1: Fetch recent completed tasks (excluding cross_doc_query tasks to avoid recursion)
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

            step_count += 1
            referenced_info = []
            compiled_contexts = []

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
                    f"### Document #{idx+1} [Task ID: {st.id} | Type: {task_type_label} | Date: {date_str}]:\n"
                    f"Objective / Input: {st.input_ref}\n"
                    f"Output Content:\n{st.output_ref}\n"
                )

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Retrieved {len(source_tasks)} historical task outputs from sovereign ledger (target: {count_to_fetch})",
                tool_called="cross_doc_fetch",
                tool_result={
                    "query_count": count_to_fetch,
                    "documents_found": len(source_tasks),
                    "referenced_tasks": referenced_info
                }
            )

            # If no tasks exist in history
            if not source_tasks:
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
                task.updated_at = datetime.utcnow()
                await db.commit()
                return

            # 3. Step 2: Dynamic Model Routing & Cross-document Synthesis
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
                    "timeout_seconds": route_decision.timeout_seconds,
                    "is_fallback": route_decision.is_fallback,
                    "available_candidates": route_decision.available_candidates
                }
            )

            step_count += 1
            all_documents_text = "\n\n".join(compiled_contexts)
            synthesis_prompt = (
                f"You are an on-premise sovereign intelligence analyst operating in an air-gapped environment.\n"
                f"The user is asking for recorded updates, latest news, trends, anomalies, or historical data from the local database ledger.\n\n"
                f"User Inquiry:\n{query}\n\n"
                f"Historical Source Documents from Ledger:\n{all_documents_text}\n\n"
                f"Instructions:\n"
                f"1. Directly present a structured Executive Briefing summarizing the latest recorded activities, status, equipment findings, and calculations.\n"
                f"2. Group key information by date/equipment and highlight status (e.g. COMPLIANT / ANOMALY), key metrics, and observations.\n"
                f"3. Do NOT make meta-disclaimers or talk about journalistic internet news. Treat 'news' as the latest recorded on-premise data.\n"
                f"4. Provide a clear and authoritative markdown response."
            )

            system_instruction = (
                "You are an air-gapped sovereign AI analyst. Perform factual, direct cross-document synthesis based strictly on the provided ledger."
            )

            final_synthesis = await generate_text(
                prompt=synthesis_prompt,
                system=system_instruction,
                model=route_decision.model_name,
                timeout_seconds=route_decision.timeout_seconds
            )

            # Store references in metadata block at bottom or JSON metadata if helpful
            ref_ids_list = [str(st.id) for st in source_tasks]

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Synthesized cross-document analysis across {len(source_tasks)} historical tasks",
                tool_called="cross_doc_synthesizer",
                tool_result={
                    "referenced_task_ids": ref_ids_list,
                    "output_length": len(final_synthesis),
                    "task_count": len(source_tasks)
                }
            )

            # Persist output file
            task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
            os.makedirs(task_storage_dir, exist_ok=True)
            with open(os.path.join(task_storage_dir, "output.txt"), "w", encoding="utf-8") as f:
                f.write(final_synthesis)

            task.output_ref = final_synthesis
            task.status = TaskStatus.done
            task.updated_at = datetime.utcnow()
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
                    t.updated_at = datetime.utcnow()
                    await db.commit()
            except Exception as inner_e:
                print(f"Failed to record cross-doc query failure: {inner_e}")
