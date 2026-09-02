import os
import json
import uuid
import traceback
from uuid import UUID
from datetime import datetime

from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Task, TaskStep, Document, TaskStatus, TaskType
from app.router.task_router import route_task
from app.models.ollama_client import generate_vision, OllamaConnectionError, OllamaTimeoutError
from app.models.ocr_classify import classify_document_type
from app.models.ocr_extract import extract_structured_fields
from app.models.pdf_processor import is_pdf, process_pdf_document
from app.agent.loop import run_agent
from app.agent.cross_doc import run_cross_doc_query

STORAGE_DIR = "./storage"

async def log_step(
    db,
    task_id: UUID,
    step_number: int,
    description: str,
    tool_called: str = None,
    tool_result: dict = None
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

async def process_task(task_id: UUID):
    """
    Background worker function that processes a task end-to-end:
    - If task_type == 'cross_doc_query': dispatches to 2-step cross-document synthesis (run_cross_doc_query)
    - If task_type in ('doc_gen', 'text_gen', 'code_exec'): dispatches to multi-step Sovereign Agent Loop (run_agent)
    - If task_type == 'ocr': executes local PDF or vision extraction pipeline (qwen2.5vl:7b / pypdf)
    Defensively catches model and execution errors to prevent crashes.
    """
    async with AsyncSessionLocal() as db:
        step_count = 0
        try:
            # 1. Fetch task
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalars().first()
            if not task:
                return

            task_type_str = task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)

            # 2. Cross-document Query path
            if task_type_str == "cross_doc_query":
                await run_cross_doc_query(
                    task_id=task.id,
                    query=task.input_ref
                )
                return

            # 3. Multi-step Agent Loop for doc_gen, text_gen, code_exec
            if task_type_str in ["doc_gen", "text_gen", "code_exec"]:
                await run_agent(
                    task_id=task.id,
                    task_type=task_type_str,
                    input_text=task.input_ref
                )
                return

            # 4. OCR Document Processing (Image or PDF)
            task.status = TaskStatus.running
            task.updated_at = datetime.utcnow()
            await db.commit()

            # Initialize step_count based on existing steps (e.g. from Auto-Router)
            existing_steps_res = await db.execute(select(TaskStep).where(TaskStep.task_id == task.id))
            step_count = len(existing_steps_res.scalars().all())

            choice = route_task(task_type=task_type_str, input_ref=task.input_ref)

            # Locate document file path
            image_path = task.input_ref
            try:
                doc_uuid = UUID(task.input_ref)
                doc_result = await db.execute(select(Document).where(Document.id == doc_uuid))
                doc = doc_result.scalars().first()
                if doc:
                    image_path = doc.storage_path
            except (ValueError, TypeError):
                pass

            # Branch: PDF Processing (Path A: Text Layer, Path B: Scanned Page OCR)
            if is_pdf(image_path):
                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description="Detected PDF document: inspecting text layer and page structure",
                    tool_called="pdf_inspector",
                    tool_result={"file_path": image_path, "is_pdf": True}
                )

                extracted_fields = await process_pdf_document(
                    file_path=image_path,
                    max_pages=10,
                    vision_model=choice.model_name
                )

                step_count += 1
                proc_path = extracted_fields.get("processing_path", "text_extraction")
                page_cnt = extracted_fields.get("page_count", 1)
                doc_type_extracted = extracted_fields.get("document_type", "document")
                trunc_note = " (truncated at 10 pages)" if extracted_fields.get("truncated") else ""

                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Processed PDF via {proc_path} ({page_cnt} page(s), type: '{doc_type_extracted}'){trunc_note}",
                    tool_called=f"pdf_{proc_path}",
                    tool_result=extracted_fields
                )

            # Branch: Standard Image OCR (PNG, JPG, etc.)
            else:
                # Step 1: Classify document type
                doc_type = await classify_document_type(image_path=image_path, model=choice.model_name)
                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Classified document as '{doc_type}'",
                    tool_called="ocr_classify",
                    tool_result={"doc_type": doc_type, "file_path": image_path, "model": choice.model_name}
                )

                # Step 2: Extract structured fields for classified type
                extracted_fields = await extract_structured_fields(
                    image_path=image_path,
                    doc_type=doc_type,
                    model=choice.model_name
                )
                step_count += 1
                await log_step(
                    db=db,
                    task_id=task.id,
                    step_number=step_count,
                    description=f"Extracted structured fields for {doc_type}",
                    tool_called="ocr_extract_fields",
                    tool_result=extracted_fields
                )

            # Save structured output to file and update task
            output_content = json.dumps(extracted_fields, indent=2)
            task_storage_dir = os.path.join(STORAGE_DIR, str(task.id))
            os.makedirs(task_storage_dir, exist_ok=True)
            output_file_path = os.path.join(task_storage_dir, "output.txt")
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(output_content)
            output_json_path = os.path.join(task_storage_dir, "output.json")
            with open(output_json_path, "w", encoding="utf-8") as f:
                f.write(output_content)

            task.output_ref = output_content
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
                step_desc = "Vision model execution timed out"
                tool_name = "task_guardrail"
                friendly_output = f"Execution timed out: {err_msg}"
            else:
                step_desc = f"Execution error: {err_msg}"
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
                print(f"Failed to record task failure: {inner_e}")
