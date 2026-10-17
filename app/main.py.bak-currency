# app/main.py
import os
import uuid
import json
import io
import csv
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, Query
from fastapi.encoders import jsonable_encoder
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


def parse_line_items(raw):
    """Handle line_items that may be JSON, plain string, or None."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except (json.JSONDecodeError, TypeError):
                pass
        return [stripped]
    return []


def parse_json_safe(raw, default):
    """Safely parse a JSON string field, returning default on failure."""
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def parse_date_param(value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    """Parse a YYYY-MM-DD date string into a datetime. Returns None if invalid."""
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        if end_of_day:
            dt = dt + timedelta(days=1) - timedelta(seconds=1)
        return dt
    except (ValueError, TypeError):
        return None


def apply_receipt_filters(
    query,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    category: Optional[str] = None,
):
    """Apply filter conditions to a SQLAlchemy query. All params are optional."""
    start_dt = parse_date_param(start_date, end_of_day=False)
    end_dt = parse_date_param(end_date, end_of_day=True)

    if start_dt:
        query = query.filter(Receipt.transaction_date >= start_date)
    if end_dt:
        query = query.filter(Receipt.transaction_date <= end_date)
    if status:
        query = query.filter(Receipt.status == status)
    if batch_id:
        query = query.filter(Receipt.batch_id == batch_id)
    if category:
        query = query.filter(Receipt.category == category)

    return query


def apply_sort(query, sort: Optional[str] = None):
    """Apply sorting to a SQLAlchemy query on Receipt."""
    if sort == "date_asc":
        return query.order_by(Receipt.transaction_date.asc())
    if sort == "amount_desc":
        return query.order_by(Receipt.total_amount.desc())
    if sort == "amount_asc":
        return query.order_by(Receipt.total_amount.asc())
    if sort == "merchant_asc":
        return query.order_by(Receipt.merchant_name.asc())
    # default: newest first
    return query.order_by(Receipt.transaction_date.desc())


def serialize_receipt_summary(r: Receipt):
    """Compact representation for the list view."""
    return {
        "id": r.id,
        "merchant_name": r.merchant_name or 'Unknown Merchant',
        "merchant_name_en": r.merchant_name_en or r.merchant_name,
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
async def get_receipts(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    status: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query(None, description="date_desc|date_asc|amount_desc|amount_asc|merchant_asc"),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Receipt)
        query = apply_receipt_filters(query, start_date, end_date, status, batch_id, category)
        query = apply_sort(query, sort)
        receipts = query.all()

        return JSONResponse(content={
            "count": len(receipts),
            "receipts": [serialize_receipt_summary(r) for r in receipts],
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "batch_id": batch_id,
                "category": category,
                "sort": sort or "date_desc",
            },
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

    return JSONResponse(content=jsonable_encoder({
        "id": receipt.id,
        "merchant_name": receipt.merchant_name,
        "merchant_address": receipt.merchant_address,
        "transaction_date": receipt.transaction_date,
        "subtotal": receipt.subtotal or 0,
        "total_amount": receipt.total_amount or 0,
        "tax_amount": receipt.tax_amount or 0,
        "currency": receipt.currency or 'USD',
        "filename": receipt.filename,
        "image_path": receipt.image_path,
        "storage_path": receipt.storage_path,
        "created_at": receipt.created_at,
        "updated_at": receipt.updated_at,
        "processed_at": receipt.processed_at,
        "confidence_score": receipt.confidence_score or 0,
        "status": receipt.status,
        "category": receipt.category,
        "document_type": receipt.document_type,
        "document_number": receipt.document_number,
        "client_name": receipt.client_name,
        "client_address": receipt.client_address,
        "due_date": receipt.due_date,
        "tax_type": receipt.tax_type,
        "tax_year": receipt.tax_year,
        "income_amount": receipt.income_amount or 0,
        "expense_amount": receipt.expense_amount or 0,
        "tax_amount_paid": receipt.tax_amount_paid or 0,
        "line_items": parse_line_items(receipt.line_items),
        "line_items_count": receipt.line_items_count,
        "parsed_data": parse_json_safe(receipt.parsed_data, {}),
        "normalized_json": receipt.normalized_json,
        "error_message": receipt.error_message,
        "batch_id": receipt.batch_id,
    }))

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

@app.post("/receipts/{receipt_id}/retry")
async def retry_receipt(receipt_id: str, db: Session = Depends(get_db)):
    """Reset a failed receipt so it can be re-uploaded and reprocessed."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if receipt.status != "failed":
        return JSONResponse(
            status_code=400,
            content={"error": f"Only failed receipts can be retried. Current status: {receipt.status}"}
        )

    receipt.status = "queued"
    receipt.error_message = None
    receipt.confidence_score = 0
    receipt.updated_at = datetime.now()
    db.commit()

    return JSONResponse(content={
        "success": True,
        "receipt_id": receipt_id,
        "message": "Receipt reset. Please re-upload the image to process it again.",
        "batch_id": receipt.batch_id,
    })

@app.post("/receipts/{receipt_id}/reprocess")
async def reprocess_receipt(receipt_id: str, db: Session = Depends(get_db)):
    """
    Re-run OCR on a receipt using its saved original file.
    Requires that the file was persisted during the first processing run.
    """
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if not receipt.file_bytes:
        return JSONResponse(
            status_code=400,
            content={"error": "Original file not available for reprocessing"}
        )

    if not receipt.batch_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Receipt is not associated with a batch"}
        )

    try:
        file_bytes = bytes(receipt.file_bytes)

        receipt.status = "queued"
        receipt.error_message = None
        db.commit()

        job_id = TaskQueueService.enqueue_receipt_processing(
            receipt_id=receipt.id,
            batch_id=receipt.batch_id,
            file_bytes=file_bytes,
            filename=receipt.filename or "receipt.jpg"
        )

        return JSONResponse(content={
            "success": True,
            "receipt_id": receipt_id,
            "job_id": job_id,
            "message": "Receipt re-queued for processing"
        })
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/admin/reprocess-all")
async def reprocess_all(db: Session = Depends(get_db)):
    """
    Re-queue every receipt that has a saved original file.
    Useful when you change the OCR prompt or model.
    """
    receipts = db.query(Receipt).filter(Receipt.file_bytes.isnot(None)).all()
    queued = 0
    skipped = 0
    errors = []

    for r in receipts:
        if not r.file_bytes:
            skipped += 1
            continue
        if not r.batch_id:
            skipped += 1
            continue

        try:
            file_bytes = bytes(r.file_bytes)

            r.status = "queued"
            r.error_message = None
            db.commit()

            TaskQueueService.enqueue_receipt_processing(
                receipt_id=r.id,
                batch_id=r.batch_id,
                file_bytes=file_bytes,
                filename=r.filename or "receipt.jpg"
            )
            queued += 1
        except Exception as e:
            errors.append(f"{r.id}: {e}")

    return JSONResponse(content={
        "success": True,
        "queued": queued,
        "skipped": skipped,
        "errors": errors,
        "total_matched": len(receipts)
    })

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
    return JSONResponse(content=jsonable_encoder({
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
    }))

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
async def export_receipts(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    status: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    format: Optional[str] = Query("csv", description="csv|json"),
    db: Session = Depends(get_db)
):
    query = db.query(Receipt)
    query = apply_receipt_filters(query, start_date, end_date, status, batch_id, category)
    query = apply_sort(query, sort)
    receipts = query.all()

    # JSON export
    if format == "json":
        return JSONResponse(content={
            "count": len(receipts),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "batch_id": batch_id,
                "category": category,
                "sort": sort or "date_desc",
            },
            "receipts": [
                {
                    "id": r.id,
                    "merchant_name": r.merchant_name or 'Unknown',
                    "merchant_address": r.merchant_address or '',
                    "transaction_date": r.transaction_date or '',
                    "subtotal": r.subtotal or 0,
                    "tax_amount": r.tax_amount or 0,
                    "total_amount": r.total_amount or 0,
                    "currency": r.currency or 'USD',
                    "category": r.category or 'Uncategorized',
                    "document_type": r.document_type or 'expense',
                    "document_number": r.document_number or '',
                    "client_name": r.client_name or '',
                    "due_date": r.due_date or '',
                    "tax_type": r.tax_type or '',
                    "tax_year": r.tax_year or '',
                    "income_amount": r.income_amount or 0,
                    "expense_amount": r.expense_amount or 0,
                    "tax_amount_paid": r.tax_amount_paid or 0,
                    "line_items": parse_line_items(r.line_items),
                    "confidence_score": r.confidence_score or 0,
                    "status": r.status or 'processed',
                    "batch_id": r.batch_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in receipts
            ],
        })

    # CSV export
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