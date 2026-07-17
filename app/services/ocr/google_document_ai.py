# app/services/ocr/google_document_ai.py
import os
import base64
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import documentai_v1 as documentai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image
import io

logger = logging.getLogger(__name__)

class GoogleDocumentAI:
    """Google Cloud Document AI service for receipt processing"""
    
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID")
        self.location = os.getenv("LOCATION", "us")
        self.processor_id = os.getenv("PROCESSOR_ID")
        
        if not all([self.project_id, self.processor_id]):
            raise ValueError("Missing required Google Cloud configuration")
        
        # Initialize Document AI client
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            self.project_id, self.location, self.processor_id
        )
        
        logger.info(f"Initialized Document AI with processor: {self.processor_name}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def process_receipt(self, image_bytes: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Process a receipt image using Google Document AI
        
        Args:
            image_bytes: Raw image bytes
            filename: Original filename (for logging)
        
        Returns:
            Structured receipt data with confidence scores
        """
        try:
            # Preprocess image
            processed_bytes = self._preprocess_image(image_bytes)
            
            # Encode to base64
            encoded_image = base64.b64encode(processed_bytes).decode("utf-8")
            
            # Create Document AI request
            request = {
                "name": self.processor_name,
                "raw_document": {
                    "content": encoded_image,
                    "mime_type": "image/jpeg",
                },
            }
            
            # Process document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Parse response
            receipt_data = self._parse_document(document)
            receipt_data['confidence'] = self._calculate_confidence(document)
            
            logger.info(f"Processed receipt: {receipt_data.get('merchant_name', 'Unknown')} - {receipt_data.get('total_amount', 0)}")
            
            return receipt_data
            
        except exceptions.PermissionDenied as e:
            logger.error(f"Permission denied: {e}")
            raise Exception("Invalid API credentials. Please check your service account key.")
        except exceptions.ResourceExhausted as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise Exception("OCR service is busy. Please try again in a few moments.")
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            raise Exception(f"Failed to process receipt: {str(e)}")
    
    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        """
        Preprocess image for better OCR results
        - Convert to RGB
        - Resize if too large
        - Enhance contrast
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if image is too large (> 4K resolution)
            max_size = 4000
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            return image_bytes
    
    def _parse_document(self, document) -> Dict[str, Any]:
        """Parse Document AI response into structured receipt data"""
        entities = {entity.type: entity for entity in document.entities}
        
        # Helper to get entity value
        def get_entity_value(entity_type, default=""):
            entity = entities.get(entity_type)
            if entity:
                return entity.mention_text
            return default
        
        # Helper to get entity confidence
        def get_entity_confidence(entity_type, default=0.0):
            entity = entities.get(entity_type)
            if entity:
                return entity.confidence or default
            return default
        
        # Parse line items
        line_items = []
        if 'line_item' in document.entities:
            for item in document.entities['line_item']:
                line_item = {}
                if hasattr(item, 'properties'):
                    for prop in item.properties:
                        prop_name = prop.type
                        if prop_name in ['description', 'quantity', 'unit_price', 'total_price']:
                            line_item[prop_name] = prop.mention_text
                if line_item:
                    line_items.append(line_item)
        
        # Build receipt data
        receipt_data = {
            "merchant_name": get_entity_value("merchant_name"),
            "merchant_address": get_entity_value("merchant_address"),
            "merchant_phone": get_entity_value("merchant_phone"),
            "merchant_website": get_entity_value("merchant_website"),
            "transaction_date": get_entity_value("transaction_date"),
            "transaction_time": get_entity_value("transaction_time"),
            "receipt_number": get_entity_value("receipt_number"),
            "subtotal": float(get_entity_value("subtotal_amount", 0)),
            "tax_amount": float(get_entity_value("tax_amount", 0)),
            "tax_rate": float(get_entity_value("tax_rate", 0)),
            "total_amount": float(get_entity_value("total_amount", 0)),
            "currency": get_entity_value("currency", "USD"),
            "payment_method": get_entity_value("payment_method"),
            "payment_card_number": get_entity_value("payment_card_number"),
            "line_items": line_items,
            "category": self._categorize_receipt(entities),
            "business": self._determine_business(entities),
            "raw_text": document.text if hasattr(document, 'text') else "",
            "field_confidences": {
                "merchant": get_entity_confidence("merchant_name"),
                "total": get_entity_confidence("total_amount"),
                "date": get_entity_confidence("transaction_date"),
                "tax": get_entity_confidence("tax_amount"),
            }
        }
        
        return receipt_data
    
    def _calculate_confidence(self, document) -> float:
        """Calculate overall confidence score"""
        if not document.entities:
            return 0.0
        
        # Average confidence of key fields
        confidences = []
        key_fields = ['merchant_name', 'total_amount', 'transaction_date']
        for field in key_fields:
            for entity in document.entities:
                if entity.type == field:
                    confidences.append(entity.confidence or 0.0)
                    break
        
        if confidences:
            return sum(confidences) / len(confidences)
        return 0.0
    
    def _categorize_receipt(self, entities: Dict) -> str:
        """Categorize receipt based on merchant type"""
        # This is a simple heuristic - can be enhanced with ML
        merchant_name = entities.get('merchant_name', '').mention_text.lower() if entities.get('merchant_name') else ''
        
        # Common categories
        categories = {
            'food': ['restaurant', 'cafe', 'pizza', 'burger', 'coffee', 'bakery', 'diner'],
            'groceries': ['grocery', 'market', 'supermarket', 'whole foods', 'trader joe'],
            'transportation': ['lyft', 'uber', 'taxi', 'transit', 'metro', 'bus', 'train'],
            'office': ['office', 'staples', 'officemax', 'best buy', 'apple', 'dell'],
            'software': ['subscription', 'adobe', 'microsoft', 'google', 'amazon web', 'salesforce'],
            'utilities': ['electric', 'water', 'gas', 'internet', 'phone', 'verizon', 'att'],
            'rent': ['rent', 'leasing', 'property'],
            'travel': ['hotel', 'marriott', 'hilton', 'airbnb', 'flight', 'airline'],
            'entertainment': ['movie', 'theater', 'concert', 'sports'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in merchant_name for keyword in keywords):
                return category
        
        return "other"
    
    def _determine_business(self, entities: Dict) -> str:
        """Determine business context"""
        # This could be enhanced with user preferences or ML
        return "general"
