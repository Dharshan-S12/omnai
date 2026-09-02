import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Document
from app.schemas import Document as DocumentSchema

router = APIRouter(prefix="/files", tags=["files"])

STORAGE_DIR = "./storage"

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_id = uuid.uuid4()
    file_dir = os.path.join(STORAGE_DIR, str(file_id))
    os.makedirs(file_dir, exist_ok=True)
    
    file_path = os.path.join(file_dir, file.filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db_document = Document(
        id=file_id,
        filename=file.filename,
        filetype=file.content_type or "application/octet-stream",
        storage_path=file_path
    )
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    return {
        "id": str(db_document.id),
        "filename": db_document.filename,
        "storage_path": db_document.storage_path
    }
