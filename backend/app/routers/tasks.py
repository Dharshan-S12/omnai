import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Task, TaskStep
from app.schemas import Task as TaskSchema, TaskCreate, TaskWithSteps, AutoTaskCreate
from app.router.task_router import auto_detect_task_intent
from app.services.task_processor import process_task

router = APIRouter(prefix="/tasks", tags=["tasks"])

STORAGE_DIR = "./storage"
DOCX_MIMETYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

@router.post("/auto", response_model=TaskWithSteps)
async def create_auto_task(
    task_in: AutoTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Autonomous Chat Endpoint:
    Auto-detects task type & pipeline from the user's prompt or uploaded file,
    creates the task, logs the intent routing step, and triggers background processing.
    """
    detected_type, routing_reason, selected_model = auto_detect_task_intent(
        prompt=task_in.prompt,
        file_path=task_in.file_path
    )

    # If OCR and a file was provided, input_ref is the file path; otherwise input_ref is the prompt
    input_ref = task_in.file_path if (detected_type == "ocr" and task_in.file_path) else task_in.prompt

    new_task = Task(
        task_type=detected_type,
        input_ref=input_ref,
        source_task_id=task_in.source_task_id,
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Log initial Auto-Router step
    router_step = TaskStep(
        task_id=new_task.id,
        step_number=1,
        description=f"Auto-Router: {routing_reason}",
        tool_called="auto_router",
        tool_result={
            "detected_task_type": detected_type,
            "routing_reason": routing_reason,
            "target_model": selected_model,
            "user_prompt": task_in.prompt,
            "attached_file": task_in.file_path
        }
    )
    db.add(router_step)
    await db.commit()

    # Trigger background execution
    background_tasks.add_task(process_task, new_task.id)

    return {
        "id": new_task.id,
        "task_type": new_task.task_type,
        "status": new_task.status,
        "input_ref": new_task.input_ref,
        "output_ref": new_task.output_ref,
        "source_task_id": new_task.source_task_id,
        "created_at": new_task.created_at,
        "updated_at": new_task.updated_at,
        "steps": [router_step]
    }

@router.post("/", response_model=TaskSchema)
async def create_task(
    task_in: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    new_task = Task(
        task_type=task_in.task_type,
        input_ref=task_in.input_ref,
        source_task_id=task_in.source_task_id,
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Trigger async background processing
    background_tasks.add_task(process_task, new_task.id)

    return new_task

@router.get("/", response_model=List[TaskSchema])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(desc(Task.created_at)))
    return result.scalars().all()

@router.get("/{task_id}", response_model=TaskWithSteps)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    steps_result = await db.execute(
        select(TaskStep)
        .where(TaskStep.task_id == task_id)
        .order_by(TaskStep.step_number)
    )
    task_steps = steps_result.scalars().all()
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "input_ref": task.input_ref,
        "output_ref": task.output_ref,
        "source_task_id": task.source_task_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "steps": task_steps
    }

@router.get("/{task_id}/output")
async def get_task_output(
    task_id: UUID,
    format: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # If docx format requested or provided in query
    if format in ["docx", "doc"]:
        docx_path = os.path.join(STORAGE_DIR, str(task_id), "output.docx")
        if os.path.exists(docx_path):
            return FileResponse(
                path=docx_path,
                media_type=DOCX_MIMETYPE,
                filename=f"task_{task_id}_output.docx"
            )
        else:
            raise HTTPException(status_code=404, detail="No Word document (.docx) output found for this task")

    output_path = os.path.join(STORAGE_DIR, str(task_id), "output.txt")
    if os.path.exists(output_path):
        return FileResponse(
            path=output_path,
            media_type="text/plain",
            filename=f"task_{task_id}_output.txt"
        )
    elif task.output_ref:
        return PlainTextResponse(content=task.output_ref)
    else:
        raise HTTPException(status_code=404, detail="No output generated for this task yet")

@router.get("/{task_id}/output/docx")
async def get_task_output_docx(task_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    docx_path = os.path.join(STORAGE_DIR, str(task_id), "output.docx")
    if os.path.exists(docx_path):
        return FileResponse(
            path=docx_path,
            media_type=DOCX_MIMETYPE,
            filename=f"task_{task_id}_output.docx"
        )
    else:
        raise HTTPException(status_code=404, detail="No Word document (.docx) output found for this task")
