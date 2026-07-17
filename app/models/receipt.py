# app/models/receipt.py
from sqlalchemy import Column, String, DateTime, Float, JSON, Text, Boolean, Integer
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Receipt data
    merchant_name = Column(String(255), nullable=False, default="Unknown")
    merchant_address = Column(Text, nullable=True)
    transaction_date = Column(DateTime, nullable=False, default=func.now())
    receipt_number = Column(String(100), nullable=True)
    
    # Financials
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(3), default="USD")
    
    # Metadata
    filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, default=0)
    image_url = Column(String(500), nullable=True)
    
    # OCR results
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=0.0)
    
    # User fields
    business = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Line items stored as JSON
    line_items = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(50), default="pending")
    manually_edited = Column(Boolean, default=False)
    is_exported = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
