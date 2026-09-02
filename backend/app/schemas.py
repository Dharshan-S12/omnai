from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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

class TaskCreate(TaskBase):
    pass

class AutoTaskCreate(BaseModel):
    prompt: str
    file_path: Optional[str] = None
    source_task_id: Optional[UUID] = None

class Task(TaskBase):
    id: UUID
    status: TaskStatus
    output_ref: Optional[str] = None
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
