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
    """Parse a value into a float, stripping currency symbols and labels."""
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


def _update_batch_progress(batch_id, db):
    """Recompute batch progress and status based on its receipts."""
    from sqlalchemy import func

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return

    total = db.query(func.count(Receipt.id)).filter(
        Receipt.batch_id == batch_id
    ).scalar() or 0

    completed = db.query(func.count(Receipt.id)).filter(
        Receipt.batch_id == batch_id,
        Receipt.status == "completed"
    ).scalar() or 0

    failed = db.query(func.count(Receipt.id)).filter(
        Receipt.batch_id == batch_id,
        Receipt.status == "failed"
    ).scalar() or 0

    batch.total_files = total
    batch.processed_files = completed
    batch.failed_files = failed

    if total > 0:
        batch.progress_percent = round(((completed + failed) / total) * 100.0, 2)
    else:
        batch.progress_percent = 0.0

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

        # Save incoming bytes to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name

        # Convert + resize + compress to JPEG for Qwen
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

        # Send to Qwen endpoint
        try:
            client = QwenClient()
            extracted = client.process_image_file(jpg_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if jpg_path != tmp_path and os.path.exists(jpg_path):
                os.unlink(jpg_path)

        if not extracted or extracted.get("error"):
            raise ValueError(f"Qwen extraction failed: {extracted}")

        logger.info(f"Extracted fields: {extracted}")

        # Map Qwen output -> Receipt model
        receipt.merchant_name = extracted.get("merchant_name") or "Unknown"
        receipt.transaction_date = extracted.get("transaction_date") or ""
        receipt.subtotal = safe_float(extracted.get("subtotal"))
        receipt.tax_amount = safe_float(extracted.get("tax_amount"))
        receipt.total_amount = safe_float(extracted.get("total_amount"))
        receipt.line_items = extracted.get("line_items") or ""
        receipt.category = extracted.get("category", "Uncategorized")
        receipt.document_type = extracted.get("document_type", "expense")
        receipt.normalized_json = extracted

        receipt.status = "completed"
        receipt.processed_at = datetime.now()
        receipt.confidence_score = 0.95

        db.commit()
        logger.info(f"Successfully processed receipt {receipt_id}")

        # Update batch progress
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

        # Update batch progress on failure too
        try:
            _update_batch_progress(batch_id, db)
        except Exception as inner:
            logger.error(f"Failed to update batch progress: {inner}")

        raise
    finally:
        db.close()