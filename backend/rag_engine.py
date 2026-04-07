import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import faiss
from .config import Config

class RAGEngine:
    def __init__(self):
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.indexes = {}  # Store FAISS indexes per session
        self.chunks_store = {}  # Store chunks per session
    
    def create_vectorstore(self, chunks: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """Create FAISS vector store from chunks"""
        
        # Extract texts
        texts = [chunk['text'] for chunk in chunks]
        
        # Create embeddings
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        
        # Normalize embeddings for cosine similarity
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product (cosine for normalized vectors)
        index.add(embeddings.astype('float32'))
        
        # Store
        self.indexes[session_id] = index
        self.chunks_store[session_id] = chunks
        
        return {
            'session_id': session_id,
            'num_chunks': len(chunks),
            'dimension': dimension
        }
    
    def retrieve(self, session_id: str, query: str, k: int = None) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks with similarity scores"""
        
        if k is None:
            k = Config.TOP_K
        
        if session_id not in self.indexes:
            return []
        
        # Encode query
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search in FAISS
        scores, indices = self.indexes[session_id].search(query_embedding.astype('float32'), k)
        
        # Get chunks with scores
        retrieved = []
        chunks = self.chunks_store[session_id]
        
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(chunks):
                retrieved.append({
                    'text': chunks[idx]['text'],
                    'score': float(score),
                    'index': int(idx),
                    'metadata': chunks[idx]['metadata']
                })
        
        return retrieved
    
    def generate_answer(self, question: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer with guardrails and confidence scoring"""
        
        if not retrieved_docs:
            return {
                'answer': "No relevant information found in the document. Please try a different question.",
                'sources': [],
                'confidence_score': 0.0,
                'grounded': False,
                'retrieval_scores': []
            }
        
        # Calculate confidence score
        confidence_score, scores = self._calculate_confidence(question, retrieved_docs)
        
        # Guardrail 1: Check similarity threshold
        if max([doc['score'] for doc in retrieved_docs]) < Config.SIMILARITY_THRESHOLD:
            return {
                'answer': "The document doesn't contain information closely matching your question. Please rephrase or ask about different topics.",
                'sources': [doc['text'][:200] + "..." for doc in retrieved_docs[:2]],
                'confidence_score': confidence_score,
                'grounded': False,
                'retrieval_scores': [doc['score'] for doc in retrieved_docs]
            }
        
        # Extract answer from context
        answer = self._extract_answer(question, retrieved_docs)
        
        # Guardrail 2: Check if answer is hallucinated
        if Config.HALLUCINATION_CHECK and self._is_hallucinated(answer, retrieved_docs):
            return {
                'answer': "I found relevant information but cannot provide a confident answer. Please review the document sections below.",
                'sources': [doc['text'][:200] + "..." for doc in retrieved_docs[:2]],
                'confidence_score': confidence_score * 0.5,
                'grounded': False,
                'retrieval_scores': [doc['score'] for doc in retrieved_docs]
            }
        
        # Guardrail 3: Low confidence threshold
        if confidence_score < Config.MIN_CONFIDENCE_FOR_ANSWER:
            return {
                'answer': "I'm not confident enough to answer this question accurately. The information in the document may be incomplete or unclear.",
                'sources': [doc['text'][:200] + "..." for doc in retrieved_docs[:2]],
                'confidence_score': confidence_score,
                'grounded': False,
                'retrieval_scores': [doc['score'] for doc in retrieved_docs]
            }
        
        # Prepare sources for display
        sources = []
        for doc in retrieved_docs[:2]:
            source_text = doc['text'][:300]
            if len(doc['text']) > 300:
                source_text += "..."
            sources.append(source_text)
        
        return {
            'answer': answer,
            'sources': sources,
            'confidence_score': confidence_score,
            'grounded': confidence_score >= 0.6,
            'retrieval_scores': [doc['score'] for doc in retrieved_docs]
        }
    
    def _calculate_confidence(self, question: str, retrieved_docs: List[Dict[str, Any]]) -> Tuple[float, List[float]]:
        """Calculate confidence score using multiple factors"""
        
        if not retrieved_docs:
            return 0.0, []
        
        # Factor 1: Retrieval similarity scores
        similarity_scores = [doc['score'] for doc in retrieved_docs]
        avg_similarity = np.mean(similarity_scores)
        
        # Factor 2: Chunk agreement (how consistent are the top chunks?)
        if len(similarity_scores) > 1:
            # Lower variance means better agreement
            variance = np.var(similarity_scores)
            agreement_score = 1.0 - min(variance, 1.0)
        else:
            agreement_score = 0.5
        
        # Factor 3: Answer coverage (will be calculated in answer extraction)
        coverage_score = 0.7  # Default, updated during answer extraction
        
        # Combine with weights
        weights = Config.get_confidence_weights()
        confidence = (
            weights['similarity'] * avg_similarity +
            weights['agreement'] * agreement_score +
            weights['coverage'] * coverage_score
        )
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence, similarity_scores
    
    def _extract_answer(self, question: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Extract answer from retrieved chunks without external LLM"""
        
        # Combine context
        context = "\n".join([doc['text'] for doc in retrieved_docs])
        question_lower = question.lower()
        
        # Define field patterns
        field_patterns = {
            'rate': ['rate', 'cost', 'price', 'charge', 'amount', 'total'],
            'pickup': ['pickup', 'pick up', 'collection', 'load date', 'origin date'],
            'delivery': ['delivery', 'deliver', 'destination', 'drop', 'delivery date'],
            'carrier': ['carrier', 'carrier name', 'transport', 'trucking company'],
            'consignee': ['consignee', 'receiver', 'recipient', 'deliver to'],
            'shipper': ['shipper', 'sender', 'shipping from', 'origin'],
            'equipment': ['equipment', 'trailer', 'truck', 'container', '53ft', '48ft'],
            'weight': ['weight', 'lbs', 'kg', 'pounds', 'gross weight'],
            'date': ['date', 'scheduled', 'when', 'datetime', 'pickup date', 'delivery date']
        }
        
        # Find which field is being asked about
        target_field = None
        for field, keywords in field_patterns.items():
            if any(keyword in question_lower for keyword in keywords):
                target_field = field
                break
        
        if target_field:
            # Try to extract specific field
            lines = context.split('\n')
            for line in lines:
                line_lower = line.lower()
                for keyword in field_patterns[target_field]:
                    if keyword in line_lower:
                        # Found relevant line
                        cleaned_line = line.strip()
                        if len(cleaned_line) > 100:
                            cleaned_line = cleaned_line[:100] + "..."
                        return f"According to the document: {cleaned_line}"
        
        # If no specific field found, return most relevant sentence
        sentences = context.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 20 and any(word in sentence.lower() for word in question_lower.split()[:3]):
                return sentence.strip() + "."
        
        # Fallback: return first relevant chunk
        if retrieved_docs:
            preview = retrieved_docs[0]['text'][:200]
            return f"Based on the document: {preview}..."
        
        return "Information found but couldn't extract specific answer. Please check the sources below."
    
    def _is_hallucinated(self, answer: str, retrieved_docs: List[Dict[str, Any]]) -> bool:
        """Check if answer might be hallucinated"""
        
        # Check for uncertainty indicators
        uncertainty_words = ['probably', 'maybe', 'perhaps', 'could be', 'might be', 'not sure']
        if any(word in answer.lower() for word in uncertainty_words):
            return True
        
        # Check if answer content exists in retrieved docs
        context = " ".join([doc['text'].lower() for doc in retrieved_docs])
        answer_words = set(answer.lower().split())
        context_words = set(context.split())
        
        # Calculate overlap
        if len(answer_words) > 0:
            overlap = len(answer_words & context_words)
            overlap_ratio = overlap / len(answer_words)
            
            # If less than 30% overlap, likely hallucinated
            if overlap_ratio < 0.3:
                return True
        
        return False
    
    def clear_session(self, session_id: str):
        """Clear session data"""
        if session_id in self.indexes:
            del self.indexes[session_id]
        if session_id in self.chunks_store:
            del self.chunks_store[session_id]
