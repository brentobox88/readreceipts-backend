import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
from datetime import datetime
from typing import List
import json
import sqlite3

# Simple database setup
def init_db():
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        file_path TEXT,
        merchant_name TEXT,
        total_amount REAL,
        tax_amount REAL,
        category TEXT,
        business TEXT,
        notes TEXT,
        transaction_date TEXT,
        status TEXT DEFAULT 'processed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

app = FastAPI(
    title="Read Receipts",
    description="Automated receipt processing for business expenses",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - FIXED TYPO HERE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
UPLOAD_DIR = "uploads/receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mock OCR Processor
class MockReceiptProcessor:
    def process_receipt(self, image_content: bytes, filename: str):
        if "pizza" in filename.lower():
            return {
                "merchant": "NORTH OF BROOKLYN PIZZERIA",
                "total": 35.88,
                "tax": 4.13,
                "category": "food",
                "business": "production",
                "notes": "NORTH OF BROOKLYN PIZZERIA - pizza (production trip food expense)"
            }
        elif "lyft" in filename.lower() or "uber" in filename.lower():
            return {
                "merchant": "Lyft",
                "total": 22.74,
                "tax": 2.62,
                "category": "transportation",
                "business": "production",
                "notes": "Lyft (production trip transportation expense)"
            }
        elif "apple" in filename.lower():
            return {
                "merchant": "Apple",
                "total": 14.68,
                "tax": 1.69,
                "category": "software",
                "business": "general",
                "notes": "Apple - iCloud 2TB"
            }
        else:
            return {
                "merchant": "Generic Store",
                "total": 50.00,
                "tax": 6.50,
                "category": "uncategorized",
                "business": "general",
                "notes": f"{filename.split('.')[0]} - General Purchase"
            }

processor = MockReceiptProcessor()

@app.get("/")
async def root():
    return {
        "app": "Read Receipts",
        "version": "2.0.0",
        "status": "running",
        "description": "Automated receipt processing for business expenses",
        "endpoints": {
            "upload": "POST /upload",
            "receipts": "GET /receipts",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "SQLite (receipts.db)",
        "storage": {
            "uploads": os.path.exists(UPLOAD_DIR),
        }
    }

@app.post("/upload")
async def upload_receipt(file: UploadFile = File(...), business: str = None):
    """Upload and process a receipt image"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process receipt (mock OCR)
        result = processor.process_receipt(content, file.filename)
        
        # Save to database
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO receipts 
        (filename, file_path, merchant_name, total_amount, tax_amount, category, business, notes, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file.filename,
            filepath,
            result["merchant"],
            result["total"],
            result["tax"],
            result["category"],
            business or result["business"],
            result["notes"],
            datetime.now().strftime("%Y-%m-%d")
        ))
        
        receipt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Receipt processed successfully",
            "receipt_id": receipt_id,
            "data": {
                "merchant": result["merchant"],
                "total": f"${result['total']:.2f}",
                "tax": f"${result['tax']:.2f}",
                "category": result["category"],
                "business": business or result["business"],
                "notes": result["notes"],
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/receipts")
async def get_receipts(business: str = None, category: str = None):
    """Get all processed receipts with optional filters"""
    try:
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM receipts WHERE 1=1"
        params = []
        
        if business:
            query += " AND business = ?"
            params.append(business)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        conn.close()
        
        # Convert to list of dictionaries
        receipts = []
        for row in rows:
            receipt = dict(zip(column_names, row))
            receipts.append(receipt)
        
        return {
            "count": len(receipts),
            "filters": {
                "business": business,
                "category": category
            },
            "receipts": receipts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/test/receipts")
async def test_receipts():
    """Create test receipts (for development)"""
    try:
        test_data = [
            ("lyft_receipt.jpg", "uploads/test/lyft.jpg", "Lyft", 22.74, 2.62, "transportation", "production", 
             "Lyft (production trip transportation expense)", "2024-01-15"),
            ("pizza_receipt.jpg", "uploads/test/pizza.jpg", "North of Brooklyn Pizzeria", 35.88, 4.13, "food", "production",
             "NORTH OF BROOKLYN PIZZERIA - pizza (production trip food expense)", "2024-01-15"),
            ("apple_receipt.jpg", "uploads/test/apple.jpg", "Apple", 14.68, 1.69, "software", "general",
             "Apple - iCloud 2TB", "2024-01-15")
        ]
        
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        
        for data in test_data:
            cursor.execute('''
            INSERT INTO receipts 
            (filename, file_path, merchant_name, total_amount, tax_amount, category, business, notes, transaction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
        
        conn.commit()
        conn.close()
        
        return {
            "message": f"Created {len(test_data)} test receipts",
            "receipts": test_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test data creation failed: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 READ RECEIPTS - SIMPLIFIED VERSION")
    print("=" * 60)
    print("📁 Database: SQLite (receipts.db)")
    print("📁 Uploads: uploads/receipts/")
    print("🌐 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("")
    print("ENDPOINTS:")
    print("  POST /upload           - Upload receipt image")
    print("  GET  /receipts         - List all receipts")
    print("  GET  /test/receipts    - Create test data")
    print("  GET  /health           - Health check")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
