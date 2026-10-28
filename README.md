# ReadReceipts Backend

FastAPI backend for a bulk receipt scanner. Accepts image uploads from a mobile client, queues them for processing, runs inference on a self-hosted vision-language model, and returns structured receipt data.

**Live app**: in TestFlight (invite-only)
**Mobile repo**: [ReadReceiptsMobile](https://github.com/brentobox88/ReadReceiptsMobile)
**Worker repo**: [runpod-qwen-worker](https://github.com/brentobox88/runpod-qwen-worker)

---

## What it does

A user uploads receipts from their phone. The backend extracts:

- Merchant name
- Transaction date (ISO 8601)
- Subtotal, tax, total
- Currency
- Individual line items with descriptions and amounts
- A per-receipt confidence score computed from field completeness

The mobile client displays extracted fields, allows inline editing, and logs corrections back to the server for eval-set expansion.

---

## Architecture

React Native (Expo) ──► FastAPI (Render) ──► Postgres
│
▼
Redis (Upstash)
│
▼
RQ Worker (Render)
│
▼
Runpod Serverless GPU
vLLM + Qwen2.5-VL-7B-AWQ

**Why each piece:**

- **Postgres over SQLite** — API and worker are separate containers; SQLite is per-container.
- **Redis queue over direct processing** — bulk uploads must not block the API.
- **Runpod serverless** — pay only for active GPU time; scale-to-zero between batches.
- **vLLM over transformers** — pinned dependencies, production-grade serving.
- **Qwen2.5-VL over PaddleOCR-VL** — general-purpose VLMs handle phone photos better than OCR-specific models.

See [`Lessons from v1.md`](Lessons%20from%20v1.md) for the full provider journey (Google Document AI → ImageToTable → PaddleOCR → Qwen).

---

## Accuracy

Measured against 9 hand-verified receipts in `evaluation/fixtures/`. Reproduce with:

```bash
python -m evaluation.run_eval

Field	Correct	Total	Accuracy
Merchant	8	9	88.9%
Total	9	9	100.0%
Date	8	9	88.9%
Tax	9	9	100.0%
Two known failures, both user-correctable via the mobile edit flow:

00fbdf98 — model returns 2023-09-18 for a receipt printed 18/09/26. 2-digit year misread (26 → 23).

1 merchant substring mismatch (name present but formatted differently than expected).

Line items: 15/15 recoverable receipts in the production backlog have populated line_items arrays after the v7 prompt deployment.

Running locally
Prerequisites: Python 3.11, Postgres (or SQLite for dev), Redis

bash
git clone https://github.com/brentobox88/readreceipts-backend
cd readreceipts-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Configure .env with DATABASE_URL, REDIS_URL, RUNPOD_API_KEY, QWEN_ENDPOINT_ID.

bash
uvicorn app.main:app --reload --port 8000
Worker (separate terminal):

bash
python -m rq.cli worker --url $REDIS_URL default
Test the pipeline:

bash
python -m evaluation.run_eval
API endpoints
Method	Path	Purpose
POST	/batches	Create a batch
POST	/batches/{id}/upload	Upload receipts to a batch
GET	/batches/{id}	Poll batch progress
GET	/batches/{id}/receipts	List receipts in a batch
GET	/receipts	List all receipts
GET	/receipts/{id}	Receipt detail
GET	/receipts/{id}/image	Serve receipt image (HEIC→JPEG transcoded)
PUT	/receipts/{id}	Update receipt fields
POST	/receipts/{id}/correction	Log a correction (eval-set expansion)
POST	/receipts/{id}/retry	Retry a failed receipt
GET	/export	CSV/JSON export
POST	/admin/reprocess-all	Re-queue all recoverable receipts
Related
Mobile app: ReadReceiptsMobile

Worker source: runpod-qwen-worker

Lessons learned: Lessons from v1.md

License
MIT