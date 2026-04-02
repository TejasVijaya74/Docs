import logging
import base64
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.schemas.response import AnalysisResponse
from app.services.extractor import extract_text
from app.services.summarizer import SummarizerService
from app.services.ner import NERService
from app.services.sentiment import SentimentService
from app.utils.file_handler import cleanup, UPLOAD_DIR
import uuid
import aiofiles

logger = logging.getLogger(__name__)
router = APIRouter()


async def save_bytes(data: bytes, extension: str) -> Path:
    dest = UPLOAD_DIR / f"{uuid.uuid4()}{extension}"
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)
    return dest


def guess_extension(filename: str = "", content_type: str = "") -> str:
    ext_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
    }
    if content_type in ext_map:
        return ext_map[content_type]
    suffix = Path(filename).suffix.lower()
    return {".pdf": ".pdf", ".docx": ".docx", ".png": ".png", ".jpg": ".jpg", ".jpeg": ".jpg"}.get(suffix, ".pdf")


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(request: Request):
    saved_path: Path | None = None
    filename = "document"

    try:
        content_type = request.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            form = await request.form()
            file = None
            for key in form:
                value = form[key]
                if hasattr(value, "read"):
                    file = value
                    break
            if file is None:
                raise HTTPException(status_code=422, detail="No file found in multipart form.")
            filename = getattr(file, "filename", "document") or "document"
            ext = guess_extension(filename, getattr(file, "content_type", ""))
            data = await file.read()
            saved_path = await save_bytes(data, ext)

        elif "application/json" in content_type:
            body = await request.json()
            logger.info(f"JSON body keys: {list(body.keys())}")

            # Handle evaluator format: fileName, fileType, fileBase64
            file_b64 = body.get("fileBase64") or body.get("file")
            filename = body.get("fileName") or body.get("filename", "document.pdf")
            file_type = body.get("fileType", "")

            if file_b64:
                try:
                    data = base64.b64decode(file_b64)
                    ext = guess_extension(filename, file_type)
                    saved_path = await save_bytes(data, ext)
                    logger.info(f"Decoded base64 file: {filename}, size: {len(data)} bytes")
                except Exception as e:
                    logger.error(f"Base64 decode failed: {e}")
                    raise HTTPException(status_code=422, detail=f"Failed to decode base64 file: {e}")
            else:
                raise HTTPException(status_code=422, detail="JSON body must contain 'fileBase64' or 'file'.")

        else:
            data = await request.body()
            if not data:
                raise HTTPException(status_code=422, detail="Empty request body.")
            ext = guess_extension(content_type=content_type)
            saved_path = await save_bytes(data, ext)

        text = await run_in_threadpool(extract_text, saved_path)

        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=422, detail="Could not extract readable text from the document.")

        summarizer = SummarizerService.get_instance()
        ner_service = NERService.get_instance()
        sentiment_service = SentimentService.get_instance()

        summary = await run_in_threadpool(summarizer.summarize, text)
        entities = await run_in_threadpool(ner_service.extract, text)
        sentiment = await run_in_threadpool(sentiment_service.analyze, text)

        preview = text[:500].replace("\n", " ").strip()
        if len(text) > 500:
            preview += "..."

        logger.info(f"Analysis complete for '{filename}' | sentiment={sentiment}")

        return AnalysisResponse(
            fileName=filename,
            extracted_text_preview=preview,
            summary=summary,
            entities=entities,
            sentiment=sentiment,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")

    finally:
        if saved_path:
            cleanup(saved_path)
