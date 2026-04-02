import logging
import re
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SPACY_MODEL = "en_core_web_sm"

LABEL_MAP = {
    "PERSON": "persons",
    "PER": "persons",
    "ORG": "organizations",
    "DATE": "dates",
    "TIME": "dates",
    "MONEY": "monetary_values",
    "GPE": "locations",
    "LOC": "locations",
    "FAC": "locations",
}

MONEY_PATTERN = re.compile(
    r"""
    (?:
        [\$\€\£\¥\₹\₩\₪\₺R\฿][\s]?\d[\d,\.]*(?:\s?(?:million|billion|trillion|thousand|M|B|K|T))?
        |
        \d[\d,\.]*[\s]?(?:USD|EUR|GBP|JPY|INR|CAD|AUD|CHF|CNY|HKD|dollars?|euros?|pounds?|rupees?|yen)
        |
        \d[\d,\.]+\s?(?:million|billion|trillion)\s?(?:dollars?|euros?|pounds?)?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


class NERService:
    _instance: Optional["NERService"] = None
    _lock = threading.Lock()

    def __init__(self):
        try:
            import spacy
            logger.info(f"Loading spaCy model: {SPACY_MODEL}")
            self._nlp = spacy.load(SPACY_MODEL)
            self._backend = "spacy"
            logger.info("spaCy NER model ready.")
        except Exception as e:
            logger.warning(f"spaCy unavailable ({e}), falling back to HuggingFace NER")
            from transformers import pipeline
            self._pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", aggregation_strategy="simple", device=-1)
            self._backend = "hf"

    @classmethod
    def get_instance(cls) -> "NERService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def extract(self, text: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {
            "persons": [],
            "organizations": [],
            "dates": [],
            "monetary_values": [],
            "locations": [],
        }

        money_hits = [m.group().strip() for m in MONEY_PATTERN.finditer(text)]
        entities["monetary_values"] = _dedupe(money_hits)

        chunk = text[:5000]

        if self._backend == "spacy":
            self._extract_spacy(chunk, entities)
        else:
            self._extract_hf(chunk, entities)

        for key in entities:
            entities[key] = _dedupe(entities[key])

        return entities

    def _extract_spacy(self, text: str, entities: Dict[str, List[str]]):
        doc = self._nlp(text)
        for ent in doc.ents:
            category = LABEL_MAP.get(ent.label_)
            if category:
                clean = ent.text.strip()
                if len(clean) > 1 and not clean.isdigit():
                    entities[category].append(clean)

    def _extract_hf(self, text: str, entities: Dict[str, List[str]]):
        results = self._pipeline(text[:512])
        for item in results:
            label = item.get("entity_group", "").upper()
            category = LABEL_MAP.get(label)
            if category:
                word = item.get("word", "").strip()
                if len(word) > 1:
                    entities[category].append(word)


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        normalized = item.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            result.append(item)
    return result