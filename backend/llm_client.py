import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMClient:
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'ollama')
        
        if self.provider == 'openai':
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
            print(f"✅ Using OpenAI: {self.model}")
            
        elif self.provider == 'ollama':
            self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            self.model = os.getenv('OLLAMA_MODEL', 'phi')
            print(f"✅ Using Ollama: {self.model} at {self.base_url}")
            
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
    
    def generate_answer(self, question: str, context: str) -> Dict[str, Any]:
        """Generate answer from context using LLM"""
        
        # Build prompt that handles ALL types of questions (including greetings)
        prompt = f"""You are a professional logistics document assistant. 

CONTEXT (only use if relevant to the question):
{context if context else "No document uploaded yet."}

USER QUESTION: {question}

INSTRUCTIONS:
1. FIRST, identify the type of question:
   - If it's a greeting (hi, hello, good morning, etc.) → Respond warmly as a helpful assistant
   - If it's a general conversation (how are you, what can you do, etc.) → Respond appropriately
   - If it's about the document → Answer ONLY from the context above
   - If no document uploaded and question needs document → Say "Please upload a document first"

2. For document questions:
   - Answer ONLY using information from the CONTEXT
   - If answer not in context, say "Not found in document"
   - Be specific, professional, and direct

3. For greetings and general conversation:
   - Be friendly and helpful
   - Briefly explain your capabilities
   - Guide user to ask about document content

ANSWER:"""
        
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional logistics document assistant. Handle greetings naturally and answer document questions strictly from context."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
                answer = response.choices[0].message.content
                certainty = 0.85
                
            else:  # ollama
                import requests
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.1
                    },
                    timeout=30
                )
                result = response.json()
                answer = result.get('response', '')
                certainty = 0.75
            
            # Determine if answer is based on context
            is_found = "not found" not in answer.lower() and "please upload" not in answer.lower()
            
            return {
                'answer': answer,
                'certainty': certainty if is_found else 0.5,
                'found_in_context': is_found
            }
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                'answer': f"Unable to process your question. Please try again.",
                'certainty': 0.3,
                'found_in_context': False
            }
    
    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured shipment data using LLM"""
        
        if not text or text.strip() == "":
            return {
                'shipment_id': None, 'shipper': None, 'consignee': None,
                'pickup_datetime': None, 'delivery_datetime': None,
                'equipment_type': None, 'mode': 'truck', 'rate': None,
                'currency': None, 'weight': None, 'carrier_name': None
            }
        
        prompt = f"""Extract logistics shipment information from the document below.

DOCUMENT TEXT:
{text[:2500]}

FIELDS TO EXTRACT (as JSON):
- shipment_id (string)
- shipper (string)
- consignee (string)
- pickup_datetime (string, format YYYY-MM-DD)
- delivery_datetime (string, format YYYY-MM-DD)
- equipment_type (string: 53ft, 48ft, dry van, reefer, flatbed, container)
- mode (string: truck, rail, air, ocean)
- rate (number)
- currency (string: USD, EUR, GBP)
- weight (number, in lbs)
- carrier_name (string)

RULES:
1. If field not found, use null
2. Return ONLY valid JSON
3. No additional text outside JSON

JSON:"""
        
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a logistics data extractor. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
                
            else:  # ollama
                import requests
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0,
                        "format": "json"
                    },
                    timeout=30
                )
                result = json.loads(response.json()['response'])
            
            # Ensure all fields exist
            default_fields = {
                'shipment_id': None, 'shipper': None, 'consignee': None,
                'pickup_datetime': None, 'delivery_datetime': None,
                'equipment_type': None, 'mode': 'truck', 'rate': None,
                'currency': None, 'weight': None, 'carrier_name': None
            }
            
            for field in default_fields:
                if field not in result:
                    result[field] = default_fields[field]
            
            return result
            
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {
                'shipment_id': None, 'shipper': None, 'consignee': None,
                'pickup_datetime': None, 'delivery_datetime': None,
                'equipment_type': None, 'mode': 'truck', 'rate': None,
                'currency': None, 'weight': None, 'carrier_name': None
            }
