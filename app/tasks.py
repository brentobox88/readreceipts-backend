# app/tasks.py — Qwen2.5-VL via Runpod
import os
import json
import tempfile
import logging
from datetime import datetime

from PIL import Image
from app.database import SessionLocal
from app.models.receipt import Receipt
from app.models.batch import Batch
from qwen_client import QwenClient
from pillow_heif import register_heif_opener

register_heif_opener()

logger = logging.getLogger(__name__)


def safe_float(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        import re
        cleaned = val.replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if match:
            try:
                return float(match.group(0))
            except (ValueError, TypeError):
                return 0.0
    return 0.0


def _compute_confidence(receipt: Receipt) -> float:
    score = 0.0
    if receipt.merchant_name and receipt.merchant_name.lower() != "unknown":
        score += 0.30
    if receipt.total_amount and receipt.total_amount > 0:
        score += 0.30
    if receipt.transaction_date:
        score += 0.20
    if receipt.tax_amount is not None:
        score += 0.10
    if receipt.line_items_count is not None:
        score += 0.10
    return round(score, 2)


def _update_batch_progress(batch_id, db):
    from sqlalchemy import func
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    total = db.query(func.count(Receipt.id)).filter(Receipt.batch_id == batch_id).scalar() or 0
    completed = db.query(func.count(Receipt.id)).filter(
        Receipt.batch_id == batch_id, Receipt.status == "completed").scalar() or 0
    failed = db.query(func.count(Receipt.id)).filter(
        Receipt.batch_id == batch_id, Receipt.status == "failed").scalar() or 0
    batch.total_files = total
    batch.processed_files = completed
    batch.failed_files = failed
    batch.progress_percent = round(((completed + failed) / total) * 100.0, 2) if total else 0.0
    if total == 0:
        batch.status = "created"
    elif (completed + failed) < total:
        batch.status = "processing"
    elif failed == total:
        batch.status = "failed"
    elif failed > 0:
        batch.status = "partial"
    else:
        batch.status = "completed"
    db.commit()


def process_receipt_task(receipt_id, batch_id, file_bytes, filename):
    db = SessionLocal()
    try:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not receipt or not batch:
            raise ValueError(f"Receipt {receipt_id} or Batch {batch_id} not found")

        receipt.status = "processing"
        db.commit()
        logger.info(f"Processing receipt {receipt_id} from batch {batch_id}")

        try:
            receipt.file_bytes = file_bytes
            receipt.filename = filename
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not save original bytes: {e}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name

        jpg_path = tmp_path + ".jpg"
        try:
            img = Image.open(tmp_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            max_dim = 1600
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                logger.info(f"Resized image from {w}x{h} to {img.size}")
            img.save(jpg_path, "JPEG", quality=80, optimize=True)
            logger.info(f"Compressed to {os.path.getsize(jpg_path)} bytes")
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            jpg_path = tmp_path

        try:
            client = QwenClient()
            raw_extracted = client.process_image_file(jpg_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if jpg_path != tmp_path and os.path.exists(jpg_path):
                os.unlink(jpg_path)

        if not raw_extracted or raw_extracted.get("error"):
            raise ValueError(f"Qwen extraction failed: {raw_extracted}")

        logger.info(f"Raw Qwen output: {raw_extracted}")

        receipt.merchant_name = raw_extracted.get("merchant_name") or "Unknown"
        receipt.merchant_name_en = raw_extracted.get("merchant_name_en") or receipt.merchant_name
        receipt.transaction_date = raw_extracted.get("transaction_date") or ""
        receipt.subtotal = safe_float(raw_extracted.get("subtotal"))
        receipt.tax_amount = safe_float(raw_extracted.get("tax_amount"))
        receipt.total_amount = safe_float(raw_extracted.get("total_amount"))
        receipt.currency = (raw_extracted.get("currency") or "USD").upper()

        li = raw_extracted.get("line_items")
        receipt.line_items = json.dumps(li) if isinstance(li, (list, dict)) else (li or "")
        count_val = raw_extracted.get("line_items_count")
        if count_val is None and isinstance(li, list):
            count_val = len(li)
        receipt.line_items_count = int(count_val) if count_val is not None else None

        receipt.category = raw_extracted.get("category") or "Uncategorized"
        receipt.document_type = raw_extracted.get("document_type") or "expense"
        receipt.raw_document_ai_json = raw_extracted
        receipt.normalized_json = raw_extracted

        receipt.confidence_score = _compute_confidence(receipt)
        receipt.status = "completed"
        receipt.processed_at = datetime.now()
        db.commit()

        logger.info(
            f"Receipt {receipt_id} done "
            f"(confidence={receipt.confidence_score}, "
            f"merchant={receipt.merchant_name}, total={receipt.total_amount})"
        )

        _update_batch_progress(batch_id, db)
        return {"receipt_id": receipt_id, "status": "completed"}

    except Exception as e:
        db.rollback()
        try:
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if receipt:
                receipt.status = "failed"
                receipt.error_message = str(e)
                db.commit()
        except Exception as inner:
            logger.error(f"Failed to mark receipt as failed: {inner}")
        try:
            _update_batch_progress(batch_id, db)
        except Exception as inner:
            logger.error(f"Failed to update batch progress: {inner}")
        raise
    finally:
        db.close()