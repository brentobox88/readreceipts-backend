"""
Run the eval: for each receipt in test_set.csv, call Qwen and compare
against ground truth in the CSV.

Run: python -m evaluation.run_eval
"""
import csv
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluation.metrics import (
    FieldResult, normalize_amount, normalize_date, normalize_text
)

FIXTURES = Path(__file__).parent / "fixtures"
TEST_SET = Path(__file__).parent / "test_set.csv"
LAST_RUN = Path(__file__).parent / "last_run.json"


def _safe_num(value):
    """Parse '168,000' or '$168.00' or 168.0 to float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _get(d, *keys):
    """Return the first non-None value from candidate keys."""
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def extract_one(image_bytes):
    """Synchronous Qwen call, production-equivalent preprocessing."""
    from qwen_client import QwenClient
    from PIL import Image
    from pillow_heif import register_heif_opener

    register_heif_opener()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    jpg_path = tmp_path + ".jpg"
    try:
        img = Image.open(tmp_path).convert("RGB")
        max_dim = 1600
        w, h = img.size
        if max(w, h) > max_dim:
            s = max_dim / max(w, h)
            img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
        img.save(jpg_path, "JPEG", quality=80, optimize=True)
        return QwenClient().process_image_file(jpg_path)
    finally:
        for p in (tmp_path, jpg_path):
            if os.path.exists(p):
                os.unlink(p)


def run():
    if not TEST_SET.exists():
        print(f"ERROR: {TEST_SET} not found")
        return

    results = {
        "merchant": FieldResult("merchant"),
        "total": FieldResult("total"),
        "date": FieldResult("date"),
        "tax": FieldResult("tax"),
    }
    rows = list(csv.DictReader(TEST_SET.open(encoding="utf-8")))
    if not rows:
        print("ERROR: test_set.csv is empty")
        return

    for i, row in enumerate(rows, 1):
        img_path = FIXTURES / row["image_file"]
        if not img_path.exists():
            print(f"[{i}/{len(rows)}] SKIP missing {row['image_file']}")
            continue
        print(f"[{i}/{len(rows)}] {row['image_file']}")

        try:
            ex = extract_one(img_path.read_bytes())
        except Exception as e:
            print(f"    QWEN ERROR: {e}")
            continue

        # Qwen uses snake_case field names that match the DB model
        got_merchant = _get(ex, "merchant_name", "merchant")
        got_total = _get(ex, "total_amount", "total")
        got_date = _get(ex, "transaction_date", "date")
        got_tax = _get(ex, "tax_amount", "tax")

        # merchant: substring match
        exp_m = normalize_text(row.get("expected_merchant"))
        got_m = normalize_text(got_merchant)
        results["merchant"].total += 1
        if exp_m and got_m and exp_m in got_m:
            results["merchant"].correct += 1

        # total, tax: exact after normalization
        exp_total = normalize_amount(row.get("expected_total"))
        got_total_v = normalize_amount(_safe_num(got_total))
        results["total"].total += 1
        if exp_total is not None and got_total_v is not None and abs(exp_total - got_total_v) < 0.01:
            results["total"].correct += 1

        exp_tax = normalize_amount(row.get("expected_tax"))
        got_tax_v = normalize_amount(_safe_num(got_tax))
        results["tax"].total += 1
        if exp_tax is not None and got_tax_v is not None and abs(exp_tax - got_tax_v) < 0.01:
            results["tax"].correct += 1

        # date: exact after normalization
        exp_d = normalize_date(row.get("expected_date"))
        got_d = normalize_date(got_date)
        results["date"].total += 1
        if exp_d and got_d and exp_d == got_d:
            results["date"].correct += 1

    print(f"\n{'Field':<12}{'Correct':<10}{'Total':<10}{'Accuracy':<10}")
    print("-" * 42)
    for name, r in results.items():
        print(f"{name:<12}{r.correct:<10}{r.total:<10}{r.accuracy:.1%}")

    LAST_RUN.write_text(json.dumps(
        {n: {"correct": r.correct, "total": r.total, "accuracy": r.accuracy}
         for n, r in results.items()}, indent=2
    ), encoding="utf-8")
    print(f"\nSaved: {LAST_RUN}")


if __name__ == "__main__":
    run()