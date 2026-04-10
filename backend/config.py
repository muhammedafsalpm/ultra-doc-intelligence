import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings"""
    
    # Chunking configuration
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    
    # Retrieval configuration
    TOP_K = 3
    SIMILARITY_THRESHOLD = 0.65  # Guardrail threshold
    
    # Confidence scoring weights
    CONFIDENCE_WEIGHTS = {
        'similarity': 0.4,
        'agreement': 0.3,
        'llm_certainty': 0.3
    }
    
    # Extraction patterns
    EXTRACTION_PATTERNS: Dict[str, list] = {
        'rate': [r'Rate:?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', r'Amount:?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)'],
        'weight': [r'Weight:?\s*(\d+(?:,\d{3})*)\s*(?:lbs|pounds|kg)'],
        'shipment_id': [r'Shipment\s*ID:?\s*([A-Z0-9-]+)', r'REF\s*#:?\s*([A-Z0-9-]+)']
    }
    
    # Guardrail settings
    MIN_CONFIDENCE_FOR_ANSWER = 0.4
    HALLUCINATION_CHECK = True
    
    # File settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    
    # Model settings
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    
    # LLM Settings
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi')
    
    @classmethod
    def get_confidence_weights(cls) -> Dict[str, float]:
        return cls.CONFIDENCE_WEIGHTS
