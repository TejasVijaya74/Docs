import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "facebook/bart-large-cnn"
MAX_INPUT_TOKENS = 1024
SUMMARY_MIN_LENGTH = 80
SUMMARY_MAX_LENGTH = 200


class SummarizerService:
    _instance: Optional["SummarizerService"] = None
    _lock = threading.Lock()

    def __init__(self):
        from transformers import BartTokenizer, BartForConditionalGeneration
        import torch
        logger.info(f"Loading summarization model: {MODEL_NAME}")
        self._tokenizer = BartTokenizer.from_pretrained(MODEL_NAME)
        self._model = BartForConditionalGeneration.from_pretrained(MODEL_NAME)
        self._model.eval()
        self._torch = torch
        logger.info("Summarization model ready.")

    @classmethod
    def get_instance(cls) -> "SummarizerService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def summarize(self, text: str) -> str:
        words = text.split()
        truncated = " ".join(words[:MAX_INPUT_TOKENS])

        if len(truncated.split()) < 30:
            return truncated.strip()

        inputs = self._tokenizer(
            truncated,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )

        with self._torch.no_grad():
            summary_ids = self._model.generate(
                inputs["input_ids"],
                num_beams=4,
                max_length=SUMMARY_MAX_LENGTH,
                min_length=SUMMARY_MIN_LENGTH,
                early_stopping=True,
                forced_bos_token_id=self._tokenizer.bos_token_id,
            )

        return self._tokenizer.decode(
            summary_ids[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()