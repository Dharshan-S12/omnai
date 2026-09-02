import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, engine, Base
from app.models import Task, TaskStep, TaskType, TaskStatus
import json

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Create a mock OCR task
        task1 = Task(
            id=uuid.uuid4(),
            task_type=TaskType.ocr,
            status=TaskStatus.done,
            input_ref="doc_1234.pdf",
            output_ref="Extracted text: Machine specs..."
        )
        db.add(task1)
        
        step1_1 = TaskStep(
            task_id=task1.id,
            step_number=1,
            description="Extracting text from PDF",
            tool_called="pdf_parser",
            tool_result={"pages": 5, "status": "success"}
        )
        step1_2 = TaskStep(
            task_id=task1.id,
            step_number=2,
            description="Performing OCR on images",
            tool_called="tesseract_ocr",
            tool_result={"confidence": 0.98}
        )
        db.add_all([step1_1, step1_2])

        # Create a mock Code Execution task
        task2 = Task(
            id=uuid.uuid4(),
            task_type=TaskType.code_exec,
            status=TaskStatus.running,
            input_ref="Analyze sales data",
            output_ref=None
        )
        db.add(task2)
        
        step2_1 = TaskStep(
            task_id=task2.id,
            step_number=1,
            description="Writing python script",
            tool_called="write_file",
            tool_result={"file": "analysis.py"}
        )
        db.add(step2_1)

        await db.commit()
        print("Database seeded with mock tasks!")

if __name__ == "__main__":
    asyncio.run(seed_data())
