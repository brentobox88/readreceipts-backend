import re
from typing import Dict, List, Optional
from datetime import datetime
import json

class MockReceiptProcessor:
    """Mock processor that simulates OCR - based on your sample receipts"""
    
    def process_receipt(self, image_content: bytes, filename: str) -> Dict:
        """
        Process receipt - returns mock data matching your spreadsheet format
        """
        # Simulate different receipt types based on filename
        if "pizza" in filename.lower() or "pizzeria" in filename.lower():
            return self._create_pizza_receipt()
        elif "lyft" in filename.lower() or "uber" in filename.lower():
            return self._create_transport_receipt()
        elif "apple" in filename.lower():
            return self._create_software_receipt()
        elif "airline" in filename.lower():
            return self._create_travel_receipt()
        else:
            return self._create_generic_receipt()
    
    def _create_pizza_receipt(self) -> Dict:
        """North of Brooklyn Pizzeria receipt"""
        return {
            "success": True,
            "merchant": {
                "name": "NORTH OF BROOKLYN PIZZERIA",
                "address": "663 GREENWOOD AVENUE, TORONTO, ON M6B 1S3",
                "phone": "6473521000"
            },
            "transaction": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "number": "738125731RT0001"
            },
            "line_items": [
                {"description": "18' Killer Bee Pie", "quantity": 1, "price": 30.00},
                {"description": "Creamy Garlic Dip", "quantity": 1, "price": 1.75}
            ],
            "financials": {
                "subtotal": 31.75,
                "tax_amount": 4.13,
                "tax_rate": 0.13,
                "total": 35.88,
                "currency": "CAD"
            },
            "categorization": {
                "category": "food",
                "business": "production",
                "tags": ["pizza", "catering", "team meal"],
                "notes": "NORTH OF BROOKLYN PIZZERIA - 18' Killer Bee Pie (production trip food expense)"
            },
            "confidence": 0.95
        }
    
    def _create_transport_receipt(self) -> Dict:
        """Lyft/Uber receipt"""
        return {
            "success": True,
            "merchant": {
                "name": "Lyft",
                "address": "San Francisco, CA"
            },
            "transaction": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "number": "LYFT" + datetime.now().strftime("%Y%m%d%H%M%S")
            },
            "line_items": [
                {"description": "Ride from Airport to Hotel", "quantity": 1, "price": 22.74}
            ],
            "financials": {
                "subtotal": 22.74,
                "tax_amount": 2.62,
                "tax_rate": 0.13,
                "total": 25.36,
                "currency": "CAD"
            },
            "categorization": {
                "category": "transportation",
                "business": "production",
                "tags": ["ride share", "airport", "transport"],
                "notes": "Lyft (production trip transportation expense)"
            },
            "confidence": 0.90
        }
    
    def _create_software_receipt(self) -> Dict:
        """Apple/Software receipt"""
        return {
            "success": True,
            "merchant": {
                "name": "Apple",
                "address": "Cupertino, CA"
            },
            "transaction": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "number": "APPLE" + datetime.now().strftime("%Y%m%d")
            },
            "line_items": [
                {"description": "iCloud 2TB Storage", "quantity": 1, "price": 14.68}
            ],
            "financials": {
                "subtotal": 14.68,
                "tax_amount": 1.69,
                "tax_rate": 0.13,
                "total": 16.37,
                "currency": "CAD"
            },
            "categorization": {
                "category": "software",
                "business": "general",
                "tags": ["subscription", "cloud storage", "software"],
                "notes": "Apple - iCloud 2TB"
            },
            "confidence": 0.92
        }
    
    def _create_travel_receipt(self) -> Dict:
        """Airline travel receipt"""
        return {
            "success": True,
            "merchant": {
                "name": "United Airlines",
                "address": "Chicago, IL"
            },
            "transaction": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "number": "UA" + datetime.now().strftime("%Y%m%d")
            },
            "line_items": [
                {"description": "YYZ to MNL Flight", "quantity": 1, "price": 851.22}
            ],
            "financials": {
                "subtotal": 851.22,
                "tax_amount": 125.33,
                "tax_rate": 0.13,
                "total": 976.55,
                "currency": "CAD"
            },
            "categorization": {
                "category": "travel",
                "business": "production",
                "tags": ["airline", "flight", "production trip"],
                "notes": "United Airlines - YYZ to MNL (production trip travel expense)"
            },
            "confidence": 0.88
        }
    
    def _create_generic_receipt(self) -> Dict:
        """Generic receipt for anything else"""
        return {
            "success": True,
            "merchant": {
                "name": "Generic Store",
                "address": "123 Main St, Toronto, ON"
            },
            "transaction": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "number": "GEN" + datetime.now().strftime("%Y%m%d%H%M%S")
            },
            "line_items": [
                {"description": "General Purchase", "quantity": 1, "price": 50.00}
            ],
            "financials": {
                "subtotal": 50.00,
                "tax_amount": 6.50,
                "tax_rate": 0.13,
                "total": 56.50,
                "currency": "CAD"
            },
            "categorization": {
                "category": "uncategorized",
                "business": "general",
                "tags": ["general expense"],
                "notes": "Generic Store - General Purchase"
            },
            "confidence": 0.80
        }

# Create instance
receipt_processor = MockReceiptProcessor()
