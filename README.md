# Ultra Doc-Intelligence

An AI-powered logistics document understanding system that allows users to upload documents (Rate Confirmations, BOLs, Shipment Instructions, Invoices) and interact with them using natural language questions.

## 🎯 Features

- **Document Processing**: Upload PDF, DOCX, or TXT files (up to 100 MB) - automatic text extraction and intelligent chunking
- **RAG-based Q&A**: Ask natural language questions, get answers grounded in the document with source snippets
- **Guardrails**: Three layers of protection against hallucinations:
  - Similarity threshold filtering
  - Context-only answering with "not found" detection
  - Confidence-based refusal
- **Confidence Scoring**: Composite score based on retrieval similarity, chunk agreement, and LLM certainty
- **Structured Extraction**: Extract 11 key shipment fields as JSON
- **Choice of LLM**: OpenAI or a local model through Ollama
- **Lightweight UI**: Clean, responsive interface for document upload, Q&A, and extraction

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (HTML/CSS/JS)              │
├─────────────────────────────────────────────────────────────┤
│                      API Layer (FastAPI)                    │
├──────────────┬──────────────┬──────────────┬───────────────┤
│   Document   │    RAG       │  Structured  │   Guardrails  │
│   Processor  │   Engine     │  Extractor   │   & Scoring   │
├──────────────┴──────────────┴──────────────┴───────────────┤
│        Vector Store (FAISS)   ·   LLM (OpenAI / Ollama)     │
│                  Embeddings (Sentence-BERT)                 │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Chunking Strategy

**Intelligent Semantic Chunking:**
- Primary split by logical sections (double newlines)
- Recursive character splitting for long sections
- Chunk size: 500 characters, overlap: 50 (800 / 100 for documents over 50,000 characters)
- Preserves semantic boundaries and context

## 🔍 Retrieval Method

- **Model**: `all-MiniLM-L6-v2` (384-dim embeddings)
- **Index**: FAISS with cosine similarity (normalized vectors)
- **k**: Top 3 most relevant chunks
- **Similarity Threshold**: 0.65 (guardrail)

## 🛡 Guardrails Approach

Three-layer protection system:

1. **Retrieval Similarity Threshold**
   - Rejects questions where the best chunk's similarity is below 0.65
   - Returns a "not found in the document" style response without calling the LLM

2. **Context-Only Answering**
   - The LLM is instructed to answer only from the retrieved chunks
   - If it replies "Not found in document", the answer is marked as not found and its confidence drops to 0.2

3. **Confidence-Based Refusal**
   - Minimum confidence threshold: 0.4
   - Below it, the system declines to answer instead of guessing
   - Answers with confidence of 0.6 or higher are marked `grounded: true`

## 📈 Confidence Scoring Method

Composite score using three factors:

```
Confidence = (0.4 × similarity_score) +
             (0.3 × chunk_agreement) +
             (0.3 × llm_certainty)
```

- **similarity_score**: Average cosine similarity of the retrieved chunks
- **chunk_agreement**: `1 − variance` of the similarity scores (variance capped at 0.5)
- **llm_certainty**: Fixed per provider (0.85 for OpenAI, 0.75 for Ollama)

Returns a score between 0.0 and 1.0. If the LLM reports the answer is not in the document, the score is set to 0.2.

## 🚀 Installation & Running

### 1. Configure the LLM

Create `backend/.env`:

```env
# openai | ollama
LLM_PROVIDER=ollama

# Used when LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-3.5-turbo

# Used when LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi
```

`.env` is git-ignored, so your API key is never committed. For Ollama, install it from https://ollama.com and pull the model first (`ollama pull phi`).

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/muhammedafsalpm/ultra-doc-intelligence.git
cd ultra-doc-intelligence

# Build and run with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

When Ollama runs on your computer (not in Docker), set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `backend/.env`, because `localhost` inside the container is the container itself.

### Option 2: Local Development

Requires Python 3.10+.

```bash
# Clone repository
git clone https://github.com/muhammedafsalpm/ultra-doc-intelligence.git
cd ultra-doc-intelligence

# Install dependencies
pip install -r backend/requirements.txt

# Start the backend
cd backend
uvicorn app:app --reload --port 8000

# Then open frontend/index.html in your browser
```

## 📡 API Endpoints

Interactive documentation is available at http://localhost:8000/docs.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload and process a document |
| `POST` | `/upload-stream` | Upload a large document in streamed chunks |
| `POST` | `/ask` | Ask a question about an uploaded document |
| `POST` | `/extract?session_id=...` | Extract structured shipment data |
| `GET` | `/sessions` | List active sessions |
| `DELETE` | `/session/{session_id}` | Clear a session |
| `GET` | `/health` | Health check |

### POST /upload
Upload and process a document (multipart form field `file`)
```json
Response: {
  "session_id": "uuid",
  "filename": "document.pdf",
  "chunks_count": 42,
  "message": "Success",
  "timestamp": "2026-01-01T00:00:00"
}
```

### POST /ask
Ask a question about the document
```json
Request: {
  "session_id": "uuid",
  "question": "What is the carrier rate?"
}
Response: {
  "answer": "According to the document: Rate: $1,200",
  "sources": ["context snippet..."],
  "confidence_score": 0.85,
  "grounded": true,
  "retrieval_scores": [0.82, 0.71, 0.66]
}
```

### POST /extract
Extract structured shipment data. The session ID is passed as a query parameter:
```
POST /extract?session_id=uuid
```
```json
Response: {
  "extracted_data": {
    "shipment_id": "SHIP123",
    "shipper": "ABC Logistics",
    "consignee": "XYZ Corp",
    "pickup_datetime": "2026-01-05",
    "delivery_datetime": "2026-01-08",
    "equipment_type": "dry van",
    "mode": "truck",
    "rate": 1200.0,
    "currency": "USD",
    "weight": 42000,
    "carrier_name": "Fast Freight LLC"
  },
  "confidence_scores": {...},
  "extraction_method": "llm_based"
}
```

## ⚠️ Failure Cases & Limitations

### Known Failure Cases

1. **Poor Quality PDFs**
   - Scanned images without OCR
   - Complex tables with merged cells
   - Handwritten text

2. **Ambiguous Information**
   - Multiple rates in document
   - Missing field labels
   - Inconsistent date formats

3. **Context Fragmentation**
   - Information spread across pages
   - Referencing external documents
   - Conditional statements

4. **Extraction Challenges**
   - Non-standard field names
   - Missing/null values in real documents
   - Currency symbols in unexpected places
   - Only the first 2,500 characters are sent to the LLM for extraction, so fields later in long documents can be missed

5. **Sessions Are In Memory**
   - Uploaded documents are lost when the backend restarts

### Mitigation Strategies
- Implement OCR for scanned documents (Tesseract)
- Add table detection and processing
- Use cross-encoder for re-ranking
- Implement feedback loop for improvement

## 🚀 Improvement Ideas

### Short-term (Next Sprint)
- [ ] Add support for multiple documents
- [ ] Implement hybrid search (BM25 + embeddings)
- [ ] Add caching for frequently asked questions
- [ ] Export Q&A history as CSV
- [ ] Add automated tests

### Medium-term (Next Month)
- [ ] Fine-tune extraction model on logistics data
- [ ] Add document comparison feature
- [ ] Implement user feedback collection
- [ ] Add support for Excel/CSV files

### Long-term (Quarter)
- [ ] Multi-modal support (images, scanned docs)
- [ ] Active learning from user corrections
- [ ] Integration with TMS APIs
- [ ] Real-time document monitoring

## 🧪 Testing

Smoke-test the API with `curl` while the backend is running:

```bash
# Health check
curl http://localhost:8000/health

# Upload a document (returns a session_id)
curl -X POST http://localhost:8000/upload -F "file=@sample.pdf"

# Ask a question
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","question":"What is the rate?"}'

# Extract shipment fields
curl -X POST "http://localhost:8000/extract?session_id=<session_id>"
```

## 📁 Project Structure

```
ultra-doc-intelligence/
├── backend/
│   ├── app.py                 # FastAPI main application
│   ├── config.py              # Configuration settings
│   ├── models.py              # Pydantic models
│   ├── document_processor.py  # Parsing & chunking
│   ├── rag_engine.py          # Retrieval, guardrails & confidence scoring
│   ├── llm_client.py          # OpenAI / Ollama client
│   ├── extractor.py           # Structured extraction
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html             # Main UI
│   ├── style.css              # Styling
│   └── script.js              # Frontend logic
├── docker-compose.yml
├── Dockerfile
├── nginx.conf                 # Serves the frontend in Docker
├── run.py                     # Quick start script
├── LICENSE
└── README.md
```

## 🔧 Configuration

### Environment variables (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `openai` or `ollama` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `phi` | Ollama model name |

### Tuning settings (`backend/config.py`)

| Setting | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | 500 | Size of text chunks (characters) |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks |
| `TOP_K` | 3 | Number of chunks to retrieve |
| `SIMILARITY_THRESHOLD` | 0.65 | Minimum similarity for answers |
| `MIN_CONFIDENCE_FOR_ANSWER` | 0.4 | Minimum confidence threshold |
| `MAX_FILE_SIZE` | 100 MB | Largest accepted upload |

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

## 📧 Support

For issues or questions:
- Open GitHub issue
- Check API documentation at `/docs`
- Review failure cases section
