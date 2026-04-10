import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import faiss
from config import Config
from llm_client import LLMClient

class RAGEngine:
    def __init__(self):
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.llm_client = LLMClient()
        self.indexes = {}
        self.chunks_store = {}
    
    def create_vectorstore(self, chunks: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings.astype('float32'))
        
        self.indexes[session_id] = index
        self.chunks_store[session_id] = chunks
        
        return {
            'session_id': session_id,
            'num_chunks': len(chunks),
            'dimension': dimension
        }
    
    def retrieve(self, session_id: str, query: str, k: int = None) -> List[Dict[str, Any]]:
        if k is None:
            k = Config.TOP_K
        
        if session_id not in self.indexes:
            return []
        
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        scores, indices = self.indexes[session_id].search(query_embedding.astype('float32'), k)
        
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
        """Generate answer using LLM with guardrails"""
        
        # Check for greetings first
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you']
        is_greeting = any(greeting in question.lower() for greeting in greetings)
        
        if is_greeting:
            return {
                'answer': "Hello! I'm your logistics document assistant. You can ask me questions about carrier rates, pickup schedules, consignee information, and more. Please upload a document and ask away!",
                'sources': [],
                'confidence_score': 1.0,
                'grounded': True,
                'retrieval_scores': []
            }
        
        if not retrieved_docs:
            return {
                'answer': "No relevant information found in the document. Please try a different question.",
                'sources': [],
                'confidence_score': 0.0,
                'grounded': False,
                'retrieval_scores': []
            }
        
        max_similarity = max([doc['score'] for doc in retrieved_docs])
        if max_similarity < Config.SIMILARITY_THRESHOLD:
            return {
                'answer': "The document doesn't contain information closely matching your question. Please rephrase or ask about different topics.",
                'sources': [doc['text'][:200] + "..." for doc in retrieved_docs[:2]],
                'confidence_score': max_similarity * 0.5,
                'grounded': False,
                'retrieval_scores': [doc['score'] for doc in retrieved_docs]
            }
        
        context = "\n\n---\n\n".join([doc['text'] for doc in retrieved_docs])
        llm_result = self.llm_client.generate_answer(question, context)
        
        confidence_score = self._calculate_confidence_with_llm(
            retrieved_docs, 
            llm_result.get('certainty', 0.7),
            llm_result.get('found_in_context', True)
        )
        
        if confidence_score < Config.MIN_CONFIDENCE_FOR_ANSWER:
            return {
                'answer': "I'm not confident enough to answer this question accurately. Please rephrase or check if the information exists in the document.",
                'sources': [doc['text'][:200] + "..." for doc in retrieved_docs[:2]],
                'confidence_score': confidence_score,
                'grounded': False,
                'retrieval_scores': [doc['score'] for doc in retrieved_docs]
            }
        
        sources = []
        for doc in retrieved_docs[:2]:
            source_text = doc['text'][:300]
            if len(doc['text']) > 300:
                source_text += "..."
            sources.append(source_text)
        
        return {
            'answer': llm_result['answer'],
            'sources': sources,
            'confidence_score': confidence_score,
            'grounded': confidence_score >= 0.6,
            'retrieval_scores': [doc['score'] for doc in retrieved_docs]
        }
    
    def _calculate_confidence_with_llm(self, retrieved_docs: List[Dict], llm_certainty: float, found: bool) -> float:
        if not found:
            return 0.2
        
        similarity_scores = [doc['score'] for doc in retrieved_docs]
        avg_similarity = np.mean(similarity_scores)
        
        if len(similarity_scores) > 1:
            variance = np.var(similarity_scores)
            agreement_score = 1.0 - min(variance, 0.5)
        else:
            agreement_score = 0.5
        
        weights = Config.get_confidence_weights()
        confidence = (
            weights['similarity'] * avg_similarity +
            weights['agreement'] * agreement_score +
            weights.get('llm_certainty', 0.3) * llm_certainty
        )
        
        return max(0.0, min(1.0, confidence))
    
    def clear_session(self, session_id: str):
        if session_id in self.indexes:
            del self.indexes[session_id]
        if session_id in self.chunks_store:
            del self.chunks_store[session_id]
