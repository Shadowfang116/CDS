import csv
from app.services.doc_classifier import classify_document
path="/app/dataset_eval.csv"
rows=[]
with open(path, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

mist=[]
for r in rows:
    filename=r["filename"]
    actual=r["actual_type"]
    text=r.get("text")
    pred, conf, _ = classify_document(filename, text)
    if actual=="unknown" and pred!="unknown":
        mist.append((filename, pred))

print("unknown-misclassified:", len(mist))
for fn,p in mist:
    print(p, "<-", fn)
