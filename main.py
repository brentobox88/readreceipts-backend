import sys
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
from datetime import datetime
import csv
import io
import shutil

# Import our OCR processor
try:
    from ocr_service import ocr_processor
    OCR_AVAILABLE = True
    print("✓ Real OCR service loaded successfully")
except ImportError as e:
    print(f"⚠ OCR not available: {e}")
    OCR_AVAILABLE = False

# Initialize database
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
        confidence REAL,
        status TEXT DEFAULT 'processed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(
    title="Read Receipts - Real OCR",
    description="Automated receipt processing with real OCR",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads/receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {
        "app": "Read Receipts",
        "version": "3.0.0",
        "ocr_available": OCR_AVAILABLE,
        "description": "Automated receipt processing with real OCR",
        "endpoints": {
            "upload": "POST /upload",
            "receipts": "GET /receipts",
            "test/receipts": "GET /test/receipts",
            "export/csv": "GET /export/csv",
            "health": "GET /health",
            "ocr/test": "GET /ocr/test"
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ocr": OCR_AVAILABLE,
        "database": "SQLite (receipts.db)"
    }

@app.get("/ocr/test")
def ocr_test():
    """Test OCR functionality"""
    if not OCR_AVAILABLE:
        return {"ocr": "not_available", "message": "OCR service not loaded"}
    
    return {
        "ocr": "available",
        "processor": "Tesseract OCR",
        "test": "OCR service is ready"
    }

@app.post("/upload")
async def upload_receipt(file: UploadFile = File(...), business: str = None):
    """Upload and process a receipt image with real OCR"""
    try:
        if not OCR_AVAILABLE:
            raise HTTPException(status_code=500, detail="OCR service not available")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        image_content = await file.read()
        
        # Process with OCR
        result = ocr_processor.process_receipt_image(image_content, file.filename)
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "OCR processing failed"))
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(filepath, "wb") as buffer:
            buffer.write(image_content)
        
        # Extract data from OCR result
        parsed_data = result["parsed_data"]
        
        # Save to database
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO receipts 
        (filename, file_path, merchant_name, total_amount, tax_amount, category, business, notes, transaction_date, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file.filename,
            filepath,
            parsed_data["merchant"]["name"],
            parsed_data["financials"]["total"],
            parsed_data["financials"]["tax_amount"],
            parsed_data.get("categorization", {}).get("category", "uncategorized"),
            business or parsed_data.get("business_assignment", {}).get("business", "general"),
            parsed_data.get("notes", ""),
            datetime.now().strftime("%Y-%m-%d"),
            result["confidence"]
        ))
        
        receipt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Receipt processed with REAL OCR!",
            "receipt_id": receipt_id,
            "ocr_confidence": result["confidence"],
            "data": {
                "merchant": parsed_data["merchant"]["name"],
                "total": f"${parsed_data['financials']['total']:.2f}",
                "tax": f"${parsed_data['financials']['tax_amount']:.2f}",
                "category": parsed_data.get("categorization", {}).get("category", "uncategorized"),
                "business": business or parsed_data.get("business_assignment", {}).get("business", "general"),
                "notes": parsed_data.get("notes", ""),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "raw_text_preview": result["raw_text"][:100] + "..." if len(result["raw_text"]) > 100 else result["raw_text"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/receipts")
def get_receipts(business: str = None, category: str = None):
    """Get all receipts with filters"""
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
    conn.close()
    
    # Format response
    receipts = []
    for row in rows:
        receipts.append({
            "id": row[0],
            "filename": row[1],
            "merchant": row[3],
            "total": row[4],
            "tax": row[5],
            "category": row[6],
            "business": row[7],
            "notes": row[8],
            "date": row[9],
            "confidence": row[10],
            "status": row[11]
        })
    
    return {
        "count": len(receipts),
        "filters": {"business": business, "category": category},
        "receipts": receipts
    }

@app.get("/test/receipts")
def create_test_receipts():
    """Create test data matching your spreadsheet"""
    test_data = [
        ("Lyft receipt.jpg", "uploads/test/lyft.jpg", "Lyft", 22.74, 2.62, "transportation", "production", 
         "Lyft (production trip transportation expense)", "2024-01-15", 0.95),
        ("Pizza receipt.jpg", "uploads/test/pizza.jpg", "NORTH OF BROOKLYN PIZZERIA", 35.88, 4.13, "food", "production",
         "NORTH OF BROOKLYN PIZZERIA - pizza (production trip food expense)", "2024-01-15", 0.92),
        ("Apple receipt.jpg", "uploads/test/apple.jpg", "Apple", 14.68, 1.69, "software", "general",
         "Apple - iCloud 2TB", "2024-01-15", 0.88),
        ("United Airlines receipt.jpg", "uploads/test/united.jpg", "United Airlines", 851.22, 125.33, "travel", "production",
         "United Airlines - YYZ to MNL (production trip travel expense)", "2024-01-15", 0.85),
        ("Sportchek receipt.jpg", "uploads/test/sportchek.jpg", "Sportchek", 1402.93, 115.93, "production_supplies", "production",
         "Sportchek - photoshoot prop", "2024-01-15", 0.90)
    ]
    
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    
    for data in test_data:
        cursor.execute('''
        INSERT INTO receipts 
        (filename, file_path, merchant_name, total_amount, tax_amount, category, business, notes, transaction_date, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
    
    conn.commit()
    conn.close()
    
    return {
        "message": f"Created {len(test_data)} test receipts",
        "receipts": test_data
    }

@app.get("/export/csv")
def export_csv(business: str = None):
    """Export receipts to CSV matching your spreadsheet format"""
    # Get receipts
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    
    query = "SELECT * FROM receipts"
    if business:
        query += " WHERE business = ?"
        cursor.execute(query, (business,))
    else:
        cursor.execute(query)
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="No receipts found")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header (your spreadsheet columns)
    writer.writerow(["DATE", "CAD", "HST", "RMB", "USD", "NOTES", "BUSINESS", "CATEGORY", "MERCHANT"])
    
    # Write data
    for row in rows:
        # row: id, filename, file_path, merchant, total, tax, category, business, notes, date, confidence, status, created_at
        date = row[9] if row[9] else datetime.now().strftime("%Y-%m-%d")
        total = float(row[4]) if row[4] else 0
        tax = float(row[5]) if row[5] else 0
        subtotal = total - tax
        notes = row[8] if row[8] else ""
        business_name = row[7] if row[7] else "general"
        category = row[6] if row[6] else "uncategorized"
        merchant = row[3] if row[3] else "Unknown"
        
        writer.writerow([
            date,
            f"${subtotal:.2f}" if subtotal > 0 else "",
            f"${tax:.2f}" if tax > 0 else "",
            "",  # RMB
            "",  # USD
            notes,
            business_name.upper(),
            category.upper(),
            merchant
        ])
    
    # Return CSV file
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=receipts_export.csv"}
    )

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 READ RECEIPTS - REAL OCR VERSION")
    print("=" * 60)
    print(f"✓ OCR Available: {OCR_AVAILABLE}")
    print("📁 Database: receipts.db")
    print("📁 Uploads: uploads/receipts/")
    print("🌐 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("")
    print("FEATURES:")
    print("  • REAL OCR text extraction from images")
    print("  • Auto-categorization (food, transportation, etc.)")
    print("  • Business assignment (production, design, general)")
    print("  • Export to CSV matching your spreadsheet format")
    print("  • Confidence scoring for OCR accuracy")
    print("")
    print("ENDPOINTS:")
    print("  POST /upload        - Upload receipt (REAL OCR)")
    print("  GET  /receipts      - List all receipts")
    print("  GET  /test/receipts - Create test data")
    print("  GET  /export/csv    - Export to CSV")
    print("  GET  /ocr/test      - Test OCR functionality")
    print("  GET  /health        - Health check")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    if __name__ == "__main__":
    	import os
    	port = int(os.getenv("PORT", 8000))
    	uvicorn.run(app, host="0.0.0.0", port=port)