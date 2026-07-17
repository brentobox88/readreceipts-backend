# app/models/category.py
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#4CAF50")
    icon = Column(String(50))
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    parent_category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    receipts = relationship("Receipt", back_populates="category_obj")
