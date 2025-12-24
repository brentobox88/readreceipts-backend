from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # File info
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    
    # OCR extracted data
    raw_text = Column(Text)
    parsed_data = Column(JSON)
    
    # Merchant info
    merchant_name = Column(String)
    merchant_address = Column(String)
    
    # Transaction details
    transaction_date = Column(DateTime)
    receipt_number = Column(String)
    
    # Financials
    subtotal = Column(Float)
    tax_amount = Column(Float)
    tax_rate = Column(Float, default=0.13)
    tip_amount = Column(Float, default=0.0)
    total_amount = Column(Float)
    currency = Column(String, default="CAD")
    
    # Categorization (from your spreadsheet examples)
    category = Column(String)  # food, transportation, software, production_supplies, travel
    business = Column(String)  # production, design, general
    tags = Column(JSON)  # e.g., ["production trip", "catering", "team dinner"]
    
    # Line items (stores items from receipt)
    line_items = Column(JSON)
    
    # Notes (for spreadsheet export)
    notes = Column(Text)
    
    # Status
    status = Column(String, default="pending")  # pending, processed, reviewed, exported
    confidence = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Receipt {self.id}: {self.merchant_name} - >"
