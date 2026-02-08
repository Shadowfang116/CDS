#!/usr/bin/env python3
"""
Seed the specific test case and documents for Prompt 5/18 testing with hardcoded UUIDs.
Creates case f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8 with sale deed and fard documents.
"""
import sys
import os
import uuid
from datetime import datetime

# Add /app to path (when running in container, /app is the backend root)
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.org import Org
from app.models.user import User, UserOrgRole
from app.models.case import Case
from app.models.document import Document, DocumentPage
from app.services.storage import put_object_bytes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io


def create_urdu_pdf(title: str, content: str) -> bytes:
    """Create a simple PDF with Urdu content (as placeholder)."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, title)
    
    # Content
    c.setFont("Helvetica", 12)
    y = height - 100
    for line in content.split('\n'):
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, line[:80])
        y -= 20
    
    c.save()
    buffer.seek(0)
    return buffer.read()


def seed_prompt5_test_data():
    """Seed the specific test case and documents with hardcoded UUIDs."""
    db: Session = SessionLocal()
    
    try:
        print("Seeding Prompt 5 test data with specific UUIDs...")
        
        # Get OrgA (must exist)
        org_a = db.query(Org).filter(Org.name == "OrgA").first()
        if not org_a:
            raise ValueError("OrgA not found - run pilot_reset.ps1 first")
        
        # Get or create admin user
        admin_user = db.query(User).filter(User.email == "admin@orga.com").first()
        if not admin_user:
            raise ValueError("admin@orga.com not found - run pilot_reset.ps1 first")
        
        # Hardcoded IDs from prompt5_collect_evidence.ps1
        CASE_ID = uuid.UUID("f14f2276-96c0-4f06-aea8-5a9c9eb9a9c8")
        SALE_DEED_DOC_ID = uuid.UUID("8fa48b2d-c169-450e-8b16-8855b6a83def")
        FARD_DOC_ID = uuid.UUID("a81b1693-63b4-4f94-b22e-21624d432c58")
        
        # Create or get case
        test_case = db.query(Case).filter(Case.id == CASE_ID).first()
        if not test_case:
            test_case = Case(
                id=CASE_ID,
                org_id=org_a.id,
                title="PROMPT 5 TEST CASE - Sale Deed + Fard",
                status="New",
            )
            db.add(test_case)
            db.flush()
            print(f"Created test case: {test_case.id}")
        else:
            print(f"Test case already exists: {test_case.id}")
        
        # Create sale deed document
        sale_deed_doc = db.query(Document).filter(Document.id == SALE_DEED_DOC_ID).first()
        if not sale_deed_doc:
            # Create synthetic sale deed PDF (Urdu content)
            sale_deed_content = """SALE DEED - بیع نامہ
            
This is a test sale deed document with Urdu text.
The document should contain seller, buyer, and witness names.

فروخت کنندہ (Seller): کاشف زابد
خریدار (Buyer): محمد علی
گواہ (Witness): احمد رضا

Property details and terms of sale.
"""
            pdf_content = create_urdu_pdf("Sale Deed", sale_deed_content)
            
            # Upload to MinIO
            minio_key_sale_deed = f"org/{org_a.id}/cases/{CASE_ID}/docs/{SALE_DEED_DOC_ID}/original.pdf"
            put_object_bytes(minio_key_sale_deed, pdf_content, "application/pdf")
            
            sale_deed_doc = Document(
                id=SALE_DEED_DOC_ID,
                org_id=org_a.id,
                case_id=CASE_ID,
                uploader_user_id=admin_user.id,
                original_filename="sale_deed.pdf",
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key_sale_deed,
                page_count=3,
                status="Split",
                doc_type="sale_deed",
                doc_type_source="manual",
            )
            db.add(sale_deed_doc)
            db.flush()
            
            # Create pages for sale deed
            for page_num in range(1, 4):  # 3 pages
                page_minio_key = f"org/{org_a.id}/cases/{CASE_ID}/docs/{SALE_DEED_DOC_ID}/pages/{page_num}.pdf"
                # Upload placeholder page PDF
                page_pdf = create_urdu_pdf(f"Sale Deed Page {page_num}", f"Page {page_num} content")
                put_object_bytes(page_minio_key, page_pdf, "application/pdf")
                
                page = DocumentPage(
                    org_id=org_a.id,
                    document_id=SALE_DEED_DOC_ID,
                    page_number=page_num,
                    minio_key_page_pdf=page_minio_key,
                    ocr_status="NotStarted",
                )
                db.add(page)
            
            db.flush()
            print(f"Created sale deed document: {sale_deed_doc.id} with 3 pages")
        else:
            print(f"Sale deed document already exists: {sale_deed_doc.id}")
        
        # Create fard document
        fard_doc = db.query(Document).filter(Document.id == FARD_DOC_ID).first()
        if not fard_doc:
            # Create synthetic fard PDF
            fard_content = """FARD DOCUMENT
            
This is a test fard document.
It should NOT contain party role information.

Property registration details only.
"""
            pdf_content = create_urdu_pdf("Fard", fard_content)
            
            # Upload to MinIO
            minio_key_fard = f"org/{org_a.id}/cases/{CASE_ID}/docs/{FARD_DOC_ID}/original.pdf"
            put_object_bytes(minio_key_fard, pdf_content, "application/pdf")
            
            fard_doc = Document(
                id=FARD_DOC_ID,
                org_id=org_a.id,
                case_id=CASE_ID,
                uploader_user_id=admin_user.id,
                original_filename="fard.pdf",
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key_fard,
                page_count=2,
                status="Split",
                doc_type="fard",
                doc_type_source="manual",
            )
            db.add(fard_doc)
            db.flush()
            
            # Create pages for fard
            for page_num in range(1, 3):  # 2 pages
                page_minio_key = f"org/{org_a.id}/cases/{CASE_ID}/docs/{FARD_DOC_ID}/pages/{page_num}.pdf"
                # Upload placeholder page PDF
                page_pdf = create_urdu_pdf(f"Fard Page {page_num}", f"Page {page_num} content")
                put_object_bytes(page_minio_key, page_pdf, "application/pdf")
                
                page = DocumentPage(
                    org_id=org_a.id,
                    document_id=FARD_DOC_ID,
                    page_number=page_num,
                    minio_key_page_pdf=page_minio_key,
                    ocr_status="NotStarted",
                )
                db.add(page)
            
            db.flush()
            print(f"Created fard document: {fard_doc.id} with 2 pages")
        else:
            print(f"Fard document already exists: {fard_doc.id}")
        
        db.commit()
        print("\n[OK] Prompt 5 test data seeded successfully!")
        print(f"\nCase ID: {CASE_ID}")
        print(f"Sale Deed Doc ID: {SALE_DEED_DOC_ID}")
        print(f"Fard Doc ID: {FARD_DOC_ID}")
        
    except Exception as e:
        db.rollback()
        print(f"\n[FAIL] Failed to seed test data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_prompt5_test_data()
