import re
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from docx import Document
import io
from config import Config

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len
        )
    
    def process_document(self, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Process uploaded document and return chunks with metadata"""
        
        # Extract text based on file type
        text = self._extract_text(file_content, filename)
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Could not extract sufficient text from document")
        
        # Clean text
        text = self._clean_text(text)
        
        # Intelligent chunking
        chunks = self._intelligent_chunking(text)
        
        # Add metadata to chunks
        chunks_with_metadata = []
        for i, chunk in enumerate(chunks):
            chunks_with_metadata.append({
                'text': chunk,
                'index': i,
                'metadata': {
                    'filename': filename,
                    'chunk_id': i,
                    'total_chunks': len(chunks)
                }
            })
        
        return chunks_with_metadata
    
    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from different file formats"""
        
        if filename.endswith('.pdf'):
            return self._extract_pdf(file_content)
        elif filename.endswith('.docx'):
            return self._extract_docx(file_content)
        elif filename.endswith('.txt'):
            return file_content.decode('utf-8', errors='ignore')
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    
    def _extract_pdf(self, content: bytes) -> str:
        """Extract text from PDF with better table handling"""
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            raise Exception(f"PDF parsing failed: {str(e)}")
    
    def _extract_docx(self, content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            doc_file = io.BytesIO(content)
            doc = Document(doc_file)
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        except Exception as e:
            raise Exception(f"DOCX parsing failed: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\$\%\#\@\-\.\:\,]', '', text)
        return text.strip()
    
    def _intelligent_chunking(self, text: str) -> List[str]:
        """Intelligent chunking preserving semantic boundaries"""
        
        # Try to split by logical sections first (double newlines often indicate sections)
        sections = text.split('\n\n')
        
        chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # If section is still too large, use recursive splitter
            if len(section) > Config.CHUNK_SIZE:
                sub_chunks = self.text_splitter.split_text(section)
                chunks.extend(sub_chunks)
            else:
                chunks.append(section)
        
        # Final fallback: if no chunks created, use text splitter
        if not chunks:
            chunks = self.text_splitter.split_text(text)
        
        return chunks
