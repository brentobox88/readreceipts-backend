import pytesseract
from PIL import Image
import io
import re
import json
from datetime import datetime
from typing import Dict, Tuple, List
import os

class ReceiptOCRProcessor:
    def __init__(self):
        """Initialize Tesseract OCR"""
        # Set Tesseract path
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\$env:USERNAME\AppData\Local\Tesseract-OCR\tesseract.exe"
        ]
        
        for path in tesseract_paths:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                pytesseract.pytesseract.tesseract_cmd = expanded_path
                print(f"✓ Tesseract OCR initialized from: {expanded_path}")
                break
        else:
            print("⚠ Tesseract not found. Using fallback mode.")
    
    def extract_text(self, image_content: bytes) -> Tuple[str, float]:
        """Extract text from receipt image"""
        try:
            # Open image
            image = Image.open(io.BytesIO(image_content))
            
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')
            
            # Apply basic preprocessing
            image = image.point(lambda x: 0 if x < 128 else 255)  # Simple threshold
            
            # Perform OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Calculate simple confidence (placeholder)
            confidence = 0.85 if len(text.strip()) > 10 else 0.3
            
            return text.strip(), confidence
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return "", 0.0
    
    def parse_receipt_text(self, text: str) -> Dict:
        """Parse OCR text into structured receipt data"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        result = {
            "merchant": {"name": "", "address": ""},
            "line_items": [],
            "financials": {
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "tax_rate": 0.13,
                "tip_amount": 0.0,
                "total": 0.0,
                "currency": "CAD"
            },
            "metadata": {"line_count": len(lines)}
        }
        
        # Parse each line
        for line in lines:
            # Merchant name (often at top)
            if not result["merchant"]["name"] and len(line) > 3 and len(line) < 50:
                # Check if it looks like a business name
                if re.search(r'[A-Z][a-z]+', line) or line.isupper():
                    result["merchant"]["name"] = line
            
            # Amount patterns
            amount_patterns = [
                r'[\$\€\£]?\s*(\d+\.\d{2})',
                r'Total.*?(\d+\.\d{2})',
                r'Amount.*?(\d+\.\d{2})',
                r'Balance.*?(\d+\.\d{2})'
            ]
            
            for pattern in amount_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    try:
                        amount = float(matches[-1])
                        
                        # Categorize by context
                        if "total" in line.lower() and amount > 0:
                            result["financials"]["total"] = amount
                        elif "tax" in line.lower() or "hst" in line.lower() or "gst" in line.lower():
                            result["financials"]["tax_amount"] = amount
                        elif "sub" in line.lower():
                            result["financials"]["subtotal"] = amount
                        elif "tip" in line.lower():
                            result["financials"]["tip_amount"] = amount
                    except:
                        pass
            
            # Line item detection (simplified)
            if re.search(r'\d+\s*[xX]?\s*.+\d+\.\d{2}', line):
                # Try to parse: "1 Pizza 12.99" or "2x Coffee 3.50"
                item_match = re.match(r'(\d+)\s*(?:[xX])?\s*(.+?)\s+(\d+\.\d{2})', line)
                if item_match:
                    qty, desc, price = item_match.groups()
                    result["line_items"].append({
                        "quantity": int(qty),
                        "description": desc.strip(),
                        "unit_price": float(price),
                        "total": float(price) * int(qty)
                    })
        
        # Calculate missing values
        if result["financials"]["subtotal"] == 0 and result["line_items"]:
            result["financials"]["subtotal"] = sum(item["total"] for item in result["line_items"])
        
        if result["financials"]["total"] == 0 and result["financials"]["subtotal"] > 0:
            result["financials"]["total"] = (
                result["financials"]["subtotal"] + 
                result["financials"]["tax_amount"] + 
                result["financials"]["tip_amount"]
            )
        
        return result
    
    def categorize_receipt(self, parsed_data: Dict, raw_text: str) -> Dict:
        """Categorize receipt based on your spreadsheet patterns"""
        merchant = parsed_data["merchant"]["name"].lower()
        items_text = " ".join([item["description"].lower() for item in parsed_data["line_items"]])
        search_text = f"{merchant} {items_text} {raw_text.lower()}"
        
        # Your specific categories from spreadsheet
        categories = {
            "food": {
                "keywords": ["pizza", "restaurant", "burger", "sushi", "cafe", "diner", 
                           "eats", "food", "pizzeria", "shack", "express", "grill"],
                "merchants": ["north of brooklyn", "shake shack", "daldongnae", 
                            "thai express", "waxy", "boston pizza"]
            },
            "transportation": {
                "keywords": ["lyft", "uber", "taxi", "ride", "transport", "airport"],
                "merchants": ["lyft", "uber"]
            },
            "software": {
                "keywords": ["apple", "icloud", "elementor", "capcut", "pro", "subscription", 
                           "cloud", "software", "app", "platform"],
                "merchants": ["apple", "elementor"]
            },
            "production_supplies": {
                "keywords": ["prop", "equipment", "gear", "camera", "sport", "champs", 
                           "photoshop", "shoot", "studio", "production"],
                "merchants": ["champs", "sportchek", "amazon"]
            },
            "travel": {
                "keywords": ["airline", "flight", "airport", "trip", "yyz", "yul", "mnnl",
                           "united", "airlines", "japan airlines", "hotel"],
                "merchants": ["united airlines", "japan airlines", "air canada"]
            },
            "utilities": {
                "keywords": ["internet", "phone", "electricity", "gas", "water", "utility"]
            }
        }
        
        # Check each category
        for category, rules in categories.items():
            # Check merchant name
            if any(merchant_name in search_text for merchant_name in rules.get("merchants", [])):
                return {
                    "category": category,
                    "confidence": "high",
                    "reason": f"Matched merchant: {parsed_data['merchant']['name']}"
                }
            
            # Check keywords
            if any(keyword in search_text for keyword in rules["keywords"]):
                return {
                    "category": category,
                    "confidence": "medium",
                    "reason": "Matched keyword in receipt"
                }
        
        return {
            "category": "uncategorized",
            "confidence": "low",
            "reason": "No specific category matches"
        }
    
    def assign_business(self, parsed_data: Dict, raw_text: str) -> Dict:
        """Assign receipt to your specific businesses"""
        text_lower = raw_text.lower()
        
        # Your business rules from spreadsheet
        business_rules = {
            "production": {
                "keywords": ["production trip", "photoshop", "studio", "shoot", "production",
                           "prop", "equipment", "gear", "camera", "trip", "yyz", "yul"],
                "categories": ["food", "transportation", "travel", "production_supplies"]
            },
            "design": {
                "keywords": ["design", "team dinner", "session", "web design", "design team"],
                "categories": ["food", "software"]
            },
            "general": {
                "keywords": [],
                "categories": ["software", "utilities", "uncategorized"]
            }
        }
        
        category = parsed_data.get("categorization", {}).get("category", "")
        
        # First check keywords
        for business, rules in business_rules.items():
            if any(keyword in text_lower for keyword in rules["keywords"]):
                return {
                    "business": business,
                    "confidence": "high",
                    "reason": "Matched business keyword"
                }
        
        # Then check by category
        for business, rules in business_rules.items():
            if category in rules["categories"]:
                return {
                    "business": business,
                    "confidence": "medium",
                    "reason": f"Assigned based on category: {category}"
                }
        
        # Default
        return {
            "business": "general",
            "confidence": "low",
            "reason": "Default business assignment"
        }
    
    def generate_notes(self, parsed_data: Dict, category: str, business: str) -> str:
        """Generate notes in your spreadsheet format"""
        merchant = parsed_data["merchant"]["name"] or "Purchase"
        items = parsed_data["line_items"]
        
        # Create item description
        if items:
            item_descriptions = [item["description"] for item in items[:2]]  # First 2 items
            items_str = " - " + ", ".join(item_descriptions)
            if len(items) > 2:
                items_str += f" and {len(items) - 2} more items"
        else:
            items_str = ""
        
        # Map to your spreadsheet format
        business_suffix = {
            "production": "production trip",
            "design": "design",
            "general": ""
        }.get(business, "")
        
        category_suffix = {
            "food": "food expense",
            "transportation": "transportation expense",
            "software": "software expense",
            "travel": "travel expense",
            "production_supplies": "production expense",
            "utilities": "utility expense"
        }.get(category, "expense")
        
        # Build notes string
        notes = merchant
        if items_str:
            notes += items_str
        
        if business_suffix:
            notes += f" ({business_suffix} {category_suffix})"
        elif category != "uncategorized":
            notes += f" ({category_suffix})"
        
        return notes
    
    def process_receipt_image(self, image_content: bytes, filename: str = "") -> Dict:
        """Complete receipt processing pipeline"""
        try:
            # 1. OCR Extraction
            raw_text, confidence = self.extract_text(image_content)
            
            if not raw_text or confidence < 0.3:
                return {
                    "success": False,
                    "error": "Low OCR confidence or no text detected",
                    "confidence": confidence
                }
            
            # 2. Parse structured data
            parsed_data = self.parse_receipt_text(raw_text)
            
            # 3. Categorize
            categorization = self.categorize_receipt(parsed_data, raw_text)
            parsed_data["categorization"] = categorization
            
            # 4. Assign business
            business_assignment = self.assign_business(parsed_data, raw_text)
            parsed_data["business_assignment"] = business_assignment
            
            # 5. Generate notes
            notes = self.generate_notes(
                parsed_data, 
                categorization["category"], 
                business_assignment["business"]
            )
            parsed_data["notes"] = notes
            
            return {
                "success": True,
                "raw_text": raw_text,
                "parsed_data": parsed_data,
                "confidence": confidence,
                "processing_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Receipt processing error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Create global instance
ocr_processor = ReceiptOCRProcessor()
