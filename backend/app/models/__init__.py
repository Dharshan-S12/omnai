import enum
import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Float, JSON, Uuid, Boolean
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
    pending_approval = "pending_approval"
    rejected = "rejected"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    input_ref = Column(String, nullable=False)
    output_ref = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
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

class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    source_task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)
    entity_key = Column(String, nullable=False, index=True)
    summary_text = Column(String, nullable=False)
    embedding_id = Column(String, nullable=True)
    strength_score = Column(Float, default=1.0, nullable=False)
    safety_critical = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    access_count = Column(Integer, default=0, nullable=False)
    superseded_by = Column(Uuid, ForeignKey("memory_entries.id"), nullable=True)

class MemoryLink(Base):
    __tablename__ = "memory_links"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    source_memory_id = Column(Uuid, ForeignKey("memory_entries.id"), nullable=False)
    target_memory_id = Column(Uuid, ForeignKey("memory_entries.id"), nullable=False)
    relation_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EquipmentNode(Base):
    __tablename__ = "equipment_nodes"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_id = Column(String, unique=True, nullable=False, index=True)
    equipment_name = Column(String, nullable=True)
    unit = Column(String, nullable=True, index=True)
    equipment_type = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EquipmentEvent(Base):
    __tablename__ = "equipment_events"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_node_id = Column(Uuid, ForeignKey("equipment_nodes.id"), nullable=False, index=True)
    source_task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

