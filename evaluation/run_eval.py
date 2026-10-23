import csv
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluation.metrics import (
    FieldResult, normalize_amount, normalize_date, normalize_text
)


def extract_one(image_bytes: bytes) -> dict:
    """Synchronous Qwen call, matching production preprocessing."""
    from qwen_client import QwenClient
    from PIL import Image

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
    fixture_dir = Path(__file__).parent / "fixtures"
    test_set = Path(__file__).parent / "test_set.csv"
    if not test_set.exists():
        print(f"ERROR: {test_set} not found.")
        return

    results = {
        "merchant": FieldResult("merchant"),
        "total": FieldResult("total"),
        "date": FieldResult("date"),
        "tax": FieldResult("tax"),
    }
    rows = list(csv.DictReader(test_set.open(encoding="utf-8")))

    for i, row in enumerate(rows, 1):
        img_path = fixture_dir / row["image_file"]
        if not img_path.exists():
            print(f"[{i}/{len(rows)}] SKIP missing {img_path}")
            continue
        print(f"[{i}/{len(rows)}] {row['image_file']}")
        try:
            ex = extract_one(img_path.read_bytes())
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        exp = normalize_text(row["expected_merchant"])
        got = normalize_text(ex.get("merchant_name") or ex.get("merchant"))
        results["merchant"].total += 1
        if exp and got and exp in got:
            results["merchant"].correct += 1

        for field, qwen_key in (("total", "total_amount"), ("tax", "tax_amount")):
            exp_v = normalize_amount(row[f"expected_{field}"])
            got_v = normalize_amount(ex.get(qwen_key) or ex.get(field))
            results[field].total += 1
            if exp_v is not None and got_v is not None and abs(exp_v - got_v) < 0.01:
                results[field].correct += 1

        exp_d = normalize_date(row["expected_date"])
        got_d = normalize_date(ex.get("transaction_date") or ex.get("date"))
        results["date"].total += 1
        if exp_d and got_d and exp_d == got_d:
            results["date"].correct += 1

    print(f"\n{'Field':<12}{'Correct':<10}{'Total':<10}{'Accuracy':<10}")
    print("-" * 42)
    for name, r in results.items():
        print(f"{name:<12}{r.correct:<10}{r.total:<10}{r.accuracy:.1%}")

    out = Path(__file__).parent / "last_run.json"
    out.write_text(json.dumps(
        {n: {"correct": r.correct, "total": r.total, "accuracy": r.accuracy}
         for n, r in results.items()}, indent=2
    ), encoding="utf-8")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    run()
