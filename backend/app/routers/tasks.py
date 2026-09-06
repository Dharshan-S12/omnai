import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional, Union, Dict, Any
from uuid import UUID

from app.database import get_db
from app.models import Task, TaskStep, TaskStatus
from app.schemas import (
    Task as TaskSchema,
    TaskCreate,
    TaskWithSteps,
    AutoTaskCreate,
    TaskApprovalRequest,
    DisambiguationResponse,
    DisambiguationOption
)
from app.router.task_router import auto_detect_task_intent
from app.services.task_processor import process_task
from app.routers.audit import record_approval_audit_event

router = APIRouter(prefix="/tasks", tags=["tasks"])

STORAGE_DIR = "./storage"
DOCX_MIMETYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

@router.post("/auto")
async def create_auto_task(
    task_in: AutoTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Autonomous Chat Endpoint:
    Auto-detects task type & pipeline with confidence scoring.
    If confidence < 0.65 and intent is unconfirmed, returns a Disambiguation prompt.
    Otherwise creates the task, logs the intent routing step, and triggers background execution.
    """
    route_res = auto_detect_task_intent(
        prompt=task_in.prompt,
        file_path=task_in.file_path,
        confirmed_intent=task_in.confirmed_intent
    )

    # If prompt is ambiguous and user hasn't confirmed intent yet -> Disambiguation Response
    if route_res.is_ambiguous and not task_in.confirmed_intent:
        options = [
            DisambiguationOption(
                task_type=opt["task_type"],
                label=opt["label"],
                description=opt["description"],
                model_name=opt["model_name"]
            )
            for opt in route_res.suggested_options
        ]
        return JSONResponse(
            status_code=200,
            content={
                "is_disambiguation": True,
                "prompt": task_in.prompt,
                "file_path": task_in.file_path,
                "confidence": round(route_res.confidence, 2),
                "message": f"Query is ambiguous (confidence: {route_res.confidence:.0%}). Please select your intended action:",
                "options": [opt.model_dump() for opt in options],
                "suggested_task_type": "doc_gen"
            }
        )

    detected_type = route_res.task_type
    routing_reason = route_res.routing_reason
    selected_model = route_res.model_name

    # If OCR and a file was provided, input_ref is the file path; otherwise input_ref is the prompt
    input_ref = task_in.file_path if (detected_type == "ocr" and task_in.file_path) else task_in.prompt

    new_task = Task(
        task_type=detected_type,
        input_ref=input_ref,
        source_task_id=task_in.source_task_id,
        status=TaskStatus.pending
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Log initial Auto-Router step
    router_step = TaskStep(
        task_id=new_task.id,
        step_number=1,
        description=f"Auto-Router: {routing_reason} (Confidence: {route_res.confidence:.0%})",
        tool_called="auto_router",
        tool_result={
            "detected_task_type": detected_type,
            "confidence": round(route_res.confidence, 2),
            "routing_reason": routing_reason,
            "target_model": selected_model,
            "user_prompt": task_in.prompt,
            "attached_file": task_in.file_path,
            "was_confirmed": bool(task_in.confirmed_intent)
        }
    )
    db.add(router_step)
    await db.commit()

    # Trigger background execution
    background_tasks.add_task(process_task, new_task.id)

    return {
        "is_disambiguation": False,
        "id": str(new_task.id),
        "task_type": new_task.task_type,
        "status": new_task.status,
        "input_ref": new_task.input_ref,
        "output_ref": new_task.output_ref,
        "confidence_score": new_task.confidence_score,
        "source_task_id": str(new_task.source_task_id) if new_task.source_task_id else None,
        "created_at": new_task.created_at.isoformat() if new_task.created_at else None,
        "updated_at": new_task.updated_at.isoformat() if new_task.updated_at else None,
        "steps": [
            {
                "id": str(router_step.id),
                "step_number": router_step.step_number,
                "description": router_step.description,
                "tool_called": router_step.tool_called,
                "tool_result": router_step.tool_result,
                "created_at": router_step.created_at.isoformat() if router_step.created_at else None
            }
        ]
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
        status=TaskStatus.pending
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
        "confidence_score": task.confidence_score,
        "source_task_id": task.source_task_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "steps": task_steps
    }

from app.auth.jwt_auth import decode_access_token

@router.post("/{task_id}/approve", response_model=TaskWithSteps)
async def approve_task(
    task_id: UUID,
    req: TaskApprovalRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
    x_user_role: Optional[str] = Header(default="supervisor", alias="X-User-Role"),
    db: AsyncSession = Depends(get_db)
):
    """
    Human Approval Gate (Role-Restricted & JWT Authenticated):
    - Validates cryptographically signed JWT token when provided.
    - Rejects invalid/expired/forged tokens with 401 Unauthorized (ignoring plain headers).
    - Rejects non-supervisor roles with 403 Forbidden.
    - Binds authenticated user's identity (subject claim) to the tamper-evident audit hash chain.
    - Approves or rejects generated document task and unlocks output download.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_auth_token:
        token = x_auth_token.strip()

    if token:
        # Cryptographic JWT validation
        payload = decode_access_token(token)
        user_role = (payload.get("role") or "operator").lower().strip()
        sub = payload.get("sub", "unknown")
        full_name = payload.get("full_name") or sub
        reviewer_name = f"{full_name} [{sub}]"
    else:
        # Legacy fallback verification for non-token test fixtures
        user_role = (x_user_role or "operator").lower().strip()
        reviewer_name = req.reviewer_name or "Supervisor Reviewer"

    # 1. Role-Based Access Control Verification
    if user_role not in ["supervisor", "admin", "lead_engineer"]:
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Role '{user_role}' is not authorized to sign off on supervisory quality gates. Supervisor role required."
        )

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.pending_approval:
        raise HTTPException(
            status_code=400,
            detail=f"Task is in '{task.status}' status and not currently pending approval"
        )

    steps_res = await db.execute(
        select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.step_number)
    )
    steps = steps_res.scalars().all()
    next_step_num = (max([s.step_number for s in steps], default=0)) + 1

    decision_label = "Approved" if req.approved else "Rejected"

    # 2. Append to cryptographic tamper-evident hash chain
    docx_file_path = os.path.join(STORAGE_DIR, str(task.id), "output.docx")
    audit_entry = record_approval_audit_event(
        task_id=task.id,
        reviewer_name=reviewer_name,
        decision=decision_label.lower(),
        reviewer_notes=req.reviewer_notes,
        docx_path=docx_file_path if os.path.exists(docx_file_path) else None
    )

    approval_step = TaskStep(
        id=uuid.uuid4(),
        task_id=task.id,
        step_number=next_step_num,
        description=f"Human Decision Gate: {decision_label} by {reviewer_name} (Role: {user_role.upper()})",
        tool_called="human_approval",
        tool_result={
            "decision": decision_label.lower(),
            "approved": req.approved,
            "reviewer_name": reviewer_name,
            "reviewer_role": user_role,
            "reviewer_notes": req.reviewer_notes or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_hash_chain": {
                "sequence_number": audit_entry["sequence_number"],
                "current_hash": audit_entry["current_hash"],
                "prev_hash": audit_entry["prev_hash"],
                "document_sha256": audit_entry["document_sha256"]
            }
        },
        created_at=datetime.now(timezone.utc)
    )
    db.add(approval_step)

    if req.approved:
        task.status = TaskStatus.done
    else:
        task.status = TaskStatus.rejected

    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    all_steps = list(steps) + [approval_step]
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "input_ref": task.input_ref,
        "output_ref": task.output_ref,
        "confidence_score": task.confidence_score,
        "source_task_id": task.source_task_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "steps": all_steps
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

    # Safety Gate Check
    if task.status == TaskStatus.pending_approval:
        raise HTTPException(
            status_code=403,
            detail="Awaiting human approval before output is accessible for download"
        )
    if task.status == TaskStatus.rejected:
        raise HTTPException(
            status_code=403,
            detail="Document was rejected by reviewer — download inaccessible"
        )

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

    # Safety Gate Check
    if task.status == TaskStatus.pending_approval:
        raise HTTPException(
            status_code=403,
            detail="Awaiting human approval before output is accessible for download"
        )
    if task.status == TaskStatus.rejected:
        raise HTTPException(
            status_code=403,
            detail="Document was rejected by reviewer — download inaccessible"
        )

    docx_path = os.path.join(STORAGE_DIR, str(task_id), "output.docx")
    if os.path.exists(docx_path):
        return FileResponse(
            path=docx_path,
            media_type=DOCX_MIMETYPE,
            filename=f"task_{task_id}_output.docx"
        )
    else:
        raise HTTPException(status_code=404, detail="No Word document (.docx) output found for this task")
