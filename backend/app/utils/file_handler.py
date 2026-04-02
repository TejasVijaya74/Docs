import os
import uuid
import logging
from pathlib import Path

import aiofiles
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/tmp/doc_analysis_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}

MAX_FILE_SIZE_MB = 20


async def save_upload(file: UploadFile) -> Path:
    content_type = file.content_type or ""
    extension = ALLOWED_EXTENSIONS.get(content_type)

    if not extension:
        ext_from_name = Path(file.filename or "").suffix.lower()
        ext_map = {".pdf": ".pdf", ".docx": ".docx", ".png": ".png", ".jpg": ".jpg", ".jpeg": ".jpg"}
        extension = ext_map.get(ext_from_name)

    if not extension:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: '{content_type}'. Accepted: PDF, DOCX, PNG, JPG.",
        )

    dest = UPLOAD_DIR / f"{uuid.uuid4()}{extension}"
    size = 0

    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                await out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")
            await out.write(chunk)

    logger.info(f"Saved upload: {dest.name} ({size / 1024:.1f} KB)")
    return dest


def cleanup(path: Path):
    try:
        path.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Failed to delete temp file {path}: {e}")

async def save_upload_from_spooled(file) -> Path:
    content_type = getattr(file, "content_type", "") or ""
    filename = getattr(file, "filename", "") or ""
    
    extension = ALLOWED_EXTENSIONS.get(content_type)
    if not extension:
        ext_from_name = Path(filename).suffix.lower()
        ext_map = {".pdf": ".pdf", ".docx": ".docx", ".png": ".png", ".jpg": ".jpg", ".jpeg": ".jpg"}
        extension = ext_map.get(ext_from_name, ".bin")

    dest = UPLOAD_DIR / f"{uuid.uuid4()}{extension}"
    
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)

    logger.info(f"Saved upload: {dest.name}")
    return dest