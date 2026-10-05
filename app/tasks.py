# app/tasks.py — updated with HEIC conversion
import os
import json
import tempfile
import logging
from datetime import datetime

from PIL import Image
from app.database import SessionLocal
from app.models.receipt import Receipt
from app.models.batch import Batch
from imagetotable_client import ImageToTableClient
from pillow_heif import register_heif_opener

register_heif_opener()

logger = logging.getLogger(__name__)


def safe_float(val):
    if val is None:
        return 0.0
    if isinstance(val, str):
        val = val.replace(",", "").replace("$", "").strip()
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


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

        # Save incoming bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name

        # Detect and convert HEIC to JPEG if needed
        jpg_path = tmp_path
        try:
            img = Image.open(tmp_path)
            if img.format in ("HEIF", "HEIC") or tmp_path.endswith(".heic"):
                logger.info(f"Converting HEIC to JPEG for {receipt_id}")
                jpg_path = tmp_path + ".jpg"
                rgb_img = img.convert("RGB")
                rgb_img.save(jpg_path, "JPEG", quality=90)
                logger.info(f"Converted to {jpg_path}")
        except Exception as e:
            logger.warning(f"Image conversion check failed: {e}")
            # Use original file if conversion check fails
            jpg_path = tmp_path

        try:
            client = ImageToTableClient(os.getenv("IMAGETOTABLE_API_KEY"))
            results = client.upload_and_process(jpg_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if jpg_path != tmp_path and os.path.exists(jpg_path):
                os.unlink(jpg_path)

        documents = results.get("documents", [])
        if not documents:
            raise ValueError("No data extracted from receipt")

        doc = documents[0]
        line_items = doc.get("line_items", [])
        extracted = line_items[0] if line_items else {}

        receipt.merchant_name = extracted.get("merchant_name") or "Unknown"
        receipt.transaction_date = extracted.get("transaction_date") or ""
        receipt.subtotal = safe_float(extracted.get("subtotal"))
        receipt.tax_amount = safe_float(extracted.get("tax_amount"))
        receipt.total_amount = safe_float(extracted.get("total_amount"))
        receipt.line_items = json.dumps(extracted.get("line_items", ""))
        receipt.category = extracted.get("category", "Uncategorized")
        receipt.document_type = extracted.get("document_type", "expense")
        receipt.status = "completed"
        receipt.processed_at = datetime.now()
        receipt.confidence_score = 0.95

        db.commit()
        logger.info(f"Successfully processed receipt {receipt_id}")

        return {"receipt_id": receipt_id, "status": "completed"}

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing receipt {receipt_id}: {e}")
        try:
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if receipt:
                receipt.status = "failed"
                receipt.error_message = str(e)
                db.commit()
        except Exception as inner:
            logger.error(f"Failed to mark receipt as failed: {inner}")
        raise
    finally:
        db.close()
