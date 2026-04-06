from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class AskRequest(BaseModel):
    session_id: str
    question: str = Field(..., min_length=1, max_length=500)

class AskResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    grounded: bool
    retrieval_scores: Optional[List[float]] = None

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    chunks_count: int
    message: str
    timestamp: datetime

class ExtractResponse(BaseModel):
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    extraction_method: str = "llm_based"

class DocumentChunk(BaseModel):
    text: str
    index: int
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
