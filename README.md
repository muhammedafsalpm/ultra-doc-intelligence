# Ultra Doc-Intelligence

An AI-powered logistics document understanding system that allows users to upload documents (Rate Confirmations, BOLs, Shipment Instructions, Invoices) and interact with them using natural language questions.

## 🎯 Features

- **Document Processing**: Upload PDF, DOCX, or TXT files - automatic text extraction and intelligent chunking
- **RAG-based Q&A**: Ask natural language questions, get grounded answers with source citations
- **Guardrails**: Three layers of protection against hallucinations:
  - Similarity threshold filtering
  - Answer grounding verification  
  - Confidence-based refusal
- **Confidence Scoring**: Composite score based on retrieval similarity, chunk agreement, and answer coverage
- **Structured Extraction**: Extract 11 key shipment fields as JSON
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
│                    Vector Store (FAISS)                     │
│                  Embeddings (Sentence-BERT)                 │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Chunking Strategy

**Intelligent Semantic Chunking**:
- Primary split by logical sections (double newlines)
- Recursive character splitting for long sections
- Chunk size: 500 characters, overlap: 50
- Preserves semantic boundaries and context

## 🔍 Retrieval Method

- **Model**: all-MiniLM-L6-v2 (384-dim embeddings)
- **Index**: FAISS with cosine similarity (normalized vectors)
- **k**: Top 3 most relevant chunks
- **Similarity Threshold**: 0.65 (guardrail)

## 🛡 Guardrails Approach

Three-layer protection system:

1. **Retrieval Similarity Threshold**
   - Rejects queries where max similarity < 0.65
   - Returns "Not found" style response

2. **Hallucination Detection**
   - Checks answer-source overlap (>30% required)
   - Detects uncertainty indicators
   - Flags potential hallucinations

3. **Confidence-Based Refusal**
   - Minimum confidence threshold: 0.4
   - Returns low-confidence response when below threshold

## 📈 Confidence Scoring Method

Composite score using three factors:

```
Confidence = (0.5 × similarity_score) + 
             (0.3 × chunk_agreement) + 
             (0.2 × answer_coverage)
```

- **similarity_score**: Average cosine similarity of retrieved chunks
- **chunk_agreement**: Inverse variance of similarity scores
- **answer_coverage**: Percentage of answer words in source context

Returns score between 0.0 and 1.0.

## 🚀 Installation & Running

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/ultra-doc-intelligence.git
cd ultra-doc-intelligence

# Build and run with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/ultra-doc-intelligence.git
cd ultra-doc-intelligence

# Install dependencies
pip install -r backend/requirements.txt

# Run the application
python run.py

# Or manually:
# Terminal 1: cd backend && uvicorn app:app --reload --port 8000
# Open frontend/index.html in browser
```

## 📡 API Endpoints

### POST `/upload`
Upload and process a document
```json
Response: {
  "session_id": "uuid",
  "filename": "document.pdf",
  "chunks_count": 42,
  "message": "Success",
  "timestamp": "2024-01-01T00:00:00"
}
```

### POST `/ask`
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
  "grounded": true
}
```

### POST `/extract`
Extract structured shipment data
```json
Request: {
  "session_id": "uuid"
}
Response: {
  "extracted_data": {
    "shipment_id": "SHIP123",
    "shipper": "ABC Logistics",
    "consignee": "XYZ Corp",
    ...
  },
  "confidence_scores": {...}
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

### Mitigation Strategies

- Implement OCR for scanned documents (Tesseract)
- Add table detection and processing
- Use cross-encoder for re-ranking
- Implement feedback loop for improvement

## 🚀 Improvement Ideas

### Short-term (Next Sprint)
- Add support for multiple documents
- Implement hybrid search (BM25 + embeddings)
- Add caching for frequently asked questions
- Export Q&A history as CSV

### Medium-term (Next Month)
- Fine-tune extraction model on logistics data
- Add document comparison feature
- Implement user feedback collection
- Add support for Excel/CSV files

### Long-term (Quarter)
- Multi-modal support (images, scanned docs)
- Active learning from user corrections
- Integration with TMS APIs
- Real-time document monitoring

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test API endpoints
curl -X POST http://localhost:8000/upload -F "file=@sample.pdf"
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"session_id":"...","question":"What is the rate?"}'
```

## 📁 Project Structure

```
ultra-doc-intelligence/
├── backend/
│   ├── app.py              # FastAPI main application
│   ├── config.py           # Configuration settings
│   ├── models.py           # Pydantic models
│   ├── document_processor.py  # Parsing & chunking
│   ├── rag_engine.py       # RAG implementation
│   ├── extractor.py        # Structured extraction
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Main UI
│   ├── style.css           # Styling
│   └── script.js           # Frontend logic
├── tests/
│   ├── test_rag.py
│   └── test_extraction.py
├── docker-compose.yml
├── Dockerfile
├── run.py                  # Quick start script
└── README.md
```

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | 500 | Size of text chunks |
| `TOP_K` | 3 | Number of chunks to retrieve |
| `SIMILARITY_THRESHOLD` | 0.65 | Minimum similarity for answers |
| `MIN_CONFIDENCE` | 0.4 | Minimum confidence threshold |

## 📝 License

MIT License - See LICENSE file for details

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