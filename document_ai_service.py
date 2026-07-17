import os
import re
import json
import sys
from typing import Dict, List, Optional
from google.cloud import documentai
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

class DocumentAIProcessor:
    def __init__(self):
        """Initialize Google Document AI"""
        # Get credentials from environment
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        self.processor_id = os.getenv("GOOGLE_DOCUMENT_AI_PROCESSOR_ID")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Set credentials path for Google Auth
        if self.credentials_path and os.path.exists(self.credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            print(f"[OK] Using credentials from: {self.credentials_path}")
        
        # Check credentials
        if not all([self.project_id, self.processor_id]):
            print("[WARNING] Document AI credentials not fully configured!")
            print(f"  Project ID: {'[OK]' if self.project_id else '[MISSING]'}")
            print(f"  Processor ID: {'[OK]' if self.processor_id else '[MISSING]'}")
            self.client = None
            self.processor_name = None
            self.initialized = False
            return
        
        try:
            # Initialize client
            self.client = documentai.DocumentProcessorServiceClient()
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            self.initialized = True
            print("[OK] Document AI initialized successfully!")
            print(f"   Project: {self.project_id}")
            print(f"   Processor: {self.processor_id}")
            print(f"   Location: {self.location}")
            print(f"   Full path: {self.processor_name}")
        except Exception as e:
            print(f"[ERROR] Error initializing Document AI: {e}")
            self.client = None
            self.processor_name = None
            self.initialized = False
    
    def process_receipt(self, image_content: bytes) -> Dict:
        """Process receipt image with Document AI"""
        if not self.initialized:
            return {
                'error': 'Document AI not initialized. Check credentials.',
                'total_amount': None,
                'total_tax_amount': None,
                'net_amount': None,
                'receipt_date': None,
                'purchase_time': None,
                'currency': None,
                'supplier_name': None,
                'supplier_address': None,
                'supplier_phone': None,
                'line_items': [],
                'confidence_scores': {},
                'entities_found': []
            }
        
        try:
            # Prepare document
            raw_document = documentai.RawDocument(
                content=image_content, 
                mime_type="image/jpeg"
            )
            
            # Process request
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract all fields
            receipt_data = self._extract_receipt_data(document)
            receipt_data['raw_text'] = document.text if hasattr(document, 'text') else ""
            receipt_data['processed'] = True
            
            return receipt_data
            
        except Exception as e:
            print(f"[ERROR] Error processing receipt: {e}")
            return {
                'error': str(e),
                'processed': False
            }
    
    def _extract_receipt_data(self, document) -> Dict:
        """Extract all receipt fields from Document AI response"""
        receipt_data = {
            'total_amount': None,
            'total_tax_amount': None,
            'net_amount': None,
            'receipt_date': None,
            'purchase_time': None,
            'currency': None,
            'supplier_name': None,
            'supplier_address': None,
            'supplier_phone': None,
            'line_items': [],
            'confidence_scores': {},
            'entities_found': []
        }
        
        # Process each entity
        for entity in document.entities:
            entity_type = entity.type_
            
            # Get normalized value if available
            if hasattr(entity, 'normalized_value') and entity.normalized_value:
                value = entity.normalized_value.text
            else:
                value = entity.mention_text
            
            # Map to our fields
            if entity_type == 'total_amount':
                receipt_data['total_amount'] = self._clean_currency(value)
                receipt_data['confidence_scores']['total_amount'] = entity.confidence
                
            elif entity_type == 'total_tax_amount':
                receipt_data['total_tax_amount'] = self._clean_currency(value)
                receipt_data['confidence_scores']['total_tax_amount'] = entity.confidence
                
            elif entity_type == 'net_amount':
                receipt_data['net_amount'] = self._clean_currency(value)
                receipt_data['confidence_scores']['net_amount'] = entity.confidence
                
            elif entity_type == 'receipt_date':
                receipt_data['receipt_date'] = value
                receipt_data['confidence_scores']['receipt_date'] = entity.confidence
                
            elif entity_type == 'purchase_time':
                receipt_data['purchase_time'] = value
                receipt_data['confidence_scores']['purchase_time'] = entity.confidence
                
            elif entity_type == 'currency':
                receipt_data['currency'] = value
                receipt_data['confidence_scores']['currency'] = entity.confidence
                
            elif entity_type == 'supplier_name':
                receipt_data['supplier_name'] = value
                receipt_data['confidence_scores']['supplier_name'] = entity.confidence
                
            elif entity_type == 'supplier_address':
                receipt_data['supplier_address'] = value
                receipt_data['confidence_scores']['supplier_address'] = entity.confidence
                
            elif entity_type == 'supplier_phone':
                receipt_data['supplier_phone'] = value
                receipt_data['confidence_scores']['supplier_phone'] = entity.confidence
                
            elif entity_type.startswith('line_item/'):
                item = self._extract_line_item(entity)
                if item:
                    receipt_data['line_items'].append(item)
            
            # Track what entities were found
            receipt_data['entities_found'].append(entity_type)
        
        return receipt_data
    
    def _clean_currency(self, value: str) -> Optional[float]:
        """Clean currency string and convert to float"""
        if not value:
            return None
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,€£]', '', value)
        cleaned = cleaned.replace(',', '')
        try:
            return float(cleaned)
        except ValueError:
            return value
    
    def _extract_line_item(self, entity) -> Dict:
        """Extract line item details"""
        item = {
            'description': None,
            'quantity': None,
            'unit_price': None,
            'amount': None
        }
        
        for prop in entity.properties:
            prop_type = prop.type_
            value = prop.mention_text
            
            if prop_type == 'line_item/description':
                item['description'] = value
            elif prop_type == 'line_item/quantity':
                try:
                    item['quantity'] = float(value)
                except ValueError:
                    item['quantity'] = value
            elif prop_type == 'line_item/unit_price':
                try:
                    item['unit_price'] = float(value.replace('$', '').replace(',', ''))
                except ValueError:
                    item['unit_price'] = value
            elif prop_type == 'line_item/amount':
                try:
                    item['amount'] = float(value.replace('$', '').replace(',', ''))
                except ValueError:
                    item['amount'] = value
        
        return item

# Create global instance
document_ai_processor = DocumentAIProcessor()
