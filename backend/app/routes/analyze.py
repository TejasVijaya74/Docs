import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.schemas.response import AnalysisResponse
from app.services.extractor import extract_text
from app.services.summarizer import SummarizerService
from app.services.ner import NERService
from app.services.sentiment import SentimentService
from app.utils.file_handler import save_upload_from_spooled, cleanup

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(request: Request):
    saved_path: Path | None = None

    try:
        form = await request.form()

        file = None
        for key in form:
            value = form[key]
            if hasattr(value, "filename") and hasattr(value, "read"):
                file = value
                break

        if file is None:
            raise HTTPException(status_code=422, detail="No file found in request body.")

        saved_path = await save_upload_from_spooled(file)

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

        logger.info(f"Analysis complete for '{file.filename}' | sentiment={sentiment}")

        return AnalysisResponse(
            fileName=file.filename or saved_path.name,
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