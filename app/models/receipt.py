# app/models/receipt.py
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Receipt(Base):
    __tablename__ = "receipts"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Batch relationship
    batch_id = Column(String(36), ForeignKey("batches.id"), nullable=True)
    
    # File info
    filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    image_path = Column(String(500), nullable=True)
    storage_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Extracted data
    merchant_name = Column(String(255), nullable=True)
    merchant_address = Column(String(500), nullable=True)
    transaction_date = Column(String(50), nullable=True)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    currency = Column(String(10), default='USD')
    line_items = Column(Text, nullable=True)
    parsed_data = Column(Text, nullable=True)
    
    # Classification
    document_type = Column(String(50), default='expense')
    document_number = Column(String(100), nullable=True)
    client_name = Column(String(255), nullable=True)
    client_address = Column(String(500), nullable=True)
    due_date = Column(String(50), nullable=True)
    tax_type = Column(String(50), nullable=True)
    tax_year = Column(String(10), nullable=True)
    category = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Amounts
    income_amount = Column(Float, default=0.0)
    expense_amount = Column(Float, default=0.0)
    tax_amount_paid = Column(Float, default=0.0)
    
    # Metadata
    confidence_score = Column(Float, default=0.0)
    status = Column(String(50), default='processed')
    error_message = Column(Text, nullable=True)
    raw_document_ai_json = Column(JSON, nullable=True)
    normalized_json = Column(JSON, nullable=True)
    manually_edited = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    batch = relationship("Batch", back_populates="receipts")
