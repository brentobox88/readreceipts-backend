from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import shutil
from datetime import datetime
from typing import List
import json

# Import our modules
from app.database import engine, Base, get_db
from app.models.receipt import Receipt
from app.services.ocr_service import receipt_processor
from app.services.spreadsheet_service import spreadsheet_exporter
from sqlalchemy.orm import Session

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Read Receipts",
    description="Automated receipt processing for business expenses",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
UPLOAD_DIR = "uploads/receipts"
EXPORT_DIR = "exports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

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
            "export": "GET /export/excel",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "storage": {
            "uploads": os.path.exists(UPLOAD_DIR),
            "exports": os.path.exists(EXPORT_DIR)
        }
    }

@app.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    business: str = None,
    db: Session = next(get_db())
):
    """
    Upload and process a receipt image
    """
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
            file_size = len(content)
            buffer.write(content)
        
        # Process receipt (mock OCR for now)
        result = receipt_processor.process_receipt(content, file.filename)
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail="Receipt processing failed")
        
        # Create receipt record
        receipt = Receipt(
            filename=file.filename,
            file_path=filepath,
            file_size=file_size,
            raw_text=json.dumps(result),  # Store raw result as JSON
            parsed_data=result,
            merchant_name=result["merchant"]["name"],
            merchant_address=result["merchant"]["address"],
            transaction_date=datetime.strptime(result["transaction"]["date"], "%Y-%m-%d"),
            receipt_number=result["transaction"]["number"],
            subtotal=result["financials"]["subtotal"],
            tax_amount=result["financials"]["tax_amount"],
            tax_rate=result["financials"]["tax_rate"],
            total_amount=result["financials"]["total"],
            currency=result["financials"]["currency"],
            category=result["categorization"]["category"],
            business=business or result["categorization"]["business"],
            tags=result["categorization"]["tags"],
            line_items=result["line_items"],
            notes=result["categorization"]["notes"],
            confidence=result["confidence"],
            status="processed",
            processed_at=datetime.now()
        )
        
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        
        return {
            "success": True,
            "message": "Receipt processed successfully",
            "receipt_id": receipt.id,
            "data": {
                "merchant": receipt.merchant_name,
                "total": f"",
                "tax": f"",
                "category": receipt.category,
                "business": receipt.business,
                "notes": receipt.notes,
                "date": receipt.transaction_date.strftime("%Y-%m-%d")
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/receipts")
async def get_receipts(
    business: str = None,
    category: str = None,
    db: Session = next(get_db())
):
    """
    Get all processed receipts with optional filters
    """
    query = db.query(Receipt).filter(Receipt.status == "processed")
    
    if business:
        query = query.filter(Receipt.business == business)
    
    if category:
        query = query.filter(Receipt.category == category)
    
    receipts = query.order_by(Receipt.transaction_date.desc()).all()
    
    return {
        "count": len(receipts),
        "filters": {
            "business": business,
            "category": category
        },
        "receipts": [
            {
                "id": r.id,
                "merchant": r.merchant_name,
                "total": r.total_amount,
                "tax": r.tax_amount,
                "category": r.category,
                "business": r.business,
                "notes": r.notes,
                "date": r.transaction_date.strftime("%Y-%m-%d"),
                "status": r.status
            }
            for r in receipts
        ]
    }

@app.get("/export/excel")
async def export_to_excel(
    business: str = None,
    db: Session = next(get_db())
):
    """
    Export receipts to Excel spreadsheet
    Returns Excel file matching your spreadsheet format
    """
    try:
        # Get receipts
        query = db.query(Receipt).filter(Receipt.status == "processed")
        if business:
            query = query.filter(Receipt.business == business)
        
        receipts = query.all()
        
        if not receipts:
            raise HTTPException(status_code=404, detail="No receipts to export")
        
        # Convert to dict format for exporter
        receipts_data = []
        for receipt in receipts:
            receipts_data.append({
                "merchant_name": receipt.merchant_name,
                "total_amount": receipt.total_amount,
                "tax_amount": receipt.tax_amount,
                "category": receipt.category,
                "business": receipt.business,
                "notes": receipt.notes,
                "transaction_date": receipt.transaction_date
            })
        
        # Export to Excel
        export_path = spreadsheet_exporter.export_to_excel(receipts_data)
        
        # Return the file
        filename = os.path.basename(export_path)
        return FileResponse(
            path=export_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/test/receipts")
async def test_receipts(db: Session = next(get_db())):
    """
    Create test receipts (for development)
    """
    # Create some test receipts matching your spreadsheet
    test_receipts = [
        {
            "filename": "lyft_receipt.jpg",
            "merchant_name": "Lyft",
            "total_amount": 22.74,
            "tax_amount": 2.62,
            "category": "transportation",
            "business": "production",
            "notes": "Lyft (production trip transportation expense)"
        },
        {
            "filename": "pizza_receipt.jpg",
            "merchant_name": "North of Brooklyn Pizzeria",
            "total_amount": 35.88,
            "tax_amount": 4.13,
            "category": "food",
            "business": "production",
            "notes": "NORTH OF BROOKLYN PIZZERIA - pizza (production trip food expense)"
        },
        {
            "filename": "apple_receipt.jpg",
            "merchant_name": "Apple",
            "total_amount": 14.68,
            "tax_amount": 1.69,
            "category": "software",
            "business": "general",
            "notes": "Apple - iCloud 2TB"
        }
    ]
    
    for test_data in test_receipts:
        receipt = Receipt(
            **test_data,
            file_path=f"uploads/test/{test_data['filename']}",
            status="processed",
            transaction_date=datetime.now()
        )
        db.add(receipt)
    
    db.commit()
    
    return {
        "message": f"Created {len(test_receipts)} test receipts",
        "receipts": test_receipts
    }

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 READ RECEIPTS - FULL VERSION")
    print("=" * 60)
    print("📁 Database: SQLite (receipts.db)")
    print("📁 Uploads: uploads/receipts/")
    print("📁 Exports: exports/")
    print("🌐 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("")
    print("ENDPOINTS:")
    print("  POST /upload           - Upload receipt image")
    print("  GET  /receipts         - List all receipts")
    print("  GET  /export/excel     - Export to Excel spreadsheet")
    print("  GET  /test/receipts    - Create test data")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
