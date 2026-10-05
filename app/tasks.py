# app/tasks.py
import logging
import json
import os
import tempfile
from datetime import datetime
from app.database import SessionLocal
from app.models.receipt import Receipt
from app.models.batch import Batch, BatchStatus
from imagetotable_client import ImageToTableClient
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def process_receipt_task(
    receipt_id: str,
    batch_id: str,
    file_bytes: bytes,
    filename: str
) -> dict:
    """
    Background task to process a single receipt using ImageToTable.ai
    """
    db = SessionLocal()
    receipt = None
    batch = None
    
    try:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        
        if not receipt or not batch:
            raise ValueError(f"Receipt {receipt_id} or Batch {batch_id} not found")
        
        receipt.status = "processing"
        db.commit()
        
        logger.info(f"Processing receipt {receipt_id} from batch {batch_id}")
        
        # Step 1: OCR via ImageToTable.ai
        imagetotable_client = ImageToTableClient(os.getenv("IMAGETOTABLE_API_KEY"))
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        
        try:
            results = imagetotable_client.upload_and_process(tmp_path)
        finally:
            os.unlink(tmp_path)
        
        documents = results.get("documents", [])
        if not documents:
            raise ValueError("No data extracted from receipt")
        
        doc = documents[0]
        
        # ImageToTable nests extracted fields inside line_items[0]
        line_items = doc.get("line_items", [])
        extracted = line_items[0] if line_items else {}
        
        def safe_float(val):
            if val is None:
                return 0.0
            if isinstance(val, str):
                val = val.replace(",", "").replace("$", "").strip()
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        
        # Step 2: Update receipt with extracted data
        receipt.merchant_name = extracted.get("merchant_name") or extracted.get("vendor_name") or "Unknown"
        receipt.transaction_date = extracted.get("transaction_date") or extracted.get("invoice_date") or ""
        receipt.subtotal = safe_float(extracted.get("subtotal"))
        receipt.tax_amount = safe_float(extracted.get("tax_amount") or extracted.get("tax"))
        receipt.total_amount = safe_float(extracted.get("total_amount") or extracted.get("total"))
        receipt.line_items = json.dumps(extracted.get("line_items", []))
        receipt.category = extracted.get("category", "Uncategorized")
        receipt.document_type = extracted.get("document_type", "expense")
        receipt.status = "completed"
        receipt.processed_at = datetime.now()
        receipt.confidence_score = 0.95
        
        db.commit()
        logger.info(f"Successfully processed receipt {receipt_id}")
        
        # Update batch progress
        _update_batch_progress(batch_id, db)
        
        return {
            "receipt_id": receipt_id,
            "status": "completed",
            "merchant": receipt.merchant_name,
            "total": receipt.total_amount,
            "category": receipt.category
        }
        
    except Exception as e:
        logger.error(f"Error processing receipt {receipt_id}: {str(e)}", exc_info=True)
        
        if receipt:
            receipt.status = "failed"
            receipt.error_message = str(e)
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
        
        if batch:
            batch.failed_files = (batch.failed_files or 0) + 1
            _update_batch_progress(batch_id, db)
        
        return {
            "receipt_id": receipt_id,
            "status": "failed",
            "error": str(e)
        }
    
    finally:
        db.close()

def _update_batch_progress(batch_id: str, db):
    """Update batch progress metrics"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    
    receipts = db.query(Receipt).filter(Receipt.batch_id == batch_id).all()
    
    completed = sum(1 for r in receipts if r.status == "completed")
    failed = sum(1 for r in receipts if r.status == "failed")
    processing = sum(1 for r in receipts if r.status == "processing")
    
    batch.processed_files = completed + failed
    batch.failed_files = failed
    batch.progress_percent = (batch.processed_files / batch.total_files * 100) if batch.total_files else 0
    
    if processing == 0:
        if failed == 0:
            batch.status = BatchStatus.COMPLETED
        elif completed == 0:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.PARTIAL
        batch.completed_at = datetime.now()
    
    completed_receipts = [r for r in receipts if r.status == "completed"]
    if completed_receipts:
        batch.total_amount = sum(r.total_amount or 0 for r in completed_receipts)
        confidences = [r.confidence_score for r in completed_receipts if r.confidence_score]
        batch.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    db.commit()


