import enum
import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, JSON, Uuid
from sqlalchemy.sql import func
from app.database import Base

class TaskType(str, enum.Enum):
    ocr = "ocr"
    text_gen = "text_gen"
    code_exec = "code_exec"
    doc_gen = "doc_gen"
    cross_doc_query = "cross_doc_query"

class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    input_ref = Column(String, nullable=False)
    output_ref = Column(String, nullable=True)
    source_task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TaskStep(Base):
    __tablename__ = "task_steps"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    tool_called = Column(String, nullable=True)
    tool_result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    filetype = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)

