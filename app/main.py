# app/main.py
import os
import uuid
import json
import io
import csv
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uvicorn

from app.database import get_db, engine, Base
from app.models.batch import Batch, BatchStatus
from app.models.receipt import Receipt
from app.services.task_queue import TaskQueueService
from imagetotable_client import ImageToTableClient

PROJECT_ID = os.getenv("PROJECT_ID", "receipt-relief")
PROCESSOR_ID = os.getenv("PROCESSOR_ID", "896553633cd26552")
IMAGETOTABLE_API_KEY = os.getenv("IMAGETOTABLE_API_KEY")

if IMAGETOTABLE_API_KEY:
    imagetotable_client = ImageToTableClient(IMAGETOTABLE_API_KEY)
    print("? ImageToTable.ai client initialized")
else:
    print("?? IMAGETOTABLE_API_KEY not set")
    imagetotable_client = None

Base.metadata.create_all(bind=engine)

# Run migrations for existing tables
try:
    from migrate_live_db import migrate
    migrate()
except Exception as e:
    print(f"Migration warning: {e}")

app = FastAPI(title="ReadReceipts API", version="2.0")

os.makedirs("uploads/receipts", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "ReadReceipts API is running", "status": "healthy"}

@app.get("/debug")
def debug():
    return {
        "PROJECT_ID": PROJECT_ID,
        "PROCESSOR_ID": PROCESSOR_ID,
        "status": "hardcoded",
        "version": "2.0"
    }

@app.get("/debug/images")
async def debug_images():
    image_dir = "uploads/receipts"
    if os.path.exists(image_dir):
        files = os.listdir(image_dir)
        return {"images": files, "count": len(files)}
    return {"images": [], "count": 0}

@app.get("/receipts")
async def get_receipts(db: Session = Depends(get_db)):
    try:
        receipts = db.query(Receipt).order_by(Receipt.created_at.desc()).all()
        return JSONResponse(content={
            "receipts": [
                {
                    "id": r.id,
                    "merchant_name": r.merchant_name or 'Unknown Merchant',
                    "merchant_address": r.merchant_address or '',
                    "transaction_date": r.transaction_date,
                    "total_amount": r.total_amount or 0,
                    "tax_amount": r.tax_amount or 0,
                    "currency": r.currency or 'USD',
                    "filename": r.filename or '',
                    "image_path": r.image_path or None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "confidence_score": r.confidence_score or 0,
                    "status": r.status or 'processed',
                    "category": r.category,
                    "document_type": r.document_type or 'expense',
                    "document_number": r.document_number,
                    "client_name": r.client_name,
                    "income_amount": r.income_amount or 0,
                    "expense_amount": r.expense_amount or 0,
                    "tax_amount_paid": r.tax_amount_paid or 0,
                    "batch_id": r.batch_id,
                }
                for r in receipts
            ]
        })
    except Exception as e:
        print(f"Error in get_receipts: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/receipts/{receipt_id}")
async def get_receipt_detail(receipt_id: str, db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return JSONResponse(content={
        "id": receipt.id,
        "merchant_name": receipt.merchant_name,
        "merchant_address": receipt.merchant_address,
        "transaction_date": receipt.transaction_date,
        "total_amount": receipt.total_amount,
        "tax_amount": receipt.tax_amount,
        "currency": receipt.currency,
        "filename": receipt.filename,
        "image_path": receipt.image_path,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
        "confidence_score": receipt.confidence_score,
        "status": receipt.status,
        "category": receipt.category,
        "document_type": receipt.document_type,
        "line_items": json.loads(receipt.line_items) if receipt.line_items else [],
        "parsed_data": json.loads(receipt.parsed_data) if receipt.parsed_data else {},
        "batch_id": receipt.batch_id,
    })

@app.put("/receipts/{receipt_id}")
async def update_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        updateable_fields = [
            "merchant_name", "merchant_address", "transaction_date",
            "total_amount", "tax_amount", "currency",
            "document_type", "document_number", "client_name",
            "due_date", "tax_type", "tax_year",
            "income_amount", "expense_amount", "tax_amount_paid",
            "category", "notes", "status"
        ]
        for field in updateable_fields:
            if field in data:
                setattr(receipt, field, data[field])
        receipt.updated_at = datetime.now()
        receipt.manually_edited = 1
        db.commit()
        return JSONResponse(content={"success": True, "message": "Receipt updated"})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/receipts/{receipt_id}")
async def delete_receipt(receipt_id: str, db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    db.delete(receipt)
    db.commit()
    return JSONResponse(content={"success": True, "message": "Receipt deleted"})

@app.post("/batches")
async def create_batch(
    name: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        batch = Batch(
            id=str(uuid.uuid4()),
            user_id="demo-user",
            status=BatchStatus.CREATED,
            name=name or f"Batch {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description=description
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return JSONResponse(content={
            "success": True,
            "batch_id": batch.id,
            "name": batch.name,
            "status": batch.status,
        })
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/batches/{batch_id}/upload")
async def upload_to_batch(
    batch_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        uploaded_receipts = []
        for file in files:
            content = await file.read()
            receipt = Receipt(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                filename=file.filename,
                file_size=len(content),
                status="queued",
                created_at=datetime.now()
            )
            db.add(receipt)
            db.flush()
            job_id = TaskQueueService.enqueue_receipt_processing(
                receipt_id=receipt.id,
                batch_id=batch_id,
                file_bytes=content,
                filename=file.filename
            )
            uploaded_receipts.append({
                "receipt_id": receipt.id,
                "filename": file.filename,
                "job_id": job_id,
                "status": "queued"
            })
        batch.total_files = (batch.total_files or 0) + len(files)
        batch.status = BatchStatus.QUEUED
        db.commit()
        return JSONResponse(content={
            "success": True,
            "batch_id": batch_id,
            "uploaded": len(uploaded_receipts),
            "receipts": uploaded_receipts
        })
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/batches/{batch_id}")
async def get_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    progress = TaskQueueService.get_batch_progress(batch_id, db)
    return JSONResponse(content={
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "total_files": batch.total_files,
        "processed_files": batch.processed_files,
        "failed_files": batch.failed_files,
        "progress_percent": batch.progress_percent,
        "total_amount": batch.total_amount,
        "avg_confidence": batch.avg_confidence,
        "progress": progress
    })

@app.get("/batches/{batch_id}/receipts")
async def get_batch_receipts(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    receipts = db.query(Receipt).filter(Receipt.batch_id == batch_id).all()
    return JSONResponse(content={
        "batch_id": batch_id,
        "receipts": [
            {
                "id": r.id,
                "filename": r.filename,
                "status": r.status,
                "merchant": r.merchant_name,
                "total": r.total_amount,
                "category": r.category,
                "confidence": r.confidence_score,
                "error": r.error_message,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None
            }
            for r in receipts
        ]
    })

@app.post("/upload")
async def upload_receipt(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not imagetotable_client:
        return JSONResponse(
            status_code=503,
            content={"error": "ImageToTable.ai client not configured"}
        )
    try:
        content = await file.read()
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            results = imagetotable_client.upload_and_process(tmp_path)
        finally:
            os.unlink(tmp_path)
        documents = results.get("documents", [])
        if not documents:
            return JSONResponse(status_code=400, content={"error": "No data extracted"})
        doc = documents[0]
        receipt_id = str(uuid.uuid4())
        current_time = datetime.now()
        receipt = Receipt(
            id=receipt_id,
            merchant_name=doc.get("merchant", "Unknown"),
            transaction_date=doc.get("date", ""),
            subtotal=doc.get("subtotal", 0),
            tax_amount=doc.get("tax", 0),
            total_amount=doc.get("total", 0),
            line_items=json.dumps(doc.get("line_items", [])),
            status="completed",
            created_at=current_time,
            processed_at=current_time
        )
        db.add(receipt)
        db.commit()
        return JSONResponse(content={
            "success": True,
            "receipt_id": receipt_id,
            "data": doc
        })
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/export")
async def export_receipts(db: Session = Depends(get_db)):
    receipts = db.query(Receipt).order_by(Receipt.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Merchant', 'Date', 'Amount', 'Currency',
        'Document Type', 'Document #', 'Client Name', 'Due Date',
        'Tax Type', 'Tax Year', 'Income', 'Expense', 'Tax Paid',
        'Category', 'Confidence', 'Status'
    ])
    for r in receipts:
        writer.writerow([
            r.merchant_name or 'Unknown',
            r.transaction_date or 'N/A',
            r.total_amount or 0,
            r.currency or 'USD',
            r.document_type or 'expense',
            r.document_number or '',
            r.client_name or '',
            r.due_date or '',
            r.tax_type or '',
            r.tax_year or '',
            r.income_amount or 0,
            r.expense_amount or 0,
            r.tax_amount_paid or 0,
            r.category or 'Uncategorized',
            f"{(r.confidence_score or 0) * 100:.0f}%",
            r.status or 'processed'
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=receipts_export.csv"}
    )

@app.post("/reports/generate")
async def generate_report(request: Request, db: Session = Depends(get_db)):
    filters = await request.json()
    receipts = db.query(Receipt).all()
    summary = {
        'total_receipts': len(receipts),
        'total_income': sum(r.income_amount or 0 for r in receipts if r.document_type == 'invoice'),
        'total_expenses': sum(r.expense_amount or 0 for r in receipts if r.document_type == 'expense'),
        'total_tax': sum(r.tax_amount_paid or 0 for r in receipts if r.document_type == 'tax'),
    }
    summary['net_income'] = summary['total_income'] - summary['total_expenses']
    return JSONResponse(content={'summary': summary, 'receipts': []})

if __name__ == '__main__':
    print("[START] Starting ReadReceipts API v2.0")
    uvicorn.run(app, host="0.0.0.0", port=8000)

