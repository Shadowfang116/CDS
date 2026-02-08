# Pilot Sample Documents

This folder is for storing test documents used during pilot testing.

## Important Notes

⚠️ **DO NOT commit real bank documents or sensitive data to this repository.**

✅ **DO use:**
- Anonymized test documents
- Sample property documents (with PII removed)
- Synthetic documents generated for testing
- Public domain documents

## Folder Structure

Place your test documents here:
- `sample_scanned.pdf` - A scanned PDF document
- `sample_photo.jpg` - A photo of a document (optional)
- `sample_text.pdf` - A text-based PDF (optional)

## Usage

To test with a real document:

```powershell
.\scripts\dev\pilot_real_doc.ps1 -Path "docs\pilot_samples\your_document.pdf"
```

**Important:** You must provide a **real PDF or image file**. Text files or invalid PDFs will cause the upload to fail.

The script will:
1. Create a new test case titled "REAL DOC TEST - <timestamp>"
2. Upload your document (PDF, PNG, or JPG)
3. Wait for document to be split into pages
4. Run OCR automatically
5. Wait for OCR completion (up to 180 seconds)
6. Print the case URL for review

**If upload fails:**
- Verify the file is a valid PDF/image
- Check file size (max 50 MB)
- Check worker logs: `docker compose logs worker --tail=100`

## Document Requirements

- **Format:** PDF, PNG, or JPG
- **Size:** Max 50 MB
- **Pages:** Max 50 pages per document
- **Quality:** Clear, readable text (for OCR)

## Creating Test Documents

If you need to create test documents:

1. **Scanned PDF:** Use a scanner or mobile app to scan a document
2. **Photo:** Take a photo of a document with your phone
3. **Synthetic:** Use reportlab or similar to generate test PDFs

Remember to remove or anonymize any sensitive information before testing.

