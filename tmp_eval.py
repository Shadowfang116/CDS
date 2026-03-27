from app.services.doc_classifier import classify_document
samples=[
    ("Chain mutation.pdf", None),
    ("Completion Certificate .pdf", None),
]
for name, text in samples:
    pred, conf, det = classify_document(name, text)
    print(name, "->", pred, conf, det)
