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
        
        prompt = f"""You are a logistics document assistant. Answer the question based ONLY on the provided context.

Context:
{context}

Question: {question}

Instructions:
1. Answer ONLY using information from the context above
2. If the answer is not in the context, say "Not found in document"
3. Be specific and direct
4. Include relevant details like dates, rates, names
5. if the {question} is like greeting like Hi, hello, good mnornging then reply according to that

Answer:"""
        
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a precise logistics assistant. Only answer from given context."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
                answer = response.choices[0].message.content
                certainty = 0.85  # OpenAI is reliable
                
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
            
            # Check if answer indicates not found
            is_found = "not found" not in answer.lower() and "no information" not in answer.lower()
            
            return {
                'answer': answer,
                'certainty': certainty if is_found else 0.2,
                'found_in_context': is_found
            }
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                'answer': f"LLM Error: {str(e)}. Using fallback.",
                'certainty': 0.3,
                'found_in_context': False
            }
    
    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured shipment data using LLM"""
        
        prompt = f"""Extract logistics shipment information from the document below.

Document:
{text[:2500]}

Extract these fields as JSON:
- shipment_id (string)
- shipper (string)
- consignee (string)
- pickup_datetime (string, format: YYYY-MM-DD if possible)
- delivery_datetime (string, format: YYYY-MM-DD if possible)
- equipment_type (string: 53ft, 48ft, dry van, reefer, flatbed, container)
- mode (string: truck, rail, air, ocean)
- rate (number)
- currency (string: USD, EUR, GBP)
- weight (number, in lbs)
- carrier_name (string)

Rules:
1. If a field is not found, use null
2. Return ONLY valid JSON, no other text
3. Convert dates to YYYY-MM-DD when possible

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
            # Return empty extraction on error
            return {
                'shipment_id': None, 'shipper': None, 'consignee': None,
                'pickup_datetime': None, 'delivery_datetime': None,
                'equipment_type': None, 'mode': 'truck', 'rate': None,
                'currency': None, 'weight': None, 'carrier_name': None
            }
