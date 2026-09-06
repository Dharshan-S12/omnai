from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from app.models import TaskType, TaskStatus

class TaskStepBase(BaseModel):
    step_number: int
    description: str
    tool_called: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None

class TaskStepCreate(TaskStepBase):
    task_id: UUID

class TaskStep(TaskStepBase):
    id: UUID
    task_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    task_type: TaskType
    input_ref: str
    source_task_id: Optional[UUID] = None
    confidence_score: Optional[float] = None

class TaskCreate(TaskBase):
    pass

class AutoTaskCreate(BaseModel):
    prompt: str
    file_path: Optional[str] = None
    source_task_id: Optional[UUID] = None
    confirmed_intent: Optional[str] = None

class DisambiguationOption(BaseModel):
    task_type: str
    label: str
    description: str
    model_name: str

class DisambiguationResponse(BaseModel):
    is_disambiguation: bool = True
    prompt: str
    file_path: Optional[str] = None
    confidence: float
    message: str
    options: List[DisambiguationOption]
    suggested_task_type: str

class TaskApprovalRequest(BaseModel):
    approved: bool
    reviewer_notes: Optional[str] = None
    reviewer_name: Optional[str] = "Supervisor"

class Task(TaskBase):
    id: UUID
    status: TaskStatus
    output_ref: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskWithSteps(Task):
    steps: List[TaskStep] = []

class DocumentBase(BaseModel):
    filename: str
    filetype: str
    storage_path: str

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: UUID
    uploaded_at: datetime
    task_id: Optional[UUID] = None

    class Config:
        from_attributes = True

# Audit Hash Chain Schemas
class AuditEntrySchema(BaseModel):
    id: UUID
    sequence_number: int
    task_id: UUID
    reviewer_name: str
    decision: str
    reviewer_notes: Optional[str] = None
    document_sha256: Optional[str] = None
    timestamp: str
    prev_hash: str
    current_hash: str

class AuditVerifyResponse(BaseModel):
    verified: bool
    total_records: int
    latest_hash: Optional[str] = None
    tampered_sequence: Optional[int] = None
    error_message: Optional[str] = None
    checked_at: str

# Router Decision Schema
class RouterDecisionSchema(BaseModel):
    id: str
    prompt: str
    chosen_intent: str
    confidence: float
    routing_reason: str
    was_disambiguated: bool
    confirmed_by_user: bool
    timestamp: str
