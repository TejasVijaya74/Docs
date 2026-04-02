import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
CONFIDENCE_THRESHOLD = 0.65
MAX_CHARS = 512


class SentimentService:
    _instance: Optional["SentimentService"] = None
    _lock = threading.Lock()

    def __init__(self):
        from transformers import pipeline
        logger.info(f"Loading sentiment model: {MODEL_NAME}")
        self._pipeline = pipeline(
            "sentiment-analysis",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=-1,
            truncation=True,
            max_length=512,
        )
        logger.info("Sentiment model ready.")

    @classmethod
    def get_instance(cls) -> "SentimentService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def analyze(self, text: str) -> str:
        sample = self._representative_sample(text)
        result = self._pipeline(sample)[0]

        label = result["label"].lower()
        score = result["score"]

        if score < CONFIDENCE_THRESHOLD:
            return "neutral"

        if label == "positive":
            return "positive"
        elif label == "negative":
            return "negative"
        return "neutral"

    def _representative_sample(self, text: str) -> str:
        words = text.split()
        if len(words) <= 100:
            return text[:MAX_CHARS]
        first = " ".join(words[:50])
        last = " ".join(words[-50:])
        combined = f"{first} {last}"
        return combined[:MAX_CHARS]