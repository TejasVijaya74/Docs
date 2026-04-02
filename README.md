---
title: Doc Analysis API
emoji: 📄
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# AI-Powered Document Analysis & Extraction API

A production-grade REST API that accepts PDF, DOCX, and image documents and returns structured AI-extracted insights.

## Live URL
```
https://jim5-doc-analysis-api.hf.space/api/v1/analyze
```

## GitHub Repository
```
https://github.com/TejasVijaya74/Docs
```

## API Usage

### Request
```bash
curl -X POST https://jim5-doc-analysis-api.hf.space/api/v1/analyze \
  -H "x-api-key: hackathon-key-2024" \
  -F "file=@document.pdf"
```

### Response
```json
{
  "fileName": "sample1.pdf",
  "extracted_text_preview": "...",
  "summary": "...",
  "entities": {
    "persons": [],
    "organizations": [],
    "dates": [],
    "monetary_values": [],
    "locations": []
  },
  "sentiment": "positive"
}
```

## Architecture
```
backend/
├── app/
│   ├── main.py              # FastAPI app + model warm-up
│   ├── routes/
│   │   └── analyze.py       # POST /api/v1/analyze
│   ├── services/
│   │   ├── extractor.py     # PDF + DOCX extraction
│   │   ├── ocr.py           # Tesseract OCR for images
│   │   ├── summarizer.py    # facebook/bart-large-cnn
│   │   ├── ner.py           # spaCy en_core_web_sm
│   │   └── sentiment.py     # distilbert-sst-2
│   ├── utils/
│   │   └── file_handler.py
│   └── schemas/
│       └── response.py
├── requirements.txt
└── Dockerfile
```

## Tech Stack

- **Framework:** FastAPI
- **OCR:** Tesseract + pytesseract
- **PDF Extraction:** PyMuPDF + pdfplumber
- **DOCX Extraction:** python-docx
- **Summarization:** facebook/bart-large-cnn (HuggingFace)
- **NER:** spaCy en_core_web_sm
- **Sentiment:** distilbert-base-uncased-finetuned-sst-2-english
- **Deployment:** HuggingFace Spaces (Docker)

## Setup Instructions

### Prerequisites
- Python 3.11+
- Tesseract OCR installed

### Local Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Run
```bash
export X_API_KEY=your-secret-key
uvicorn app.main:app --reload --port 8000
```

## AI Tools Used

| Tool | Usage |
|------|-------|
| **Claude (Anthropic)** | System architecture design, deployment guidance |
| **facebook/bart-large-cnn** | Document summarization |
| **distilbert-base-uncased-finetuned-sst-2-english** | Sentiment analysis |
| **spaCy en_core_web_sm** | Named entity recognition |

## Known Limitations

- Free tier HuggingFace Space may sleep after inactivity (30 second wake-up time)
- Image OCR accuracy depends on image quality
- Summarization limited to first 1024 tokens for large documents
- No GPU — inference runs on CPU only
