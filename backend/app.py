from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict
import uuid
from datetime import datetime
import asyncio

from config import Config
from models import AskRequest, AskResponse, UploadResponse, ExtractResponse, HealthResponse
from document_processor import DocumentProcessor
from rag_engine import RAGEngine
from extractor import StructuredExtractor

# Initialize FastAPI app
app = FastAPI(
    title="Ultra Doc-Intelligence",
    description="AI-powered logistics document understanding system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
doc_processor = DocumentProcessor()
rag_engine = RAGEngine()
extractor = StructuredExtractor()

# Store sessions (in production, use Redis or database)
sessions: Dict[str, Dict] = {}

@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a logistics document"""
    
    # Validate file size
    content = await file.read()
    if len(content) > Config.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Validate file type
    file_extension = None
    for ext in Config.ALLOWED_EXTENSIONS:
        if file.filename.lower().endswith(ext):
            file_extension = ext
            break
    
    if not file_extension:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {Config.ALLOWED_EXTENSIONS}")
    
    try:
        session_id = str(uuid.uuid4())
        
        # Process document
        chunks = doc_processor.process_document(content, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not process document")
        
        # Create vector store
        vectorstore = rag_engine.create_vectorstore(chunks, session_id)
        
        # Store session
        sessions[session_id] = {
            "filename": file.filename,
            "chunks": chunks,
            "created_at": datetime.now(),
            "vectorstore": vectorstore
        }
        
        return UploadResponse(
            session_id=session_id,
            filename=file.filename,
            chunks_count=len(chunks),
            message="Document uploaded and processed successfully",
            timestamp=datetime.now()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/upload-stream")
async def upload_document_stream(file: UploadFile = File(...)):
    """Upload large documents using streaming"""
    
    import tempfile
    import aiofiles
    import os
    
    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
        tmp_path = tmp_file.name
        
        # Stream file in chunks
        total_size = 0
        chunk_number = 0
        
        async with aiofiles.open(tmp_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                
                # Check size limit
                if total_size > Config.MAX_FILE_SIZE:
                    os.unlink(tmp_path)
                    raise HTTPException(status_code=413, detail=f"File too large. Max: {Config.MAX_FILE_SIZE/1024/1024}MB")
                
                await f.write(chunk)
                chunk_number += 1
                
                # Log progress for very large files
                if total_size > 50 * 1024 * 1024 and chunk_number % 10 == 0:
                    print(f"Uploading: {total_size/1024/1024:.1f}MB")
    
    try:
        # Read the temp file
        with open(tmp_path, 'rb') as f:
            content = f.read()
        
        session_id = str(uuid.uuid4())
        
        # Process document
        chunks = doc_processor.process_document(content, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not process document")
        
        # Create vector store
        vectorstore = rag_engine.create_vectorstore(chunks, session_id)
        
        # Store session
        sessions[session_id] = {
            "filename": file.filename,
            "chunks": chunks,
            "created_at": datetime.now(),
            "vectorstore": vectorstore,
            "file_size_mb": total_size / 1024 / 1024
        }
        
        return UploadResponse(
            session_id=session_id,
            filename=file.filename,
            chunks_count=len(chunks),
            message=f"Document uploaded ({(total_size/1024/1024):.1f}MB) and processed into {len(chunks)} chunks",
            timestamp=datetime.now()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question about the uploaded document"""
    
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a document first.")
    
    try:
        # Retrieve relevant chunks
        retrieved_docs = rag_engine.retrieve(request.session_id, request.question)
        
        # Generate answer with guardrails
        result = rag_engine.generate_answer(request.question, retrieved_docs)
        
        return AskResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question answering failed: {str(e)}")

@app.post("/extract", response_model=ExtractResponse)
async def extract_structured_data(session_id: str):
    """Extract structured shipment data from the document"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a document first.")
    
    try:
        session = sessions[session_id]
        
        # Extract structured data
        extracted = extractor.extract_shipment_data(session["chunks"])
        
        return ExtractResponse(**extracted)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session"""
    
    if session_id in sessions:
        rag_engine.clear_session(session_id)
        del sessions[session_id]
        return {"message": "Session cleared successfully"}
    
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    
    return {
        "active_sessions": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "filename": data["filename"],
                "created_at": data["created_at"].isoformat(),
                "chunks_count": len(data["chunks"])
            }
            for sid, data in sessions.items()
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
