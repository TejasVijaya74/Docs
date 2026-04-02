# Document Analysis API

A production-grade REST API that accepts PDF, DOCX, and image documents and returns structured AI-extracted insights: clean text, a concise summary, named entities, and sentiment.

---

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app + lifespan model warm-up
│   ├── routes/
│   │   └── analyze.py       # POST /api/v1/analyze endpoint
│   ├── services/
│   │   ├── extractor.py     # PDF (PyMuPDF + pdfplumber fallback) / DOCX
│   │   ├── ocr.py           # Tesseract OCR for images
│   │   ├── summarizer.py    # facebook/bart-large-cnn (singleton)
│   │   ├── ner.py           # spaCy en_core_web_sm + regex money patterns
│   │   └── sentiment.py     # distilbert-base-uncased-finetuned-sst-2-english
│   ├── utils/
│   │   └── file_handler.py  # Async upload, validation, cleanup
│   └── schemas/
│       └── response.py      # Pydantic response models
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## API Reference

### `POST /api/v1/analyze`

**Request:** `multipart/form-data`

| Field | Type   | Required | Description              |
|-------|--------|----------|--------------------------|
| file  | binary | Yes      | PDF, DOCX, PNG, or JPG   |

**Response:**

```json
{
  "filename": "contract.pdf",
  "extracted_text_preview": "This agreement is made between...",
  "summary": "A legal services agreement between Acme Corp and John Doe dated January 2024, valued at $50,000.",
  "entities": {
    "persons": ["John Doe", "Jane Smith"],
    "organizations": ["Acme Corp"],
    "dates": ["January 1, 2024"],
    "monetary_values": ["$50,000"],
    "locations": ["New York", "California"]
  },
  "sentiment": "neutral"
}
```

**Sentiment values:** `positive` | `negative` | `neutral`

---

## Local Development

### Prerequisites

- Python 3.11+
- Tesseract OCR installed (`brew install tesseract` on macOS, `apt install tesseract-ocr` on Linux)

### Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Docker

### Build & Run

```bash
docker build -t doc-analysis-api .
docker run -p 8000:8000 --memory=4g doc-analysis-api
```

> **Note:** First run downloads ~1.6GB of model weights. The Dockerfile pre-downloads them during build so runtime is instant.

---

## Example Usage

### cURL

```bash
# Analyze a PDF
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@/path/to/document.pdf"

# Analyze a DOCX
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@/path/to/report.docx"

# Analyze an image
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@/path/to/scan.png"
```

### Python

```python
import httpx

with open("document.pdf", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/api/v1/analyze",
        files={"file": ("document.pdf", f, "application/pdf")},
    )

data = response.json()
print(data["summary"])
print(data["entities"])
print(data["sentiment"])
```

---

## Deployment

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

Set env vars in Railway dashboard (none required by default — models are bundled).

### Render

1. Create a new **Web Service** on Render
2. Connect your GitHub repo
3. Set:
   - **Environment:** Docker
   - **Instance:** Standard (2GB RAM minimum, 4GB recommended)
   - **Port:** 8000
4. Deploy

### AWS ECS / Fargate

```bash
# Build and push to ECR
aws ecr create-repository --repository-name doc-analysis-api
docker tag doc-analysis-api:latest <account>.dkr.ecr.<region>.amazonaws.com/doc-analysis-api
docker push <account>.dkr.ecr.<region>.amazonaws.com/doc-analysis-api

# Then create ECS task definition with 4GB memory, 2 vCPU
# and expose port 8000 via an ALB
```

Recommended instance: `t3.medium` or Fargate with 4GB memory.

---

## Models Used

| Task             | Model                                             | Size   |
|------------------|---------------------------------------------------|--------|
| Summarization    | `facebook/bart-large-cnn`                        | ~1.6GB |
| Named Entity Rec | `spacy en_core_web_sm`                           | ~12MB  |
| Sentiment        | `distilbert-base-uncased-finetuned-sst-2-english`| ~268MB |

---

## Design Decisions

- **Singleton model loading:** All three AI models are loaded once at startup via the `lifespan` hook and held in memory. Eliminates per-request cold-start latency.
- **Async I/O + threadpool offload:** File I/O is fully async; blocking CPU-bound inference is offloaded to a thread pool via `run_in_threadpool`, keeping the event loop free.
- **Dual PDF backend:** PyMuPDF is tried first for speed and layout fidelity. pdfplumber is the fallback for complex PDFs.
- **Regex-augmented money NER:** spaCy's MONEY entity recall is improved with a custom regex that catches currency symbols, abbreviations (USD, EUR), and verbal amounts (5 million dollars).
- **Confidence-gated sentiment:** Results below 65% confidence are returned as `neutral` to avoid misleading low-confidence classifications.