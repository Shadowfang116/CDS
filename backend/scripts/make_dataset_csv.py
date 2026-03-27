"""
Create a dataset CSV for classification evaluation from a folder of documents.

Usage:
  python -c "import sys,os; sys.path.insert(0, r'C:\\path\\to\\backend'); from scripts.make_dataset_csv import main; main()" \
    --input_dir C:\\docs \
    --output C:\\dataset.csv

It writes a CSV with columns: filename,actual_type,text
- actual_type left blank for manual labeling
- if a sidecar .txt with same stem exists, it is loaded as 'text'
"""
import argparse
import csv
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--glob", default="*.pdf", help="File glob, e.g., *.pdf or *.jpg")
    args = ap.parse_args()

    in_dir = Path(args.input_dir)
    rows = []
    for p in sorted(in_dir.rglob(args.glob)):
        text = ""
        txt = p.with_suffix(".txt")
        if txt.exists():
            try:
                text = txt.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
        rows.append({"filename": p.name, "actual_type": "", "text": text})

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "actual_type", "text"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()

