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
MAX_STEPS = 6

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

    if "sop" in text_lower or "policy" in text_lower or "guideline" in text_lower or "approval" in text_lower or "inspection" in text_lower or normalized_type == "doc_gen":
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

            from app.router.model_router import route_model

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
                    "You are a sovereign AI intelligence agent operating in a secure air-gapped environment.\n"
                    "Provide a direct, authoritative, and well-structured response to the user's prompt."
                )

                reasoning_prompt = f"{source_context}User Prompt: {input_text}\n\nAuthoritative Response:"

                final_output = await generate_text(
                    prompt=reasoning_prompt,
                    system=reasoning_system,
                    model=reasoning_decision.model_name,
                    timeout_seconds=reasoning_decision.timeout_seconds
                )

                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Direct reasoning completed via {reasoning_decision.model_name}",
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
                "- search_kb: Search local vector knowledge base for SOPs, guidelines, compliance policies, or reference documents.\n"
                "- run_code: Execute Python code in a secure sandboxed environment for calculations, statistics, or data processing.\n"
                "- generate_text: Perform intermediate domain analysis, text reasoning, or drafting.\n\n"
                "Output STRICTLY a JSON array of step objects, with no surrounding commentary. Format:\n"
                "[\n"
                "  {\"step\": 1, \"action\": \"search_kb|run_code|generate_text\", \"description\": \"brief summary\", \"instruction\": \"query or prompt\"}\n"
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

            for step_item in steps_plan:
                if step_count >= (MAX_STEPS - 1):
                    break

                step_count += 1
                action = str(step_item.get("action", "")).lower()
                desc = step_item.get("description", f"Step {step_count}")
                instruction = step_item.get("instruction", input_text)

                # Tool 1: Knowledge Base Search (RAG)
                if action == "search_kb" or ("search" in action and "kb" in action) or (not action and ("sop" in desc.lower() or "policy" in desc.lower())):
                    search_query = instruction or input_text
                    kb_results = search_kb(query=search_query, top_k=3)
                    
                    await log_step(
                        db=db,
                        task_id=task.id,
                        step_number=step_count,
                        description=f"Queried local SOP knowledge base for '{search_query[:60]}'",
                        tool_called="search_kb",
                        tool_result={"query": search_query, "chunks_found": len(kb_results), "matches": kb_results}
                    )

                    context_snippet = f"### Retrieved SOP Reference (Query: {search_query}):\n"
                    for r in kb_results:
                        context_snippet += f"- [Source: {r.get('source')}]: {r.get('text')}\n"
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
            # PHASE 3: FINAL SYNTHESIS
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

            await log_step(
                db=db,
                task_id=task.id,
                step_number=step_count,
                description=f"Synthesized final response with {synth_decision.model_name} from all step observations and tool results",
                tool_called="agent_synthesizer",
                tool_result={
                    "model": synth_decision.model_name,
                    "output_length": len(final_output),
                    "preview": final_output[:200] if final_output else ""
                }
            )

            # Persist output file & update Task record
            task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
            os.makedirs(task_storage_dir, exist_ok=True)
            output_file_path = os.path.join(task_storage_dir, "output.txt")
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(final_output)

            # If doc_gen task, generate downloadable formatted Word (.docx) document
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
                    description="Generated Word document (.docx)",
                    tool_called="docgen_docx",
                    tool_result={
                        "file_path": docx_file_path,
                        "file_size_bytes": os.path.getsize(docx_file_path) if os.path.exists(docx_file_path) else 0,
                        "document_title": doc_title
                    }
                )

            task.output_ref = final_output
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
