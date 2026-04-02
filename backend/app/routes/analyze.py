import logging
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.schemas.response import AnalysisResponse
from app.services.extractor import extract_text
from app.services.summarizer import SummarizerService
from app.services.ner import NERService
from app.services.sentiment import SentimentService
from app.utils.file_handler import save_upload, cleanup

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    saved_path: Path | None = None

    try:
        saved_path = await save_upload(file)

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
            filename=file.filename or saved_path.name,
            extracted_text_preview=preview,
            summary=summary,
            entities=entities,
            sentiment=sentiment,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed for '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")

    finally:
        if saved_path:
            cleanup(saved_path)