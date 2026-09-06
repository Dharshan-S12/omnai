import os
import re
import json
import uuid
import traceback
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional

from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Task, TaskStep, TaskStatus
from app.models.ollama_client import generate_text, OllamaConnectionError, OllamaTimeoutError
from app.rag import search_kb
from app.sandbox import run_code
from app.docgen import generate_docx

STORAGE_DIR = "./storage"
MAX_STEPS = 16

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

def extract_python_code(raw_text: str) -> str:
    """Extract python code from markdown code blocks or return raw text."""
    if not raw_text:
        return ""
    # Try finding ```python ... ```
    match = re.search(r"```(?:python|py)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()

def parse_plan_json(raw_text: str, task_type: str, input_text: str) -> List[Dict[str, Any]]:
    """Parse JSON plan list from model response with resilient fallbacks."""
    if raw_text:
        cleaned = raw_text.strip()
        # Remove markdown code formatting if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Try direct JSON parsing
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[:3]
        except Exception:
            pass

        # Try extracting bracketed JSON substring
        match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed[:3]
            except Exception:
                pass

    # Heuristic fallback based on task_type and text keywords
    normalized_type = str(task_type).lower()
    text_lower = input_text.lower()

    if "memory" in text_lower or "history" in text_lower or "trend" in text_lower or "previous" in text_lower or "prior" in text_lower or "last inspection" in text_lower:
        return [
            {
                "step": 1,
                "action": "search_memory",
                "description": "Retrieve structured equipment evolution and long-term inspection history",
                "instruction": input_text
            },
            {
                "step": 2,
                "action": "generate_text",
                "description": "Synthesize response analyzing historical trends and findings",
                "instruction": f"Synthesize trend analysis using retrieved memory records for: {input_text}"
            }
        ]
    elif "sop" in text_lower or "policy" in text_lower or "guideline" in text_lower or "approval" in text_lower or "inspection" in text_lower or normalized_type == "doc_gen":
        return [
            {
                "step": 1,
                "action": "search_kb",
                "description": "Query local knowledge base for relevant SOPs and compliance policies",
                "instruction": input_text
            },
            {
                "step": 2,
                "action": "generate_text",
                "description": "Synthesize and draft the document using retrieved SOP rules",
                "instruction": f"Draft the required response adhering to SOP guidelines for: {input_text}"
            }
        ]
    elif "calculate" in text_lower or "compute" in text_lower or "code" in text_lower or normalized_type == "code_exec":
        return [
            {
                "step": 1,
                "action": "run_code",
                "description": "Execute calculation or script in isolated sandbox",
                "instruction": f"Perform computation for: {input_text}"
            }
        ]
    else:
        return [
            {
                "step": 1,
                "action": "generate_text",
                "description": "Analyze input and formulate response",
                "instruction": input_text
            }
        ]

async def run_agent(task_id: UUID, task_type: str, input_text: str):
    """
    Multi-Step Sovereign Agent Loop:
    1. PLAN: Decomposes user goal into 2-4 concrete tool steps using local LLM.
    2. ACT & OBSERVE: Executes each step using local tools (search_kb, run_code, generate_text).
    3. SYNTHESIZE: Aggregates all tool observations into the final output.
    All steps and tool calls are persisted to task_steps table. Max step count capped at 6.
    """
    async with AsyncSessionLocal() as db:
        step_count = 0
        try:
            # 1. Fetch Task
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

            # If source_task_id is present, fetch upstream task output (e.g. OCR structured data)
            source_context = ""
            if task.source_task_id:
                source_res = await db.execute(select(Task).where(Task.id == task.source_task_id))
                source_task = source_res.scalars().first()
                if source_task and source_task.output_ref:
                    source_context = (
                        f"### Upstream Document Context (Source Task {task.source_task_id}):\n"
                        f"{source_task.output_ref}\n\n"
                    )

            # ----------------------------------------------------
            # PART 3: SEMANTIC RESPONSE CACHE LOOKUP
            # ----------------------------------------------------
            from app.cache import lookup_semantic_cache
            cache_hit = lookup_semantic_cache(prompt_text=input_text, task_type=task_type)
            if cache_hit:
                cached_output = cache_hit["output_text"]
                cached_sim = cache_hit["similarity"]
                cached_id = str(cache_hit["cached_task_id"])
                cached_conf = cache_hit.get("confidence_score", 95.0)

                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Semantic Cache Hit: Reused analysis from Task #{cached_id[:8]} (Similarity: {round(cached_sim*100, 1)}%)",
                    tool_called="semantic_cache_hit",
                    tool_result={
                        "matched_task_id": cached_id,
                        "similarity": cached_sim,
                        "age_hours": cache_hit.get("age_hours"),
                        "matched_prompt": cache_hit.get("matched_prompt")
                    }
                )

                task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
                os.makedirs(task_storage_dir, exist_ok=True)
                with open(os.path.join(task_storage_dir, "output.txt"), "w", encoding="utf-8") as f:
                    f.write(cached_output)

                if str(task_type).lower() == "doc_gen":
                    doc_title_words = input_text.split()[:8]
                    doc_title = " ".join(doc_title_words).strip(".:,; ") or "Sovereign Generated Document"
                    docx_file_path = os.path.join(task_storage_dir, "output.docx")
                    generate_docx(title=doc_title, content=cached_output, output_path=docx_file_path)

                    step_count += 1
                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description="Generated Word document (.docx) from cached analysis",
                        tool_called="docgen_docx",
                        tool_result={"file_path": docx_file_path, "from_cache": True}
                    )

                    step_count += 1
                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description="Compliance gate: Cached document placed in 'pending_approval' awaiting supervisor sign-off",
                        tool_called="human_approval_gate",
                        tool_result={
                            "status": "pending_approval",
                            "download_locked": True,
                            "confidence_score": cached_conf,
                            "from_cache": True
                        }
                    )
                    task.status = TaskStatus.pending_approval
                else:
                    task.status = TaskStatus.done

                task.output_ref = cached_output
                task.confidence_score = cached_conf
                task.updated_at = datetime.utcnow()
                await db.commit()
                return

            from app.router.model_router import route_model, generate_with_escalation

            # ----------------------------------------------------
            # FAST PATH: DIRECT REASONING FOR text_gen
            # ----------------------------------------------------
            if task_type == "text_gen":
                reasoning_decision = await route_model(task_type="text_gen", prompt=input_text, category_hint="reasoning")

                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Model Router (Direct Reasoning): Switched to '{reasoning_decision.model_name}' for direct inference & deep reasoning",
                    tool_called="model_switcher",
                    tool_result={
                        "stage": "direct_reasoning",
                        "selected_model": reasoning_decision.model_name,
                        "category": reasoning_decision.category,
                        "timeout_seconds": reasoning_decision.timeout_seconds
                    }
                )

                reasoning_system = (
                    "You are MRPL OmniAI EngineCore, an expert sovereign engineering and operations intelligence assistant for Mangalore Refinery and Petrochemicals Limited (MRPL).\n"
                    "You have full domain capabilities for technical document analysis, ISO vibration assessment, SOP compliance validation, and maintenance report synthesis.\n"
                    "Provide a thorough, direct, authoritative, and professionally structured response addressing the user's prompt using the provided document context or equipment history. Never state that you cannot process documents or perform analysis."
                )

                reasoning_prompt = f"{source_context}User Prompt: {input_text}\n\nProvide the requested analysis, summary, or response:"

                final_output, escalation_info = await generate_with_escalation(
                    prompt=reasoning_prompt,
                    system=reasoning_system,
                    min_length=80,
                    fast_model="qwen2.5:3b",
                    primary_model=reasoning_decision.model_name
                )

                if escalation_info and escalation_info.get("escalated"):
                    step_count += 1
                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Model Escalation: Escalated to {escalation_info['primary_model']} ({escalation_info['reason']})",
                        tool_called="model_escalation",
                        tool_result=escalation_info
                    )

                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Direct reasoning completed via {escalation_info['primary_model'] if (escalation_info and escalation_info.get('escalated')) else reasoning_decision.model_name}",
                    tool_called="direct_reasoning",
                    tool_result={
                        "model": reasoning_decision.model_name,
                        "output_length": len(final_output)
                    }
                )

                # Save output artifacts
                task_dir = os.path.join(STORAGE_DIR, str(task.id))
                os.makedirs(task_dir, exist_ok=True)
                with open(os.path.join(task_dir, "output.txt"), "w", encoding="utf-8") as f:
                    f.write(final_output)

                task.status = TaskStatus.done
                task.output_ref = final_output
                task.updated_at = datetime.utcnow()
                await db.commit()
                return

            # ----------------------------------------------------
            # PHASE 1: PLAN (For Code Exec & DocGen Multi-Step Tasks)
            # ----------------------------------------------------
            planner_decision = await route_model(task_type=task_type, prompt=input_text, category_hint="fast_inference")

            step_count += 1
            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Model Router (Planner): {planner_decision.reason}",
                tool_called="model_switcher",
                tool_result={
                    "stage": "planner",
                    "selected_model": planner_decision.model_name,
                    "category": planner_decision.category,
                    "timeout_seconds": planner_decision.timeout_seconds
                }
            )

            step_count += 1
            planner_system = (
                "You are an on-premise sovereign AI agent planner operating in an air-gapped environment.\n"
                "Analyze the user's task and create a concise execution plan with 2 to 3 sequential steps.\n\n"
                "Available Tools:\n"
                "- search_memory: Query structured long-term evolving memory for equipment history, past inspection trends, previous measurements, and linked evolution chains.\n"
                "- search_kb: Search local vector knowledge base for SOPs, guidelines, compliance policies, or reference documents.\n"
                "- run_code: Execute Python code in a secure sandboxed environment for calculations, statistics, or data processing.\n"
                "- generate_text: Perform intermediate domain analysis, text reasoning, or drafting.\n\n"
                "Output STRICTLY a JSON array of step objects, with no surrounding commentary. Format:\n"
                "[\n"
                "  {\"step\": 1, \"action\": \"search_memory|search_kb|run_code|generate_text\", \"description\": \"brief summary\", \"instruction\": \"query or prompt\"}\n"
                "]"
            )

            planner_prompt = f"Task Type: {task_type}\n"
            if source_context:
                planner_prompt += f"{source_context}"
            planner_prompt += f"User Goal: {input_text}\n\nGenerate the plan JSON:"

            plan_raw = await generate_text(
                prompt=planner_prompt,
                system=planner_system,
                model=planner_decision.model_name,
                timeout_seconds=planner_decision.timeout_seconds
            )

            effective_input = f"{source_context}Goal: {input_text}" if source_context else input_text
            steps_plan = parse_plan_json(plan_raw, task_type, effective_input)

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Generated multi-step execution plan ({len(steps_plan)} step(s)) using {planner_decision.model_name}",
                tool_called="agent_planner",
                tool_result={"plan": steps_plan, "raw_plan_preview": plan_raw[:200] if plan_raw else "", "model": planner_decision.model_name}
            )

            # ----------------------------------------------------
            # PHASE 2: ACT & OBSERVE
            # ----------------------------------------------------
            accumulated_observations: List[str] = []
            if source_context:
                accumulated_observations.append(source_context)

            # Metrics for Confidence Scoring & Multi-Agent DocGen Pipeline
            total_retrieved_chunks = 0
            total_discarded_chunks = 0
            kept_chunk_distances: List[float] = []
            all_kept_chunks: List[Dict[str, Any]] = []

            for step_item in steps_plan:
                if step_count >= (MAX_STEPS - 1):
                    break

                step_count += 1
                action = str(step_item.get("action", "")).lower()
                desc = step_item.get("description", f"Step {step_count}")
                instruction = step_item.get("instruction", input_text)

                # Tool: Long-Term Structured Memory Search
                if action == "search_memory" or ("search" in action and "memory" in action) or (not action and ("history" in desc.lower() or "trend" in desc.lower() or "previous" in desc.lower())):
                    from app.memory import search_memory
                    search_query = instruction or input_text
                    mem_results = await search_memory(query=search_query, top_k=5)

                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Queried structured long-term memory for '{search_query[:60]}'",
                        tool_called="search_memory",
                        tool_result={"query": search_query, "memories_found": len(mem_results), "matches": mem_results}
                    )

                    context_snippet = f"### Retrieved Long-Term Memory (Query: {search_query}):\n"
                    if not mem_results:
                        context_snippet += "No matching prior memory records found.\n"
                    for m in mem_results:
                        status_str = "CURRENT" if m.get("is_current") else "SUPERSEDED"
                        context_snippet += f"- [{status_str} Memory | {m.get('entity_key')} | Strength: {m.get('computed_strength')}]: {m.get('summary_text')}\n"
                        if m.get("explanation"):
                            context_snippet += f"  (Recall Explanation: {m.get('explanation')})\n"
                        if m.get("linked_memories"):
                            context_snippet += f"  Linked Records ({len(m['linked_memories'])}):\n"
                            for lm in m["linked_memories"]:
                                lm_status = "CURRENT" if lm.get("is_current") else "SUPERSEDED"
                                context_snippet += f"    * [{lm_status} | {lm.get('entity_key')} | Rel: {', '.join(lm.get('relation_types', []))}]: {lm.get('summary_text')}\n"
                    accumulated_observations.append(context_snippet)

                # Tool 1: Knowledge Base Search (RAG) + Corrective Retrieval Grading
                elif action == "search_kb" or ("search" in action and "kb" in action) or (not action and ("sop" in desc.lower() or "policy" in desc.lower())):
                    search_query = instruction or input_text
                    kb_results = search_kb(query=search_query, top_k=3)
                    total_retrieved_chunks += len(kb_results)
                    
                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Queried local SOP knowledge base for '{search_query[:60]}'",
                        tool_called="search_kb",
                        tool_result={"query": search_query, "chunks_found": len(kb_results), "matches": kb_results}
                    )

                    kept_chunks = []
                    discarded_chunks = []

                    if kb_results:
                        # ----------------------------------------------------
                        # SAFETY GATE 1: Corrective Retrieval Grading
                        # ----------------------------------------------------
                        grading_decision = await route_model(task_type="text_gen", prompt=search_query, category_hint="fast_inference")
                        grading_prompt = (
                            f"You are a strict document retrieval grader evaluating whether reference excerpts are relevant to answering a user query.\n"
                            f"User Query: {search_query}\n\n"
                            f"Evaluate each excerpt below:\n"
                        )
                        for i, r in enumerate(kb_results):
                            grading_prompt += f"[Excerpt {i+1}]: {r.get('text')}\n"
                        grading_prompt += (
                            f"\nFor each excerpt, output whether it is relevant (yes/no).\n"
                            f"Output STRICTLY a JSON array of strings, e.g. [\"yes\", \"no\"], with one entry per excerpt."
                        )

                        step_count += 1
                        try:
                            grade_raw = await generate_text(
                                prompt=grading_prompt,
                                system="You are an automated RAG relevance grader. Respond ONLY with a valid JSON array of 'yes' or 'no' strings.",
                                model=grading_decision.model_name,
                                timeout_seconds=grading_decision.timeout_seconds
                            )
                            # Parse JSON array
                            cleaned_grade = grade_raw.strip()
                            if cleaned_grade.startswith("```"):
                                cleaned_grade = re.sub(r"^```(?:json)?\s*", "", cleaned_grade)
                                cleaned_grade = re.sub(r"\s*```$", "", cleaned_grade).strip()
                            
                            grades = []
                            try:
                                grades = json.loads(cleaned_grade)
                            except Exception:
                                # Fallback: search for words yes/no
                                for line in grade_raw.splitlines():
                                    if "yes" in line.lower():
                                        grades.append("yes")
                                    elif "no" in line.lower():
                                        grades.append("no")

                            for idx, r in enumerate(kb_results):
                                g = str(grades[idx]).lower() if idx < len(grades) else "yes"
                                if "yes" in g or g == "true":
                                    kept_chunks.append(r)
                                    if r.get("distance") is not None:
                                        kept_chunk_distances.append(float(r["distance"]))
                                else:
                                    discarded_chunks.append(r)

                        except Exception as grade_err:
                            # Fallback gracefully to keep all chunks if grading failed
                            kept_chunks = list(kb_results)
                            for r in kept_chunks:
                                if r.get("distance") is not None:
                                    kept_chunk_distances.append(float(r["distance"]))

                        total_discarded_chunks += len(discarded_chunks)

                        await log_step(
                            db=db,
                            task_id=task.id,
                            step_number=step_count,
                            description=f"Corrective RAG Grading: {len(kept_chunks)} relevant chunk(s) kept, {len(discarded_chunks)} irrelevant discarded",
                            tool_called="corrective_rag_grade",
                            tool_result={
                                "total_evaluated": len(kb_results),
                                "kept_count": len(kept_chunks),
                                "discarded_count": len(discarded_chunks),
                                "kept_sources": [k.get("source") for k in kept_chunks],
                                "discarded_sources": [d.get("source") for d in discarded_chunks]
                            }
                        )
                        all_kept_chunks.extend(kept_chunks)

                    # Build context snippet for synthesizer
                    if kept_chunks:
                        context_snippet = f"### Retrieved & Verified SOP Reference (Query: {search_query}):\n"
                        for r in kept_chunks:
                            context_snippet += f"- [Source: {r.get('source')}]: {r.get('text')}\n"
                    elif kb_results and not kept_chunks:
                        context_snippet = (
                            f"### Retrieved SOP Reference (Query: {search_query}):\n"
                            f"[Notice: All {len(kb_results)} candidate SOP chunks were graded irrelevant. Proceeding without ungrounded assumptions.]\n"
                        )
                    else:
                        context_snippet = f"### Retrieved SOP Reference (Query: {search_query}): No matches found in knowledge base.\n"

                    accumulated_observations.append(context_snippet)

                # Tool 2: Code Execution Sandbox (Switches to Coder Model)
                elif action == "run_code" or ("code" in action and "exec" in action) or (not action and ("calculate" in desc.lower() or "compute" in desc.lower())):
                    coder_decision = await route_model(task_type="code_exec", prompt=instruction or input_text, category_hint="coding")

                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Model Router (Coding): {coder_decision.reason}",
                        tool_called="model_switcher",
                        tool_result={
                            "stage": "code_gen",
                            "selected_model": coder_decision.model_name,
                            "category": coder_decision.category
                        }
                    )

                    step_count += 1
                    # Generate executable Python script
                    code_gen_prompt = (
                        f"Write a clean, self-contained Python script to solve the following calculation or data task:\n"
                        f"Task: {input_text}\n"
                        f"Step Instruction: {instruction}\n"
                        f"Print all calculated results clearly to standard output with print().\n"
                        f"Output ONLY executable Python code inside a ```python ``` code block."
                    )
                    code_raw = await generate_text(
                        prompt=code_gen_prompt,
                        model=coder_decision.model_name,
                        timeout_seconds=coder_decision.timeout_seconds
                    )
                    code_to_run = extract_python_code(code_raw)

                    sandbox_output = run_code(code_to_run, timeout_seconds=15)

                    status_note = " (Execution Timed Out after 15s)" if sandbox_output.get("timed_out") else ""
                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Executed Python script in isolated sandbox (exit code {sandbox_output['exit_code']}){status_note}",
                        tool_called="code_sandbox",
                        tool_result={
                            "code": code_to_run,
                            "stdout": sandbox_output["stdout"],
                            "stderr": sandbox_output["stderr"],
                            "exit_code": sandbox_output["exit_code"],
                            "timed_out": sandbox_output["timed_out"]
                        }
                    )

                    obs_text = f"### Sandbox Execution Results:\n"
                    if sandbox_output["timed_out"]:
                        obs_text += "Status: Execution timed out after 15 seconds (Sandbox process killed).\n"
                    if sandbox_output["stdout"]:
                        obs_text += f"Output:\n{sandbox_output['stdout']}\n"
                    if sandbox_output["stderr"]:
                        obs_text += f"Errors/Warnings:\n{sandbox_output['stderr']}\n"
                    accumulated_observations.append(obs_text)

                # Tool 3: Text Reasoning / Intermediate Drafting
                else:
                    reasoning_decision = await route_model(task_type=task_type, prompt=instruction or input_text)
                    context_history = "\n\n".join(accumulated_observations) if accumulated_observations else "No prior tool context."
                    step_prompt = (
                        f"User Goal: {input_text}\n\n"
                        f"Prior Context & Evidence:\n{context_history}\n\n"
                        f"Step Instruction: {instruction}\n"
                        f"Execute this step with thoroughness and precision."
                    )
                    step_output = await generate_text(
                        prompt=step_prompt,
                        model=reasoning_decision.model_name,
                        timeout_seconds=reasoning_decision.timeout_seconds
                    )

                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Executed intermediate step via {reasoning_decision.model_name}: {desc[:60]}",
                        tool_called="generate_text",
                        tool_result={
                            "instruction": instruction,
                            "model": reasoning_decision.model_name,
                            "output_preview": step_output[:200] if step_output else "",
                            "output_length": len(step_output)
                        }
                    )
                    accumulated_observations.append(f"### Intermediate Analysis ({desc}):\n{step_output}")

            # ----------------------------------------------------
            # PHASE 3: FINAL SYNTHESIS & SAFETY CRITIQUE
            # ----------------------------------------------------
            step_count += 1
            if step_count > MAX_STEPS:
                # Cap exceeded error handling
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Agent exceeded maximum step limit ({MAX_STEPS})",
                    tool_called="agent_guardrail",
                    tool_result={"error": "Maximum step limit exceeded", "max_steps": MAX_STEPS}
                )
                task.status = TaskStatus.failed
                task.output_ref = "Error: Task exceeded maximum allowed step budget."
                task.updated_at = datetime.utcnow()
                await db.commit()
                return

            # ----------------------------------------------------
            # DOC_GEN: SPECIALIST MULTI-AGENT PIPELINE
            # ----------------------------------------------------
            if str(task_type).lower() == "doc_gen":
                from app.agent.multi_agent_docgen import run_multi_agent_docgen_pipeline
                from app.cache import store_semantic_cache

                final_output, confidence_score, step_count = await run_multi_agent_docgen_pipeline(
                    db=db,
                    task=task,
                    step_count=step_count,
                    input_text=input_text,
                    source_context=source_context,
                    kept_chunks=all_kept_chunks,
                    total_retrieved_chunks=total_retrieved_chunks,
                    total_discarded_chunks=total_discarded_chunks,
                    kept_chunk_distances=kept_chunk_distances
                )

                # Gate 3: Mandatory Human Approval Gate
                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description="Compliance gate: Document placed in 'pending_approval' awaiting supervisor sign-off",
                    tool_called="human_approval_gate",
                    tool_result={
                        "status": "pending_approval",
                        "download_locked": True,
                        "confidence_score": confidence_score,
                        "action_required": "Review synthesized output and approve via POST /tasks/{id}/approve"
                    }
                )

                task.status = TaskStatus.pending_approval
                task.output_ref = final_output
                task.confidence_score = confidence_score
                task.updated_at = datetime.utcnow()
                await db.commit()

                try:
                    store_semantic_cache(
                        task_id=task.id,
                        prompt_text=input_text,
                        output_text=final_output,
                        task_type="doc_gen",
                        confidence_score=confidence_score
                    )
                except Exception as cache_err:
                    print(f"Semantic cache store notice: {cache_err}")

                return

            # ----------------------------------------------------
            # SINGLE AGENT SYNTHESIS (code_exec and general fallback)
            # ----------------------------------------------------
            synth_decision = await route_model(task_type=task_type, prompt=input_text, category_hint="general")

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Model Router (Synthesis): {synth_decision.reason}",
                tool_called="model_switcher",
                tool_result={
                    "stage": "synthesis",
                    "selected_model": synth_decision.model_name,
                    "category": synth_decision.category
                }
            )

            step_count += 1
            context_all = "\n\n".join(accumulated_observations) if accumulated_observations else "Direct execution."
            synthesis_prompt = (
                f"You are an on-premise sovereign AI synthesizer.\n"
                f"Synthesize the final authoritative output for the user's task, incorporating all observations, retrieved SOP knowledge, and sandbox execution results.\n\n"
                f"User Task:\n{input_text}\n\n"
                f"Execution Observations & Evidence:\n{context_all}\n\n"
                f"Provide a structured, complete, and professional response."
            )

            final_output = await generate_text(
                prompt=synthesis_prompt,
                system="You are a sovereign confidential document synthesis agent. Produce clear, formatted output.",
                model=synth_decision.model_name,
                timeout_seconds=synth_decision.timeout_seconds
            )

            # ----------------------------------------------------
            # SAFETY GATE 2: Self-Critique & Contradiction Check
            # ----------------------------------------------------
            step_count += 1
            critique_decision = await route_model(task_type="text_gen", prompt=input_text, category_hint="fast_inference")
            critique_system = (
                "You are an impartial safety & quality critic for confidential industrial documents.\n"
                "Review the synthesized output against the source grounding context.\n"
                "Does this document state any figure, measurement, threshold, or compliance status that contradicts the source material?\n"
                "If there are issues or contradictions, list them concisely. If there are no contradictions and the document is accurate, respond strictly with: 'No issues found.'"
            )
            critique_prompt = (
                f"Grounding Reference Context:\n{context_all}\n\n"
                f"Synthesized Document to Verify:\n{final_output}\n\n"
                f"Critique Evaluation:"
            )

            critique_text = "No issues found."
            try:
                critique_text = await generate_text(
                    prompt=critique_prompt,
                    system=critique_system,
                    model=critique_decision.model_name,
                    timeout_seconds=critique_decision.timeout_seconds
                )
            except Exception as crit_err:
                critique_text = f"Automated critique warning: {crit_err}"

            critique_lower = critique_text.lower()
            has_critique_issues = "no issues found" not in critique_lower and "no issues" not in critique_lower

            # ----------------------------------------------------
            # CONFIDENCE SCORE CALCULATION (0 - 100)
            # ----------------------------------------------------
            penalty_critique = 35.0 if has_critique_issues else 0.0
            if kept_chunk_distances:
                avg_dist = sum(kept_chunk_distances) / len(kept_chunk_distances)
                penalty_dist = min(30.0, avg_dist * 35.0)
            elif total_retrieved_chunks > 0 and not kept_chunk_distances:
                penalty_dist = 25.0
            else:
                penalty_dist = 0.0
            penalty_discard = 10.0 if total_discarded_chunks > 0 else 0.0

            raw_confidence = 100.0 - penalty_critique - penalty_dist - penalty_discard
            confidence_score = round(max(5.0, min(99.0, raw_confidence)), 1)
            task.confidence_score = confidence_score

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Safety Self-Critique: {'No issues found' if not has_critique_issues else 'Contradiction/grounding issues flagged'} (Confidence: {confidence_score}%)",
                tool_called="self_critique",
                tool_result={
                    "critique_summary": critique_text.strip()[:300],
                    "has_issues": has_critique_issues,
                    "confidence_score": confidence_score,
                    "penalties": {
                        "critique_penalty": penalty_critique,
                        "distance_penalty": round(penalty_dist, 1),
                        "discard_penalty": penalty_discard
                    }
                }
            )

            step_count += 1
            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Synthesized final response with {synth_decision.model_name} (Confidence: {confidence_score}%)",
                tool_called="agent_synthesizer",
                tool_result={
                    "model": synth_decision.model_name,
                    "output_length": len(final_output),
                    "confidence_score": confidence_score,
                    "preview": final_output[:200] if final_output else ""
                }
            )

            # Persist output file & update Task record
            task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
            os.makedirs(task_storage_dir, exist_ok=True)
            output_file_path = os.path.join(task_storage_dir, "output.txt")
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(final_output)

            if str(task_type).lower() == "doc_gen":
                doc_title_words = input_text.split()[:8]
                doc_title = " ".join(doc_title_words).strip(".:,; ") or "Sovereign Generated Document"
                docx_file_path = os.path.join(task_storage_dir, "output.docx")
                generate_docx(title=doc_title, content=final_output, output_path=docx_file_path)

                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description="Generated Word document (.docx) from synthesized report",
                    tool_called="docgen_docx",
                    tool_result={"file_path": docx_file_path}
                )

                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description="Compliance gate: Document placed in 'pending_approval' awaiting supervisor sign-off",
                    tool_called="human_approval_gate",
                    tool_result={
                        "status": "pending_approval",
                        "download_locked": True,
                        "confidence_score": confidence_score
                    }
                )
                task.status = TaskStatus.pending_approval
            else:
                task.status = TaskStatus.done

            task.output_ref = final_output
            task.confidence_score = confidence_score
            task.updated_at = datetime.utcnow()
            await db.commit()

            # Ingest completed document / synthesis into long-term memory
            try:
                from app.memory import ingest_memory
                doc_title_extracted = input_text[:60]
                await ingest_memory(
                    task_id=task.id,
                    structured_output={
                        "document_title": f"Agent Output: {doc_title_extracted}",
                        "findings": final_output[:500],
                        "task_prompt": input_text,
                        "confidence_score": confidence_score
                    },
                    doc_type=str(task_type)
                )
            except Exception as mem_err:
                print(f"Warning: Long-term memory ingestion skipped: {mem_err}")

            task.output_ref = final_output
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
                or "connection refused" in err_msg.lower()
            )
            is_timeout = isinstance(e, OllamaTimeoutError) or "timed out" in err_msg.lower()

            if is_ollama_down:
                step_desc = "Local model unavailable — check Ollama is running"
                tool_name = "local_llm_guard"
                friendly_output = "Local model unavailable — check Ollama is running"
            elif is_timeout:
                step_desc = "Model execution timed out"
                tool_name = "task_guardrail"
                friendly_output = f"Execution timed out: {err_msg}"
            else:
                step_desc = f"Agent loop failure: {err_msg}"
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
                print(f"Failed to record agent task failure: {inner_e}")
