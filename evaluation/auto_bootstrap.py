"""
Bootstrap test_set.csv from prod receipts using a judge model.
Run: python -m evaluation.auto_bootstrap
Requires: OPENAI_API_KEY in .env
"""
import os, csv, base64, json
from pathlib import Path
import requests

from dotenv import load_dotenv
load_dotenv()

API = "https://readreceipts-api-sxyz.onrender.com"
FIXTURES = Path(__file__).parent / "fixtures"
OUT = Path(__file__).parent / "test_set.csv"
REVIEW = Path(__file__).parent / "needs_review.csv"


def fetch_completed(limit=None):
    resp = requests.get(f"{API}/receipts", timeout=60).json()
    done = [r for r in resp["receipts"] if r["status"] == "completed"]
    return done[:limit] if limit else done




def looks_like_image(data):
    """Check magic bytes for PNG, JPEG, GIF, WebP, or HEIC."""
    if not data or len(data) < 12:
        return False
    if data[:3] == b'\xff\xd8\xff':
        return True                      # JPEG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return True                      # PNG
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return True                      # GIF
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return True                      # WebP
    # HEIC / HEIF: ftyp box at offset 4
    if len(data) >= 12 and data[4:8] == b'ftyp':
        return True
    return False

def fetch_image(receipt_id):
    """Fetch image via the durable endpoint (reads from Postgres file_bytes)."""
    r = requests.get(f"{API}/receipts/{receipt_id}/image", timeout=60)
    if r.ok and r.headers.get("content-type", "").startswith("image"):
        content = r.content
        return content if looks_like_image(content) else None
    return None




def _safe_num(value):
    """Parse number from string like '168,000' or '\.00' or 168.0."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    import re
    # Remove currency symbols, spaces, thousand separators, keep digits/dot/minus
    cleaned = re.sub(r'[^0-9.\-]', '', str(value))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def judge_with_openai(image_bytes):
    from openai import OpenAI
    client = OpenAI()
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text":
                 "Extract from this receipt. Return ONLY JSON with keys: "
                 "merchant_name, transaction_date (YYYY-MM-DD), total_amount, "
                 "tax_amount. Use null for missing."},
                {"type": "image_url", "image_url":
                 {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def run():
    completed = fetch_completed()
    print(f"Found {len(completed)} completed receipts")
    agreed, disagreed = [], []

    for i, r in enumerate(completed, 1):
        print(f"[{i}/{len(completed)}] {r['id'][:8]}...", end=" ")
        img = fetch_image(r["id"])
        if not img:
            print("NO IMAGE")
            continue
        (FIXTURES / f"{r['id']}.jpg").write_bytes(img)

        try:
            judge = judge_with_openai(img)
        except Exception as e:
            err = str(e)
            if 'invalid_image_format' in err or 'unsupported image' in err.lower():
                print('SKIP: unsupported format (not JPEG/PNG)')
            else:
                print(f"JUDGE ERROR: {err[:200]}")
            continue

        db_total = round(_safe_num(r.get("total_amount")), 2)
        jd_total = round(_safe_num(judge.get("total_amount")), 2)
        match = abs(db_total - jd_total) < 0.01

        row = {
            "image_file": f"{r['id']}.jpg",
            "expected_merchant": judge.get("merchant_name") or "",
            "expected_total": jd_total,
            "expected_date": judge.get("transaction_date") or "",
            "expected_tax": round(_safe_num(judge.get("tax_amount")), 2),
            "db_total": db_total,
            "db_merchant": r.get("merchant_name") or "",
            "agreement": "yes" if match else "no",
        }
        (agreed if match else disagreed).append(row)
        print("AGREE" if match else "DISAGREE")

    with OUT.open("w", newline="", encoding="utf-8") as f:
        cols = ["image_file", "expected_merchant", "expected_total",
                "expected_date", "expected_tax"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(agreed)

    with REVIEW.open("w", newline="", encoding="utf-8") as f:
        if disagreed:
            w = csv.DictWriter(f, fieldnames=list(disagreed[0].keys()))
        else:
            w = csv.DictWriter(f, fieldnames=["image_file", "agreement"])
        w.writeheader(); w.writerows(disagreed)

    print(f"\nOK {len(agreed)} agreed -> test_set.csv")
    print(f"WARN {len(disagreed)} disagreed -> needs_review.csv")


if __name__ == "__main__":
    run()