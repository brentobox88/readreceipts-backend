# app/models/batch.py
from sqlalchemy import Column, String, DateTime, Integer, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from app.database import Base  # <-- ADD THIS IMPORT

class BatchStatus(str, Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class Batch(Base):
    __tablename__ = "batches"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    
    status = Column(String(50), default=BatchStatus.CREATED)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    
    progress_percent = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    avg_confidence = Column(Float, default=0.0)
    
    name = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    tags = Column(JSON, nullable=True)
    
    error_log = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    receipts = relationship("Receipt", back_populates="batch")
