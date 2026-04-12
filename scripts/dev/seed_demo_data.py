#!/usr/bin/env python3
"""
Seed realistic demo data for Phase 10 pilot readiness.
Creates OrgA + OrgB with cases, documents, OCR, exceptions, CPs, exports, approvals, digests.
"""
import sys
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add /app to path (when running in container, /app is the backend root)
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.org import Org
from app.models.user import User, UserOrgRole
from app.models.case import Case
from app.models.document import Document, DocumentPage
from app.models.rules import Exception_, ConditionPrecedent
from app.models.export import Export
from app.models.approval import ApprovalRequest
from app.models.digest import DigestSchedule
from app.models.notification import Notification
from app.models.ocr_extraction import OCRExtractionCandidate
from app.core.security import get_password_hash
from app.services.storage import put_object_bytes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

LOCAL_DEMO_PASSWORD = "ChangeMe123!"


def create_synthetic_pdf(title: str, content: str) -> bytes:
    """Create a simple PDF with text."""
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


def seed_demo_data():
    """Seed demo data - idempotent (clears and reseeds)."""
    db: Session = SessionLocal()
    
    try:
        print("Seeding demo data...")
        
        # Clear existing demo data (optional - comment out to keep existing)
        # db.query(Notification).delete()
        # db.query(ApprovalRequest).delete()
        # db.query(Export).delete()
        # db.query(Exception_).delete()
        # db.query(ConditionPrecedent).delete()
        # db.query(DocumentPage).delete()
        # db.query(Document).delete()
        # db.query(Case).delete()
        # db.query(DigestSchedule).delete()
        # db.query(UserOrgRole).delete()
        # db.query(User).delete()
        # db.query(Org).delete()
        # db.commit()
        
        # Create Orgs
        org_a = db.query(Org).filter(Org.name == "OrgA").first()
        if not org_a:
            org_a = Org(name="OrgA")
            db.add(org_a)
            db.flush()
            print(f"Created OrgA: {org_a.id}")
        
        org_b = db.query(Org).filter(Org.name == "OrgB").first()
        if not org_b:
            org_b = Org(name="OrgB")
            db.add(org_b)
            db.flush()
            print(f"Created OrgB: {org_b.id}")
        
        # Create Users for OrgA
        users_orga = {}
        for role in ["Admin", "Reviewer", "Approver", "Viewer"]:
            email = f"{role.lower()}@orga.com"
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, full_name=f"{role} User")
                db.add(user)
                db.flush()
            user.full_name = f"{role} User"
            user.password_hash = get_password_hash(LOCAL_DEMO_PASSWORD)
            user.must_change_password = False
            user.failed_login_attempts = 0
            user.locked_until = None
            user.is_active = True
            
            # Create role mapping
            role_map = db.query(UserOrgRole).filter(
                UserOrgRole.user_id == user.id,
                UserOrgRole.org_id == org_a.id,
            ).first()
            if not role_map:
                role_map = UserOrgRole(user_id=user.id, org_id=org_a.id, role=role)
                db.add(role_map)
            users_orga[role] = user
        
        # Create Users for OrgB
        users_orgb = {}
        for role in ["Admin", "Reviewer"]:
            email = f"{role.lower()}@orgb.com"
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, full_name=f"{role} User")
                db.add(user)
                db.flush()
            user.full_name = f"{role} User"
            user.password_hash = get_password_hash(LOCAL_DEMO_PASSWORD)
            user.must_change_password = False
            user.failed_login_attempts = 0
            user.locked_until = None
            user.is_active = True
            
            role_map = db.query(UserOrgRole).filter(
                UserOrgRole.user_id == user.id,
                UserOrgRole.org_id == org_b.id,
            ).first()
            if not role_map:
                role_map = UserOrgRole(user_id=user.id, org_id=org_b.id, role=role)
                db.add(role_map)
            users_orgb[role] = user
        
        db.commit()
        
        # Create Cases for OrgA
        case_titles = [
            "Property Deal #001 - Society Plot",
            "Property Deal #002 - Urban House",
            "Property Deal #003 - Commercial Property",
            "Property Deal #004 - Residential Apartment",
            "Property Deal #005 - Land Parcel",
        ]
        
        cases_orga = []
        for i, title in enumerate(case_titles):
            case = db.query(Case).filter(
                Case.org_id == org_a.id,
                Case.title == title,
            ).first()
            if not case:
                statuses = ["New", "Processing", "Review", "Ready for Approval", "Approved"]
                case = Case(
                    org_id=org_a.id,
                    title=title,
                    status=statuses[i % len(statuses)],
                )
                db.add(case)
                db.flush()
            cases_orga.append(case)
        
        # Create Cases for OrgB
        cases_orgb = []
        for i in range(3):
            title = f"OrgB Case #{i+1}"
            case = db.query(Case).filter(
                Case.org_id == org_b.id,
                Case.title == title,
            ).first()
            if not case:
                case = Case(org_id=org_b.id, title=title, status="New")
                db.add(case)
                db.flush()
            cases_orgb.append(case)
        
        db.commit()
        
        # GUARANTEE: Create "PILOT DEMO CASE" for smoke tests
        demo_case_title = "PILOT DEMO CASE"
        demo_case = db.query(Case).filter(
            Case.org_id == org_a.id,
            Case.title == demo_case_title,
        ).first()
        if not demo_case:
            demo_case = Case(
                org_id=org_a.id,
                title=demo_case_title,
                status="New",
            )
            db.add(demo_case)
            db.flush()
            print(f"Created PILOT DEMO CASE: {demo_case.id}")
            # Add to cases_orga list for counting
            cases_orga.append(demo_case)
        else:
            print(f"Found existing PILOT DEMO CASE: {demo_case.id}")
            # Ensure it's in the list
            if demo_case not in cases_orga:
                cases_orga.append(demo_case)
            # IDEMPOTENT: Verify document exists even if case exists
            demo_doc_check = db.query(Document).filter(
                Document.org_id == org_a.id,
                Document.case_id == demo_case.id,
                Document.original_filename == "PILOT_DEMO_DOCUMENT.pdf",
            ).first()
            if not demo_doc_check:
                print(f"  WARNING: PILOT_DEMO_CASE exists but PILOT_DEMO_DOCUMENT.pdf is missing. Will create it below.")
        
        # P9: Create LDA case with keywords triggering LDA_001/LDA_002
        lda_case_title = "PILOT LDA REVISED PLAN CASE"
        lda_case = db.query(Case).filter(
            Case.org_id == org_a.id,
            Case.title == lda_case_title,
        ).first()
        if not lda_case:
            lda_case = Case(
                org_id=org_a.id,
                title=lda_case_title,
                status="Processing",
            )
            db.add(lda_case)
            db.flush()
            print(f"Created {lda_case_title}: {lda_case.id}")
            cases_orga.append(lda_case)
        else:
            print(f"Found existing {lda_case_title}: {lda_case.id}")
            if lda_case not in cases_orga:
                cases_orga.append(lda_case)
        
        # P9: Create REVENUE case with khasra mismatch triggering LRA_001/LRA_002
        revenue_case_title = "PILOT REVENUE KHASRA MISMATCH CASE"
        revenue_case = db.query(Case).filter(
            Case.org_id == org_a.id,
            Case.title == revenue_case_title,
        ).first()
        if not revenue_case:
            revenue_case = Case(
                org_id=org_a.id,
                title=revenue_case_title,
                status="Processing",
            )
            db.add(revenue_case)
            db.flush()
            print(f"Created {revenue_case_title}: {revenue_case.id}")
            cases_orga.append(revenue_case)
        else:
            print(f"Found existing {revenue_case_title}: {revenue_case.id}")
            if revenue_case not in cases_orga:
                cases_orga.append(revenue_case)
        
        # P9: Ensure DHA/SOCIETY case exists (use first case or create one)
        dha_case_title = "PILOT DHA SOCIETY CASE"
        dha_case = db.query(Case).filter(
            Case.org_id == org_a.id,
            Case.title == dha_case_title,
        ).first()
        if not dha_case:
            dha_case = Case(
                org_id=org_a.id,
                title=dha_case_title,
                status="Processing",
            )
            db.add(dha_case)
            db.flush()
            print(f"Created {dha_case_title}: {dha_case.id}")
            cases_orga.append(dha_case)
        else:
            print(f"Found existing {dha_case_title}: {dha_case.id}")
            if dha_case not in cases_orga:
                cases_orga.append(dha_case)
        
        # GUARANTEE: Create "PILOT_DEMO_DOCUMENT.pdf" for smoke tests
        demo_doc_filename = "PILOT_DEMO_DOCUMENT.pdf"
        demo_doc = db.query(Document).filter(
            Document.org_id == org_a.id,
            Document.case_id == demo_case.id,
            Document.original_filename == demo_doc_filename,
        ).first()
        
        if not demo_doc:
            # Create synthetic PDF with 3 pages and rule-triggering content
            page_contents = [
                "PILOT DEMO DOCUMENT - Page 1\n\nProperty Details:\n- Location: Block A, Phase 2, Society Plot\n- Area: 500 sq yards\n- Owner: John Doe\n- CNIC: 12345-1234567-1\n\nThis property may have encumbrance or mortgage considerations.\nPlease verify all liens and charges before proceeding.",
                "PILOT DEMO DOCUMENT - Page 2\n\nAdditional Information:\n- Property Type: Residential Plot\n- Registry Date: 2020-01-15\n- Sale Deed Number: SD-2020-001\n\nNote: There may be pending litigation or disputes.\nAll parties must be verified.",
                "PILOT DEMO DOCUMENT - Page 3\n\nTerms and Conditions:\n- Transfer of ownership subject to clearance\n- All encumbrances must be disclosed\n- Mortgage status: To be verified\n\nEnd of document."
            ]
            
            # Create multi-page PDF
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            for page_idx, page_content in enumerate(page_contents):
                if page_idx > 0:
                    c.showPage()
                
                # Title
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 50, f"PILOT DEMO DOCUMENT - Page {page_idx + 1}")
                
                # Content
                c.setFont("Helvetica", 12)
                y = height - 100
                for line in page_content.split('\n'):
                    if y < 50:
                        break
                    c.drawString(50, y, line[:80])
                    y -= 20
            
            c.save()
            buffer.seek(0)
            pdf_content = buffer.read()
            
            # Upload to MinIO
            doc_id = uuid.uuid4()
            minio_key = f"org/{org_a.id}/cases/{demo_case.id}/docs/{doc_id}/original.pdf"
            put_object_bytes(minio_key, pdf_content, "application/pdf")
            
            # Create document
            demo_doc = Document(
                id=doc_id,
                org_id=org_a.id,
                case_id=demo_case.id,
                uploader_user_id=users_orga["Admin"].id,
                original_filename=demo_doc_filename,
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key,
                page_count=3,
                status="Split",
                doc_type="sale_deed",
                doc_type_source="manual",
            )
            db.add(demo_doc)
            db.flush()
            
            # Create pages (3 pages)
            for page_num in range(1, 4):
                # Create individual page PDF
                page_buffer = io.BytesIO()
                page_canvas = canvas.Canvas(page_buffer, pagesize=letter)
                page_canvas.setFont("Helvetica", 12)
                page_canvas.drawString(50, height - 50, f"Page {page_num} - {page_contents[page_num - 1][:50]}")
                page_canvas.save()
                page_buffer.seek(0)
                page_pdf = page_buffer.read()
                
                page_key = f"org/{org_a.id}/cases/{demo_case.id}/docs/{doc_id}/pages/{page_num}.pdf"
                put_object_bytes(page_key, page_pdf, "application/pdf")
                
                # Set OCR text for demo (so extraction candidates can be created)
                # Use the page content as OCR text for realistic demo
                ocr_text = page_contents[page_num - 1]
                page = DocumentPage(
                    org_id=org_a.id,
                    document_id=demo_doc.id,
                    page_number=page_num,
                    minio_key_page_pdf=page_key,
                    ocr_status="Done",  # Set to Done so extraction can work immediately
                    ocr_text=ocr_text,  # Set OCR text for demo extraction
                    ocr_confidence=85.0,  # Reasonable confidence for demo
                )
                db.add(page)
            
            db.commit()
            print(f"Created PILOT_DEMO_DOCUMENT.pdf: {demo_doc.id} (3 pages)")
        else:
            print(f"Found existing PILOT_DEMO_DOCUMENT.pdf: {demo_doc.id}")
            # IDEMPOTENT: Ensure pages exist (always verify, even if doc exists)
            existing_pages = db.query(DocumentPage).filter(
                DocumentPage.org_id == org_a.id,
                DocumentPage.document_id == demo_doc.id,
            ).count()
            if existing_pages == 0:
                print(f"  WARNING: PILOT_DEMO_DOCUMENT.pdf exists but has no pages. Recreating pages...")
                # Recreate pages if missing
                page_contents = [
                    "PILOT DEMO DOCUMENT - Page 1\n\nProperty Details:\n- Location: Block A, Phase 2, Society Plot\n- Area: 500 sq yards\n- Owner: John Doe\n- CNIC: 12345-1234567-1\n\nThis property may have encumbrance or mortgage considerations.\nPlease verify all liens and charges before proceeding.",
                    "PILOT DEMO DOCUMENT - Page 2\n\nAdditional Information:\n- Property Type: Residential Plot\n- Registry Date: 2020-01-15\n- Sale Deed Number: SD-2020-001\n\nNote: There may be pending litigation or disputes.\nAll parties must be verified.",
                    "PILOT DEMO DOCUMENT - Page 3\n\nTerms and Conditions:\n- Transfer of ownership subject to clearance\n- All encumbrances must be disclosed\n- Mortgage status: To be verified\n\nEnd of document."
                ]
                for page_num in range(1, 4):
                    page_buffer = io.BytesIO()
                    page_canvas = canvas.Canvas(page_buffer, pagesize=letter)
                    page_canvas.setFont("Helvetica", 12)
                    page_canvas.drawString(50, height - 50, f"Page {page_num} - {page_contents[page_num - 1][:50]}")
                    page_canvas.save()
                    page_buffer.seek(0)
                    page_pdf = page_buffer.read()
                    
                    page_key = f"org/{org_a.id}/cases/{demo_case.id}/docs/{demo_doc.id}/pages/{page_num}.pdf"
                    put_object_bytes(page_key, page_pdf, "application/pdf")
                    
                    # Set OCR text for demo
                    ocr_text = page_contents[page_num - 1]
                    page = DocumentPage(
                        org_id=org_a.id,
                        document_id=demo_doc.id,
                        page_number=page_num,
                        minio_key_page_pdf=page_key,
                        ocr_status="Done",  # Set to Done so extraction can work
                        ocr_text=ocr_text,  # Set OCR text for demo extraction
                        ocr_confidence=85.0,  # Reasonable confidence for demo
                    )
                    db.add(page)
                db.commit()
                print(f"  [OK] Recreated 3 pages for PILOT_DEMO_DOCUMENT.pdf")
            elif existing_pages != 3:
                print(f"  WARNING: PILOT_DEMO_DOCUMENT.pdf has {existing_pages} pages, expected 3. Tests may fail.")
        
        # P9: Create LDA document with keywords
        lda_doc_filename = "LDA_REVISED_PLAN_DOCUMENT.pdf"
        lda_doc = db.query(Document).filter(
            Document.org_id == org_a.id,
            Document.case_id == lda_case.id,
            Document.original_filename == lda_doc_filename,
        ).first()
        if not lda_doc:
            lda_content = "LDA Placement Letter\n\nRevised layout plan under process.\nApproval awaited from LDA.\nThis property requires LDA approval.\nPlacement letter reference: LDA/PL/2024/001"
            pdf_content = create_synthetic_pdf("LDA Revised Plan Document", lda_content)
            doc_id = uuid.uuid4()
            minio_key = f"org/{org_a.id}/cases/{lda_case.id}/docs/{doc_id}/original.pdf"
            put_object_bytes(minio_key, pdf_content, "application/pdf")
            lda_doc = Document(
                id=doc_id,
                org_id=org_a.id,
                case_id=lda_case.id,
                uploader_user_id=users_orga["Admin"].id,
                original_filename=lda_doc_filename,
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key,
                page_count=1,
                status="Split",
                doc_type="placement_letter",
                doc_type_source="manual",
            )
            db.add(lda_doc)
            db.flush()
            # Create page with OCR text
            page_key = f"org/{org_a.id}/cases/{lda_case.id}/docs/{doc_id}/pages/1.pdf"
            put_object_bytes(page_key, pdf_content, "application/pdf")
            page = DocumentPage(
                org_id=org_a.id,
                document_id=lda_doc.id,
                page_number=1,
                minio_key_page_pdf=page_key,
                ocr_status="Done",
                ocr_text=lda_content,
                ocr_confidence=90.0,
            )
            db.add(page)
            db.commit()
            print(f"Created {lda_doc_filename}: {lda_doc.id}")
        
        # P9: Create REVENUE documents with khasra mismatch
        revenue_doc1_filename = "FARD_123_4.pdf"
        revenue_doc1 = db.query(Document).filter(
            Document.org_id == org_a.id,
            Document.case_id == revenue_case.id,
            Document.original_filename == revenue_doc1_filename,
        ).first()
        if not revenue_doc1:
            revenue_content1 = "Fard Malkiat\n\nKhasra No. 123/4\nMouza: Sample Village\nOwner: Test Owner"
            pdf_content = create_synthetic_pdf("Fard Document", revenue_content1)
            doc_id = uuid.uuid4()
            minio_key = f"org/{org_a.id}/cases/{revenue_case.id}/docs/{doc_id}/original.pdf"
            put_object_bytes(minio_key, pdf_content, "application/pdf")
            revenue_doc1 = Document(
                id=doc_id,
                org_id=org_a.id,
                case_id=revenue_case.id,
                uploader_user_id=users_orga["Admin"].id,
                original_filename=revenue_doc1_filename,
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key,
                page_count=1,
                status="Split",
                doc_type="fard",
                doc_type_source="manual",
            )
            db.add(revenue_doc1)
            db.flush()
            page_key = f"org/{org_a.id}/cases/{revenue_case.id}/docs/{doc_id}/pages/1.pdf"
            put_object_bytes(page_key, pdf_content, "application/pdf")
            page = DocumentPage(
                org_id=org_a.id,
                document_id=revenue_doc1.id,
                page_number=1,
                minio_key_page_pdf=page_key,
                ocr_status="Done",
                ocr_text=revenue_content1,
                ocr_confidence=90.0,
            )
            db.add(page)
            db.commit()
            print(f"Created {revenue_doc1_filename}: {revenue_doc1.id}")
        
        # Second revenue doc with different khasra
        revenue_doc2_filename = "JAMABANDI_999_1.pdf"
        revenue_doc2 = db.query(Document).filter(
            Document.org_id == org_a.id,
            Document.case_id == revenue_case.id,
            Document.original_filename == revenue_doc2_filename,
        ).first()
        if not revenue_doc2:
            revenue_content2 = "Jamabandi\n\nKhasra No. 999/1\nMouza: Sample Village\nOwner: Test Owner"
            pdf_content = create_synthetic_pdf("Jamabandi Document", revenue_content2)
            doc_id = uuid.uuid4()
            minio_key = f"org/{org_a.id}/cases/{revenue_case.id}/docs/{doc_id}/original.pdf"
            put_object_bytes(minio_key, pdf_content, "application/pdf")
            revenue_doc2 = Document(
                id=doc_id,
                org_id=org_a.id,
                case_id=revenue_case.id,
                uploader_user_id=users_orga["Admin"].id,
                original_filename=revenue_doc2_filename,
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key,
                page_count=1,
                status="Split",
                doc_type="jamabandi",
                doc_type_source="manual",
            )
            db.add(revenue_doc2)
            db.flush()
            page_key = f"org/{org_a.id}/cases/{revenue_case.id}/docs/{doc_id}/pages/1.pdf"
            put_object_bytes(page_key, pdf_content, "application/pdf")
            page = DocumentPage(
                org_id=org_a.id,
                document_id=revenue_doc2.id,
                page_number=1,
                minio_key_page_pdf=page_key,
                ocr_status="Done",
                ocr_text=revenue_content2,
                ocr_confidence=90.0,
            )
            db.add(page)
            db.commit()
            print(f"Created {revenue_doc2_filename}: {revenue_doc2.id}")
        
        # P9: Create DHA document (missing NDC)
        dha_doc_filename = "DHA_TRANSFER_DOCUMENT.pdf"
        dha_doc = db.query(Document).filter(
            Document.org_id == org_a.id,
            Document.case_id == dha_case.id,
            Document.original_filename == dha_doc_filename,
        ).first()
        if not dha_doc:
            dha_content = "DHA Transfer Document\n\nDefence Housing Authority\nPhase 5, Block A\nProperty transfer document\nNote: NDC not included"
            pdf_content = create_synthetic_pdf("DHA Transfer Document", dha_content)
            doc_id = uuid.uuid4()
            minio_key = f"org/{org_a.id}/cases/{dha_case.id}/docs/{doc_id}/original.pdf"
            put_object_bytes(minio_key, pdf_content, "application/pdf")
            dha_doc = Document(
                id=doc_id,
                org_id=org_a.id,
                case_id=dha_case.id,
                uploader_user_id=users_orga["Admin"].id,
                original_filename=dha_doc_filename,
                content_type="application/pdf",
                size_bytes=len(pdf_content),
                minio_key_original=minio_key,
                page_count=1,
                status="Split",
                doc_type="dha_transfer",
                doc_type_source="manual",
            )
            db.add(dha_doc)
            db.flush()
            page_key = f"org/{org_a.id}/cases/{dha_case.id}/docs/{doc_id}/pages/1.pdf"
            put_object_bytes(page_key, pdf_content, "application/pdf")
            page = DocumentPage(
                org_id=org_a.id,
                document_id=dha_doc.id,
                page_number=1,
                minio_key_page_pdf=page_key,
                ocr_status="Done",
                ocr_text=dha_content,
                ocr_confidence=90.0,
            )
            db.add(page)
            db.commit()
            print(f"Created {dha_doc_filename}: {dha_doc.id}")
        
        # Create additional documents for other cases (optional)
        doc_types = ["sale_deed", "society_allotment", "registry_rod", "noc", "tax_receipt"]
        for case in cases_orga[:3]:  # First 3 cases
            for i, doc_type in enumerate(doc_types[:3]):  # 3 docs per case
                # Skip if this is the demo case (already created)
                if case.id == demo_case.id:
                    continue
                    
                # Check if doc exists
                existing = db.query(Document).filter(
                    Document.org_id == org_a.id,
                    Document.case_id == case.id,
                    Document.original_filename.like(f"%{doc_type}%"),
                ).first()
                if existing:
                    continue
                
                # Create synthetic PDF
                content = f"This is a sample {doc_type} document.\n\nProperty details:\n- Location: Sample Location\n- Area: 500 sq yards\n- Owner: Sample Owner\n\nThis document is for demonstration purposes."
                
                pdf_content = create_synthetic_pdf(
                    f"{doc_type.replace('_', ' ').title()}",
                    content
                )
                
                # Upload to MinIO
                doc_id = uuid.uuid4()
                minio_key = f"org/{org_a.id}/cases/{case.id}/docs/{doc_id}/original.pdf"
                put_object_bytes(minio_key, pdf_content, "application/pdf")
                
                # Create document
                doc = Document(
                    id=doc_id,
                    org_id=org_a.id,
                    case_id=case.id,
                    uploader_user_id=users_orga["Reviewer"].id,
                    original_filename=f"{doc_type}_{case.id}.pdf",
                    content_type="application/pdf",
                    size_bytes=len(pdf_content),
                    minio_key_original=minio_key,
                    page_count=2,
                    status="Split",
                    doc_type=doc_type,
                    doc_type_source="manual",
                )
                db.add(doc)
                db.flush()
                
                # Create pages
                for page_num in range(1, 3):
                    page_pdf = create_synthetic_pdf(f"Page {page_num}", f"Page {page_num} content")
                    page_key = f"org/{org_a.id}/cases/{case.id}/docs/{doc_id}/pages/{page_num}.pdf"
                    put_object_bytes(page_key, page_pdf, "application/pdf")
                    
                    page = DocumentPage(
                        org_id=org_a.id,
                        document_id=doc.id,
                        page_number=page_num,
                        minio_key_page_pdf=page_key,
                        ocr_status="Done",
                        ocr_text=f"Sample OCR text for page {page_num}",
                        ocr_confidence=85.5,
                    )
                    db.add(page)
        
        db.commit()
        print("Created documents and pages")
        
        # Create one approval request for OrgA
        if cases_orga:
            approval = db.query(ApprovalRequest).filter(
                ApprovalRequest.org_id == org_a.id,
            ).first()
            if not approval:
                approval = ApprovalRequest(
                    org_id=org_a.id,
                    case_id=cases_orga[0].id,
                    requested_by_user_id=users_orga["Reviewer"].id,
                    requested_by_role="Reviewer",
                    request_type="case_decision",
                    status="Approved",
                    payload_json={"decision": "PASS", "rationale": "All checks passed"},
                    decided_by_user_id=users_orga["Approver"].id,
                    decided_at=datetime.utcnow(),
                    decision_reason="Approved for pilot demo",
                )
                db.add(approval)
                db.commit()
                print("Created approval request")
        
        # Create one digest schedule for OrgA
        schedule = db.query(DigestSchedule).filter(
            DigestSchedule.org_id == org_a.id,
        ).first()
        if not schedule:
            schedule = DigestSchedule(
                org_id=org_a.id,
                name="Daily Digest",
                created_by_user_id=users_orga["Admin"].id,
                cadence="daily",
                hour_local=9,
                is_enabled=True,
            )
            db.add(schedule)
            db.commit()
            print("Created digest schedule")
        
        # Verify demo case and document exist (they should from above)
        demo_case = db.query(Case).filter(
            Case.org_id == org_a.id,
            Case.title == "PILOT DEMO CASE",
        ).first()
        
        demo_doc = None
        if demo_case:
            demo_doc = db.query(Document).filter(
                Document.org_id == org_a.id,
                Document.case_id == demo_case.id,
                Document.original_filename == "PILOT_DEMO_DOCUMENT.pdf",
            ).first()
        
        if not demo_case or not demo_doc:
            raise Exception("CRITICAL: Failed to create or find PILOT DEMO CASE and PILOT_DEMO_DOCUMENT.pdf")
        
        # Get page count
        page_count = db.query(DocumentPage).filter(
            DocumentPage.org_id == org_a.id,
            DocumentPage.document_id == demo_doc.id,
        ).count()
        
        # Ensure at least one OCR extraction candidate exists for demo
        # This makes the "Extract from OCR" UI immediately testable
        existing_candidate = db.query(OCRExtractionCandidate).filter(
            OCRExtractionCandidate.org_id == org_a.id,
            OCRExtractionCandidate.case_id == demo_case.id,
            OCRExtractionCandidate.status == "Pending",
        ).first()
        
        if not existing_candidate:
            # Create a demo extraction candidate for "party.name.raw" field
            # The OCR text contains "Owner: John Doe" which should extract to this field
            demo_page = db.query(DocumentPage).filter(
                DocumentPage.org_id == org_a.id,
                DocumentPage.document_id == demo_doc.id,
                DocumentPage.page_number == 1,
            ).first()
            
            if demo_page and demo_page.ocr_text:
                # Extract "John Doe" from OCR text as a demo candidate
                candidate = OCRExtractionCandidate(
                    org_id=org_a.id,
                    case_id=demo_case.id,
                    document_id=demo_doc.id,
                    page_number=1,
                    field_key="party.name.raw",
                    proposed_value="John Doe",
                    confidence=0.85,
                    snippet="Owner: John Doe",
                    status="Pending",
                    quality_level_at_create="Good",
                    is_low_quality=False,
                )
                db.add(candidate)
                db.commit()
                print("Created demo OCR extraction candidate (party.name.raw = 'John Doe')")
        
        print("[OK] Demo data seeded successfully!")
        print(f"   OrgA: {len(cases_orga)} cases, {len(users_orga)} users")
        print(f"   OrgB: {len(cases_orgb)} cases, {len(users_orgb)} users")
        print("\nLogin credentials:")
        print(f"   OrgA Admin: admin@orga.com / {LOCAL_DEMO_PASSWORD}")
        print(f"   OrgA Reviewer: reviewer@orga.com / {LOCAL_DEMO_PASSWORD}")
        print(f"   OrgB Admin: admin@orgb.com / {LOCAL_DEMO_PASSWORD}")
        print("\nDemo IDs (for smoke tests):")
        print(f"DEMO_CASE_ID={demo_case.id}")
        print(f"DEMO_DOC_ID={demo_doc.id}")
        print(f"DEMO_DOC_PAGE_COUNT={page_count}")
        print(f"DEMO_ORG=OrgA")
        print(f"DEMO_USER_EMAIL=admin@orga.com")
        print(f"DEMO_ROLE=Admin")
        
        # P9: Print regime case IDs
        if lda_case:
            print(f"\nDEMO_LDA_CASE_ID={lda_case.id}")
        if revenue_case:
            print(f"DEMO_REVENUE_CASE_ID={revenue_case.id}")
        if dha_case:
            print(f"DEMO_DHA_CASE_ID={dha_case.id}")
        
    except Exception as e:
        db.rollback()
        print(f"[FAIL] Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
