# app/services/ocr/ocr_factory.py
import os
import logging
from typing import Optional
from app.services.ocr.google_document_ai import GoogleDocumentAI

logger = logging.getLogger(__name__)

class OCRFactory:
    """Factory for creating OCR service instances"""
    
    _instance = None
    _ocr_service = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRFactory, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_ocr_service(cls):
        """Get the configured OCR service"""
        if cls._ocr_service is None:
            try:
                # Default to Google Document AI
                cls._ocr_service = GoogleDocumentAI()
                logger.info("Initialized Google Document AI OCR service")
            except Exception as e:
                logger.error(f"Failed to initialize OCR service: {e}")
                raise Exception(f"OCR service initialization failed: {str(e)}")
        
        return cls._ocr_service
    
    @classmethod
    def reset(cls):
        """Reset the OCR service (for testing)"""
        cls._ocr_service = None
        cls._instance = None
