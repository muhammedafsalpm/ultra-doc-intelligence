import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
import json
from config import Config

class StructuredExtractor:
    def __init__(self):
        self.date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
        ]
    
    def extract_shipment_data(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structured shipment data with confidence scores"""
        
        # Combine all text for extraction
        full_text = " ".join([chunk['text'] for chunks in chunks]) # Fix typo? Wait, no, chunks is the list, should be: for chunk in chunks
        full_text = " ".join([chunk['text'] for chunk in chunks])
        
        # Extract each field
        extracted = {
            'shipment_id': self._extract_shipment_id(full_text),
            'shipper': self._extract_shipper(full_text),
            'consignee': self._extract_consignee(full_text),
            'pickup_datetime': self._extract_pickup_datetime(full_text),
            'delivery_datetime': self._extract_delivery_datetime(full_text),
            'equipment_type': self._extract_equipment_type(full_text),
            'mode': self._extract_mode(full_text),
            'rate': self._extract_rate(full_text),
            'currency': self._extract_currency(full_text),
            'weight': self._extract_weight(full_text),
            'carrier_name': self._extract_carrier_name(full_text)
        }
        
        # Calculate confidence for each extraction
        confidence_scores = self._calculate_extraction_confidence(extracted, full_text)
        
        return {
            'extracted_data': extracted,
            'confidence_scores': confidence_scores
        }
    
    def _extract_shipment_id(self, text: str) -> str:
        patterns = [
            r'Shipment\s*(?:ID|#|Number):?\s*([A-Z0-9-]+)',
            r'REF\s*(?:#|ID):?\s*([A-Z0-9-]+)',
            r'Load\s*(?:ID|#):?\s*([A-Z0-9-]+)',
            r'Bill\s*of\s*Lading\s*(?:#|Number):?\s*([A-Z0-9-]+)',
            r'([A-Z]{2,5}\d{6,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_shipper(self, text: str) -> str:
        patterns = [
            r'Shipper:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'From:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Origin:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Sender:?\s*([^\n,]+(?:,\s*[^\n,]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if len(value) > 5 and len(value) < 200:
                    return value
        return None
    
    def _extract_consignee(self, text: str) -> str:
        patterns = [
            r'Consignee:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'To:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Destination:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Receiver:?\s*([^\n,]+(?:,\s*[^\n,]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if len(value) > 5 and len(value) < 200:
                    return value
        return None
    
    def _extract_pickup_datetime(self, text: str) -> str:
        # Look for pickup-specific patterns first
        pickup_patterns = [
            r'Pickup\s*(?:Date|Time|DateTime):?\s*([^\n]+)',
            r'Pick\s*Up\s*(?:Date|Time):?\s*([^\n]+)',
            r'Load\s*Date:?\s*([^\n]+)'
        ]
        
        for pattern in pickup_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Try to extract date from the string
                for date_pattern in self.date_patterns:
                    date_match = re.search(date_pattern, date_str)
                    if date_match:
                        return date_match.group(1)
        
        # Fallback: look for any date near pickup keywords
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'pickup' in line.lower() or 'load' in line.lower():
                for date_pattern in self.date_patterns:
                    match = re.search(date_pattern, line)
                    if match:
                        return match.group(1)
        
        return None
    
    def _extract_delivery_datetime(self, text: str) -> str:
        # Look for delivery-specific patterns first
        delivery_patterns = [
            r'Delivery\s*(?:Date|Time|DateTime):?\s*([^\n]+)',
            r'Deliver\s*(?:Date|Time):?\s*([^\n]+)',
            r'Destination\s*Date:?\s*([^\n]+)'
        ]
        
        for pattern in delivery_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                for date_pattern in self.date_patterns:
                    date_match = re.search(date_pattern, date_str)
                    if date_match:
                        return date_match.group(1)
        
        # Fallback: look for any date near delivery keywords
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'delivery' in line.lower() or 'deliver' in line.lower():
                for date_pattern in self.date_patterns:
                    match = re.search(date_pattern, line)
                    if match:
                        return match.group(1)
        
        return None
    
    def _extract_equipment_type(self, text: str) -> str:
        equipment_keywords = {
            '53ft': ['53ft', '53 ft', '53 foot', '53 feet'],
            '48ft': ['48ft', '48 ft', '48 foot', '48 feet'],
            'dry van': ['dry van', 'dryvan', 'dry van trailer'],
            'reefer': ['reefer', 'refrigerated', 'temperature controlled'],
            'flatbed': ['flatbed', 'flat bed', 'flat deck'],
            'container': ['container', 'shipping container', 'intermodal']
        }
        
        text_lower = text.lower()
        for equipment, keywords in equipment_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return equipment
        
        return None
    
    def _extract_mode(self, text: str) -> str:
        modes = {
            'truck': ['truck', 'ltl', 'ftl', 'full truckload', 'less than truckload'],
            'rail': ['rail', 'train', 'intermodal'],
            'air': ['air', 'air freight', 'air cargo'],
            'ocean': ['ocean', 'sea', 'maritime', 'vessel']
        }
        
        text_lower = text.lower()
        for mode, keywords in modes.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return mode
        
        return 'truck'  # Default for logistics
    
    def _extract_rate(self, text: str) -> float:
        patterns = Config.EXTRACTION_PATTERNS['rate']
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Handle comma-separated numbers
                value = match.replace(',', '')
                try:
                    rate = float(value)
                    if 10 < rate < 10000:  # Reasonable rate range
                        return rate
                except:
                    pass
        
        return None
    
    def _extract_currency(self, text: str) -> str:
        currency_symbols = {
            'USD': ['$', 'usd', 'dollar', 'dollars'],
            'EUR': ['€', 'eur', 'euro', 'euros'],
            'GBP': ['£', 'gbp', 'pound', 'pounds']
        }
        
        text_lower = text.lower()
        for currency, symbols in currency_symbols.items():
            for symbol in symbols:
                if symbol in text_lower:
                    return currency
        
        return None
    
    def _extract_weight(self, text: str) -> float:
        patterns = Config.EXTRACTION_PATTERNS['weight']
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                try:
                    weight = float(value)
                    if 100 < weight < 100000:  # Reasonable weight range in lbs
                        return weight
                except:
                    pass
        
        return None
    
    def _extract_carrier_name(self, text: str) -> str:
        patterns = [
            r'Carrier:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Carrier\s*Name:?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Transport\s*(?:by|provider):?\s*([^\n,]+(?:,\s*[^\n,]+)*)',
            r'Moved\s*by:?\s*([^\n,]+(?:,\s*[^\n,]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if len(value) > 2 and len(value) < 100:
                    return value
        
        return None
    
    def _calculate_extraction_confidence(self, extracted: Dict, text: str) -> Dict[str, float]:
        """Calculate confidence for each extracted field"""
        
        confidence = {}
        
        for field, value in extracted.items():
            if value is None:
                confidence[field] = 0.0
            else:
                # Heuristic-based confidence
                value_str = str(value)
                length_confidence = min(len(value_str) / 50, 1.0)  # Longer values might be more specific
                
                # Check if value appears near relevant keywords
                keyword_confidence = 0.5
                if field == 'rate' and isinstance(value, (int, float)):
                    if '$' in text or 'USD' in text:
                        keyword_confidence = 0.8
                
                confidence[field] = min(0.5 + (length_confidence * 0.3) + (keyword_confidence * 0.2), 1.0)
        
        return confidence
