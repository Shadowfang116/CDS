"""
Evaluate document classification accuracy.

Usage:
  python -m backend.scripts.evaluate_classification --csv path/to/samples.csv

CSV format (header required):
  filename,actual_type
  SALE_DEED_123.pdf,sale_deed
  noc_society.pdf,society_noc

If --csv is omitted, a tiny built-in sample is used.
"""
import argparse
import csv
from collections import Counter, defaultdict
from typing import List, Tuple

from app.models.document import DocumentType
from app.services.doc_classifier import classify_document


def classify_filename(name: str, text: str | None = None) -> str:
    """Heuristic classifier using the same logic as the API."""
    dt, _conf, _ = classify_document(name, ocr_text=text)
    return dt


def load_samples(csv_path: str | None) -> List[Tuple[str, str, str | None]]:
    if not csv_path:
        return [
            ("sale_deed_abc.pdf", DocumentType.SALE_DEED.value, "sale deed of residential plot"),
            ("registry_2023.pdf", DocumentType.REGISTRY_DEED.value, "registered deed no. 123 by sub-registrar"),
            ("society_noc_alpha.pdf", DocumentType.SOCIETY_NOC.value, "no objection certificate for mortgage permission"),
            ("unknown_doc.pdf", DocumentType.UNKNOWN.value, "document"),
        ]
    rows: List[Tuple[str, str, str | None]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((r.get("filename", ""), r.get("actual_type", ""), r.get("text")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="Path to CSV of samples", default=None)
    args = ap.parse_args()

    samples = load_samples(args.csv)
    if not samples:
        print("No samples found")
        return

    total = 0
    correct = 0
    per_type = Counter()
    per_type_correct = Counter()
    confusion = defaultdict(Counter)

    for sample in samples:
        if len(sample) == 3:
            filename, actual, text = sample
        else:
            filename, actual = sample[0], sample[1]
            text = None
        pred = classify_filename(filename, text)
        total += 1
        per_type[actual] += 1
        if pred == actual:
            correct += 1
            per_type_correct[actual] += 1
        else:
            confusion[actual][pred] += 1

    accuracy = (correct / total * 100.0) if total else 0.0
    print(f"Accuracy: {accuracy:.0f}%\n")

    for t in DocumentType:
        if per_type[t.value]:
            pct = per_type_correct[t.value] / per_type[t.value] * 100.0
            print(f"{t.value}: {pct:.0f}%")
    print()

    print("Confusion:")
    for actual, preds in confusion.items():
        for pred, count in preds.items():
            print(f"{actual} -> {pred} ({count} cases)")


if __name__ == "__main__":
    main()
