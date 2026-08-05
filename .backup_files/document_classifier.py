# document_classifier.py - AI-powered document type detection
import re

class DocumentClassifier:
    def __init__(self):
        self.types = {
            'invoice': {
                'keywords': ['invoice', 'bill to', 'due date', 'invoice number', 'invoice date', 'client', 'total due'],
                'patterns': [
                    r'INVOICE\s*#?\s*[A-Z0-9-]+',
                    r'Due\s*Date:\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                    r'Bill\s*To:',
                    r'Invoice\s*Date',
                ],
                'category': 'Revenue'
            },
            'tax': {
                'keywords': ['hst', 'gst', 'tax return', 'tax statement', 'income tax', 'tax payment', 'tax year'],
                'patterns': [
                    r'HST\s*#?\s*[0-9]+',
                    r'GST\s*#?\s*[0-9]+',
                    r'Tax\s*Year:\s*\d{4}',
                    r'Tax\s*Return',
                ],
                'category': 'Tax'
            },
            'expense': {
                'keywords': ['total', 'subtotal', 'payment', 'receipt', 'thank you', 'merchant'],
                'patterns': [
                    r'Total:\s*\$[\d,]+\.\d{2}',
                    r'Subtotal:\s*\$[\d,]+\.\d{2}',
                    r'Payment\s*Type:',
                ],
                'category': 'Expenses'
            }
        }

    def detect_type(self, text: str) -> dict:
        text = text.lower()
        scores = {doc_type: 0 for doc_type in self.types}
        
        for doc_type, rules in self.types.items():
            # Check keywords
            for keyword in rules['keywords']:
                if keyword.lower() in text:
                    scores[doc_type] += 2
            
            # Check patterns
            for pattern in rules['patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    scores[doc_type] += 3
            
            # Check for merchant names that indicate type
            if doc_type == 'expense':
                if any(word in text for word in ['starbucks', 'tim hortons', 'walmart', 'costco']):
                    scores[doc_type] += 1
        
        # Determine the best match
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type] / 10
        
        return {
            'document_type': best_type,
            'confidence': min(confidence, 1.0),
            'category': self.types[best_type]['category'],
            'scores': scores
        }

    def extract_invoice_data(self, text: str) -> dict:
        data = {}
        
        # Extract invoice number
        invoice_match = re.search(r'INVOICE\s*#?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
        if invoice_match:
            data['document_number'] = invoice_match.group(1)
        
        # Extract due date
        due_match = re.search(r'Due\s*Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
        if due_match:
            data['due_date'] = due_match.group(1)
        
        # Extract client name
        client_match = re.search(r'Bill\s*To:\s*([^\n]+)', text, re.IGNORECASE)
        if client_match:
            data['client_name'] = client_match.group(1).strip()
        
        return data

    def extract_tax_data(self, text: str) -> dict:
        data = {}
        
        # Extract tax year
        year_match = re.search(r'Tax\s*Year:\s*(\d{4})', text, re.IGNORECASE)
        if year_match:
            data['tax_year'] = year_match.group(1)
        
        # Detect tax type
        if 'hst' in text.lower():
            data['tax_type'] = 'HST'
        elif 'gst' in text.lower():
            data['tax_type'] = 'GST'
        elif 'income tax' in text.lower():
            data['tax_type'] = 'Income Tax'
        
        return data

    def classify_receipt(self, raw_text: str, parsed_data: dict) -> dict:
        # Get document type
        doc_info = self.detect_type(raw_text)
        
        # Extract additional data based on type
        extra_data = {}
        if doc_info['document_type'] == 'invoice':
            extra_data = self.extract_invoice_data(raw_text)
        elif doc_info['document_type'] == 'tax':
            extra_data = self.extract_tax_data(raw_text)
        
        # Determine if business or personal
        is_business = True
        if any(word in raw_text.lower() for word in ['personal', 'personal use']):
            is_business = False
        
        return {
            **doc_info,
            **extra_data,
            'is_business': is_business,
            'is_reimbursable': doc_info['document_type'] == 'expense' and is_business
        }
