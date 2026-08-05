import os
import re
import json
import base64
from google.cloud import documentai_v1 as documentai

# ============================================
# HARDCODED VALUES - For demo deployment
# ============================================
PROJECT_ID = "receipt-relief"
PROCESSOR_ID = "896553633cd26552"
LOCATION = "us"  # Format is 'us' or 'eu'
# ============================================

def clean_price(value):
    if not value:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Remove currency symbols, commas, and extra whitespace
    cleaned = re.sub(r'[$,]', '', str(value))
    try:
        return float(cleaned)
    except:
        return 0.0

class DocumentAIProcessor:
    def __init__(self):
        self.client = None
        self.processor_name = None
        self.initialized = False
        self.init_document_ai()

    def init_document_ai(self):
        """Initialize Document AI client with hardcoded credentials."""
        try:
            # Use hardcoded PROJECT_ID and PROCESSOR_ID
            self.client = documentai.DocumentProcessorServiceClient()
            self.processor_name = self.client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
            self.initialized = True
            print(f"[OK] Document AI initialized successfully!")
            print(f"   Project: {PROJECT_ID}")
            print(f"   Processor: {PROCESSOR_ID}")
            print(f"   Location: {LOCATION}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Document AI: {str(e)}")
            self.initialized = False

    def process_receipt(self, image_content):
        """Process a receipt image using Document AI."""
        if not self.initialized:
            return {"error": "Document AI not initialized. Check credentials."}

        try:
            # Encode image to base64
            encoded_image = base64.b64encode(image_content).decode("utf-8")

            # Configure the process request
            raw_document = documentai.RawDocument(
                content=encoded_image,
                mime_type="image/jpeg"
            )

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )

            # Process the document
            result = self.client.process_document(request=request)
            document = result.document

            # Extract data from Document AI response
            extracted_data = self._parse_document(document)
            extracted_data["raw_text"] = document.text if hasattr(document, 'text') else ""

            return extracted_data

        except Exception as e:
            print(f"[ERROR] Document processing failed: {str(e)}")
            return {"error": f"Processing failed: {str(e)}"}

    def _parse_document(self, document):
        """Parse Document AI response into structured data."""
        extracted = {
            "supplier_name": "",
            "supplier_address": "",
            "receipt_date": "",
            "total_amount": 0.0,
            "total_tax_amount": 0.0,
            "net_amount": 0.0,
            "currency": "USD",
            "line_items": [],
            "confidence_scores": {},
            "entities_found": []
        }

        # Extract entities from Document AI response
        if hasattr(document, 'entities'):
            for entity in document.entities:
                entity_type = entity.type_
                confidence = entity.confidence if hasattr(entity, 'confidence') else 0.0
                extracted["confidence_scores"][entity_type] = confidence

                if entity_type == "supplier_name":
                    extracted["supplier_name"] = entity.mention_text
                elif entity_type == "supplier_address":
                    extracted["supplier_address"] = entity.mention_text
                elif entity_type == "receipt_date":
                    extracted["receipt_date"] = entity.mention_text
                elif entity_type == "total_amount":
                    extracted["total_amount"] = clean_price(entity.mention_text)
                elif entity_type == "total_tax":
                    extracted["total_tax_amount"] = clean_price(entity.mention_text)
                elif entity_type == "net_amount":
                    extracted["net_amount"] = clean_price(entity.mention_text)
                elif entity_type == "currency":
                    extracted["currency"] = entity.mention_text

        # Extract line items if available
        if hasattr(document, 'pages'):
            for page in document.pages:
                for table in page.tables:
                    for row in table.header_rows:
                        # Simplified line item extraction
                        pass

        return extracted

# Create a global instance for use in the main app
document_ai_processor = DocumentAIProcessor()
