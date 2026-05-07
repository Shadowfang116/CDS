import io
import uuid
from datetime import datetime, timedelta

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.document import Document, DocumentPage
from app.models.evaluation import EvaluationFinding, EvaluationRun
from app.models.export import Export, EXPORT_STATUS_SUCCEEDED
from app.models.org import Org
from app.models.rules import ConditionPrecedent, Exception_
from app.models.user import User, UserOrgRole
from app.services.dossier_versions import empty_dossier
from app.services.storage import put_object_bytes

DEMO_ORG_NAME = "Demo Law Firm"
DEMO_ADMIN_EMAIL = "demo-admin@example.com"
DEMO_CASE_TITLE = "Al-Noor Commercial Tower — Block C, Gulberg III, Lahore"
LEGACY_DEMO_CASE_TITLE = "DHA Lahore Residential Mortgage"


def _pdf_bytes(title: str, body: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(48, 740, title)
    pdf.setFont("Helvetica", 11)
    y = 710
    for line in body.splitlines():
        pdf.drawString(48, y, line[:96])
        y -= 18
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def seed_demo_data(db: Session) -> dict[str, str]:
    demo_org = db.query(Org).filter(Org.name == DEMO_ORG_NAME).first()
    if not demo_org:
        demo_org = Org(name=DEMO_ORG_NAME)
        db.add(demo_org)
        db.flush()

    admin_user = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
    if not admin_user:
        admin_user = User(
            email=DEMO_ADMIN_EMAIL,
            full_name="Demo Admin",
            password_hash=hash_password("demo-reset-required"),
            must_change_password=True,
        )
        db.add(admin_user)
        db.flush()
    else:
        admin_user.full_name = "Demo Admin"
        admin_user.password_hash = hash_password("demo-reset-required")
        admin_user.must_change_password = True

    role = (
        db.query(UserOrgRole)
        .filter(UserOrgRole.user_id == admin_user.id, UserOrgRole.org_id == demo_org.id)
        .first()
    )
    if not role:
        db.add(UserOrgRole(user_id=admin_user.id, org_id=demo_org.id, role="Admin"))

    case = (
        db.query(Case)
        .filter(Case.org_id == demo_org.id, Case.title.in_([DEMO_CASE_TITLE, LEGACY_DEMO_CASE_TITLE]))
        .first()
    )
    if not case:
        case = Case(org_id=demo_org.id, title=DEMO_CASE_TITLE, status="Review")
        db.add(case)
        db.flush()

    case.title = DEMO_CASE_TITLE
    case.status = "Review"
    case.decision = None
    case.decision_notes = {
        "evaluation_output": {
            "status": "review_required",
            "summary": "Outstanding title chain and authority Exceptions require legal resolution before approval readiness can be confirmed.",
        }
    }

    dossier = empty_dossier()
    dossier["fields"] = {
        "matter.reference": {"value": "ANCT/BDC/2026/017", "source": "manual", "locked": True},
        "party.name.borrower": {"value": "Al-Noor Developers (Private) Limited", "source": "manual", "locked": True},
        "party.name.seller": {"value": "Horizon Realty Holdings", "source": "manual", "locked": True},
        "party.cnic": {"value": "35202-1234567-1", "source": "manual", "locked": True},
        "property.address": {"value": "Plot 27, Block C, Gulberg III, Lahore", "source": "manual", "locked": True},
        "property.scheme_name": {"value": "Gulberg III Commercial Area", "source": "manual", "locked": True},
        "property.block": {"value": "Block C", "source": "manual", "locked": True},
        "property.city": {"value": "Lahore", "source": "manual", "locked": True},
        "transaction.amount_pkr": {"value": "PKR 425,000,000", "source": "manual", "locked": True},
        "facility.finance_type": {"value": "Term finance facility secured by equitable mortgage", "source": "manual", "locked": True},
        "title.title_type": {"value": "Freehold commercial title", "source": "manual", "locked": True},
        "title.registry_reference": {"value": "Sale Deed No. 1234/2023", "source": "manual", "locked": True},
        "revenue.mutation_reference": {"value": "Mutation Entry No. 887", "source": "manual", "locked": True},
        "authority.noc_reference": {"value": "NOC — Lahore Development Authority", "source": "manual", "locked": True},
    }
    dossier["evaluation_output"] = {
        "status": "review_required",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": "Legal review remains in progress because material Exceptions and CPs remain outstanding.",
    }
    dossier["revision_history"] = [
        {
            "version": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "actor_id": str(admin_user.id),
            "summary": "Demo dossier refreshed for Lahore commercial finance presentation.",
        }
    ]
    case.dossier_json = dossier
    db.flush()

    document_specs = [
        {
            "filename": "Sale Deed No. 1234-2023.pdf",
            "aliases": ["Sale Deed No. 1234-2023.pdf", "sale_deed.pdf"],
            "doc_type": "registry_deed",
            "page_text": "Registered Sale Deed No. 1234/2023 pertaining to Plot 27, Block C, Gulberg III, Lahore, executed in favour of Al-Noor Developers (Private) Limited for PKR 425,000,000.",
        },
        {
            "filename": "Mutation Entry No. 887.pdf",
            "aliases": ["Mutation Entry No. 887.pdf", "cnic.pdf"],
            "doc_type": "mutation_entry",
            "page_text": "Mutation Entry No. 887 from the Lahore revenue record reflects transfer in favour of Al-Noor Developers (Private) Limited, subject to updated mortgage notation in favour of the financing bank.",
        },
        {
            "filename": "NOC — Lahore Development Authority.pdf",
            "aliases": ["NOC — Lahore Development Authority.pdf", "society_noc.pdf"],
            "doc_type": "authority_noc",
            "page_text": "No Objection Certificate issued by Lahore Development Authority for the commercial tower situated at Plot 27, Block C, Gulberg III, Lahore, subject to compliance with building and mortgage endorsement conditions.",
        },
    ]

    existing_documents = (
        db.query(Document)
        .filter(Document.case_id == case.id, Document.org_id == demo_org.id)
        .order_by(Document.created_at.asc())
        .all()
    )
    matched_document_ids: set = set()
    documents_by_filename: dict[str, Document] = {}

    for spec in document_specs:
        document = None
        for existing in existing_documents:
            if existing.id in matched_document_ids:
                continue
            if existing.original_filename in spec["aliases"]:
                document = existing
                break
        if document is None:
            for existing in existing_documents:
                if existing.id not in matched_document_ids:
                    document = existing
                    break

        if document is None:
            document = Document(
                org_id=demo_org.id,
                case_id=case.id,
                uploader_user_id=admin_user.id,
                original_filename=spec["filename"],
                content_type="application/pdf",
                size_bytes=0,
                minio_key_original=f"org/{demo_org.id}/cases/{case.id}/docs/{uuid.uuid4()}/original.pdf",
                page_count=1,
                status="Processed",
                doc_type=spec["doc_type"],
            )
            db.add(document)
            db.flush()
        else:
            document.original_filename = spec["filename"]
            document.content_type = "application/pdf"
            document.page_count = 1
            document.status = "Processed"
            document.doc_type = spec["doc_type"]
            if not document.minio_key_original:
                document.minio_key_original = f"org/{demo_org.id}/cases/{case.id}/docs/{uuid.uuid4()}/original.pdf"

        pdf_bytes = _pdf_bytes(spec["filename"], spec["page_text"])
        document.size_bytes = len(pdf_bytes)
        put_object_bytes(document.minio_key_original, pdf_bytes, "application/pdf")

        page = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document.id, DocumentPage.org_id == demo_org.id, DocumentPage.page_number == 1)
            .first()
        )
        if not page:
            page = DocumentPage(
                org_id=demo_org.id,
                document_id=document.id,
                page_number=1,
                minio_key_page_pdf=f"org/{demo_org.id}/cases/{case.id}/docs/{document.id}/pages/1.pdf",
                ocr_status="Done",
                ocr_text=spec["page_text"],
            )
            db.add(page)
        else:
            page.ocr_status = "Done"
            page.ocr_text = spec["page_text"]
            if not page.minio_key_page_pdf:
                page.minio_key_page_pdf = f"org/{demo_org.id}/cases/{case.id}/docs/{document.id}/pages/1.pdf"
        put_object_bytes(page.minio_key_page_pdf, pdf_bytes, "application/pdf")

        matched_document_ids.add(document.id)
        documents_by_filename[spec["filename"]] = document

    db.flush()

    db.query(Exception_).filter(Exception_.case_id == case.id, Exception_.org_id == demo_org.id).delete(synchronize_session=False)
    exception_specs = [
        {
            "rule_id": "DEMO_TITLE_CHAIN",
            "module": "Title",
            "severity": "Critical",
            "title": "Title chain gap between prior conveyance and current ownership",
            "description": "The matter file does not yet contain the immediately preceding conveyance instrument required to complete the title chain into the Borrower under Sale Deed No. 1234/2023.",
            "source_filename": "Sale Deed No. 1234-2023.pdf",
            "cp_text": "Obtain and review the missing prior conveyance instrument together with a chain-of-title confirmation from the Sub-Registrar before approval.",
        },
        {
            "rule_id": "DEMO_MUTATION_GAP",
            "module": "Revenue",
            "severity": "High",
            "title": "Mutation record requires mortgage endorsement update",
            "description": "Mutation Entry No. 887 evidences transfer into the Borrower but does not yet reflect the proposed mortgage notation in favour of the financing bank.",
            "source_filename": "Mutation Entry No. 887.pdf",
            "cp_text": "File the revenue entry required to record or confirm the mortgage notation in favour of the Bank before disbursement.",
        },
        {
            "rule_id": "DEMO_LDA_SCOPE",
            "module": "Authority",
            "severity": "High",
            "title": "Authority NOC requires confirmation of mortgage permissibility",
            "description": "The available LDA NOC is not yet paired with a clear confirmation that the commercial unit may be charged to the Bank without further authority objection.",
            "source_filename": "NOC — Lahore Development Authority.pdf",
            "cp_text": "Procure a fresh authority confirmation or endorsement expressly permitting mortgage creation over the property in favour of the Bank.",
        },
        {
            "rule_id": "DEMO_POSSESSION_FILE",
            "module": "Occupancy",
            "severity": "Medium",
            "title": "Possession and tenancy evidence remains incomplete",
            "description": "The matter record does not yet contain a current possession memo and tenant status confirmation for the commercial tower.",
            "source_filename": "Sale Deed No. 1234-2023.pdf",
            "cp_text": "Provide an updated possession memo and current tenancy statement supported by site verification evidence.",
        },
    ]

    for spec in exception_specs:
        source_document = documents_by_filename.get(spec["source_filename"])
        db.add(
            Exception_(
                org_id=demo_org.id,
                case_id=case.id,
                rule_id=spec["rule_id"],
                severity=spec["severity"],
                module=spec["module"],
                title=spec["title"],
                description=spec["description"],
                evidence_refs=[
                    {
                        "document_id": str(source_document.id) if source_document else None,
                        "page_number": 1,
                        "note": "Seeded demo evidence reference",
                    }
                ],
                cp_text=spec["cp_text"],
                is_manual=True,
                source_document_id=source_document.id if source_document else None,
                source_page=1,
                status="Open",
            )
        )

    db.query(ConditionPrecedent).filter(ConditionPrecedent.case_id == case.id, ConditionPrecedent.org_id == demo_org.id).delete(synchronize_session=False)
    cp_specs = [
        {
            "rule_id": "CP_TITLE_CHAIN",
            "severity": "High",
            "text": "Obtain the missing prior conveyance instrument and Sub-Registrar search confirming an unbroken chain of title into Al-Noor Developers (Private) Limited.",
            "evidence_required": "Certified prior conveyance instrument, Sub-Registrar search, and reviewer confirmation memorandum",
        },
        {
            "rule_id": "CP_MUTATION_ENDORSEMENT",
            "severity": "High",
            "text": "Procure updated revenue documentation showing Mutation Entry No. 887 together with mortgage endorsement or equivalent revenue confirmation in favour of the Bank.",
            "evidence_required": "Updated mutation extract, mortgage notation evidence, and revenue office acknowledgement",
        },
        {
            "rule_id": "CP_LDA_CONFIRMATION",
            "severity": "Medium",
            "text": "Provide a current LDA confirmation or NOC expressly permitting mortgage creation over Plot 27, Block C, Gulberg III, Lahore for the financing transaction.",
            "evidence_required": "Fresh LDA NOC, authority correspondence, and legal review note",
        },
    ]

    for index, spec in enumerate(cp_specs, start=1):
        db.add(
            ConditionPrecedent(
                org_id=demo_org.id,
                case_id=case.id,
                rule_id=spec["rule_id"],
                severity=spec["severity"],
                text=spec["text"],
                evidence_required=spec["evidence_required"],
                due_date=datetime.utcnow() + timedelta(days=5 * index),
                status="Open",
            )
        )

    db.query(AuditLog).filter(AuditLog.case_id == case.id, AuditLog.org_id == demo_org.id).delete(synchronize_session=False)
    audit_entries = [
        {
            "action": "case.created",
            "entity_type": "case",
            "entity_id": str(case.id),
            "after_json": {"title": DEMO_CASE_TITLE, "status": "Review"},
            "created_at": datetime.utcnow() - timedelta(days=3, hours=4),
        },
        {
            "action": "document.uploaded",
            "entity_type": "document",
            "entity_id": str(documents_by_filename["Sale Deed No. 1234-2023.pdf"].id),
            "after_json": {"filename": "Sale Deed No. 1234-2023.pdf", "category": "title evidence"},
            "created_at": datetime.utcnow() - timedelta(days=2, hours=6),
        },
        {
            "action": "evaluation.completed",
            "entity_type": "case",
            "entity_id": str(case.id),
            "after_json": {"status": "review_required", "open_exceptions": 4, "open_cps": 3},
            "created_at": datetime.utcnow() - timedelta(days=1, hours=2),
        },
    ]
    for entry in audit_entries:
        db.add(
            AuditLog(
                org_id=demo_org.id,
                case_id=case.id,
                actor_id=admin_user.id,
                action=entry["action"],
                entity_type=entry["entity_type"],
                entity_id=entry["entity_id"],
                after_json=entry["after_json"],
                created_at=entry["created_at"],
                request_id=f"demo-seed-{uuid.uuid4().hex[:10]}",
            )
        )

    existing_runs = db.query(EvaluationRun).filter(EvaluationRun.case_id == case.id, EvaluationRun.org_id == demo_org.id).all()
    run_ids = [run.id for run in existing_runs]
    if run_ids:
        db.query(EvaluationFinding).filter(EvaluationFinding.evaluation_run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(EvaluationRun).filter(EvaluationRun.id.in_(run_ids)).delete(synchronize_session=False)

    evaluation_run = EvaluationRun(
        org_id=demo_org.id,
        case_id=case.id,
        started_at=datetime.utcnow() - timedelta(days=1, hours=2),
        completed_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=56),
        duration_ms=240000,
        critical_recall=1.0,
        overall_recall=0.86,
        precision=0.8,
        expected_count=7,
        matched_count=6,
        missed_count=1,
        extra_count=1,
        status="completed",
        created_by=admin_user.id,
        error_message=None,
    )
    db.add(evaluation_run)
    db.flush()

    finding_specs = [
        {
            "finding_type": "exception",
            "expected_rule_id": "DEMO_TITLE_CHAIN",
            "actual_rule_id": "DEMO_TITLE_CHAIN",
            "expected_title": "Title chain gap between prior conveyance and current ownership",
            "actual_title": "Title chain gap between prior conveyance and current ownership",
            "expected_text": "Critical title chain exception expected for missing prior conveyance.",
            "actual_text": "Critical title chain exception raised for missing prior conveyance.",
            "expected_severity": "Critical",
            "actual_severity": "Critical",
            "match_status": "matched",
            "similarity_score": 0.99,
            "notes": "Seeded demo finding",
        },
        {
            "finding_type": "cp",
            "expected_rule_id": "CP_LDA_CONFIRMATION",
            "actual_rule_id": "CP_LDA_CONFIRMATION",
            "expected_title": "Authority confirmation CP",
            "actual_title": "Authority confirmation CP",
            "expected_text": "Authority mortgage permissibility CP expected.",
            "actual_text": "Authority mortgage permissibility CP generated.",
            "expected_severity": "Medium",
            "actual_severity": "Medium",
            "match_status": "matched",
            "similarity_score": 0.93,
            "notes": "Seeded demo finding",
        },
        {
            "finding_type": "exception",
            "expected_rule_id": None,
            "actual_rule_id": "DEMO_POSSESSION_FILE",
            "expected_title": None,
            "actual_title": "Possession and tenancy evidence remains incomplete",
            "expected_text": None,
            "actual_text": "Possession and tenancy evidence remains incomplete.",
            "expected_severity": None,
            "actual_severity": "Medium",
            "match_status": "extra",
            "similarity_score": 0.52,
            "notes": "Seeded extra finding to keep the matter in review_required state.",
        },
    ]
    for spec in finding_specs:
        db.add(
            EvaluationFinding(
                evaluation_run_id=evaluation_run.id,
                expectation_id=None,
                finding_type=spec["finding_type"],
                expected_rule_id=spec["expected_rule_id"],
                actual_rule_id=spec["actual_rule_id"],
                expected_title=spec["expected_title"],
                actual_title=spec["actual_title"],
                expected_text=spec["expected_text"],
                actual_text=spec["actual_text"],
                expected_severity=spec["expected_severity"],
                actual_severity=spec["actual_severity"],
                match_status=spec["match_status"],
                similarity_score=spec["similarity_score"],
                notes=spec["notes"],
            )
        )

    export = db.query(Export).filter(Export.case_id == case.id, Export.org_id == demo_org.id).first()
    export_bytes = _pdf_bytes(
        "Bank Pack [DRAFT]",
        "Demo Bank Pack for Al-Noor Commercial Tower — Block C, Gulberg III, Lahore.\nGenerated for product walkthrough and presentation use.",
    )
    if not export:
        export = Export(
            org_id=demo_org.id,
            case_id=case.id,
            export_type="bank_pack_pdf",
            filename="BANK_PACK__AL_NOOR_COMMERCIAL_TOWER.pdf",
            content_type="application/pdf",
            minio_key=f"org/{demo_org.id}/cases/{case.id}/exports/{uuid.uuid4()}/BANK_PACK__AL_NOOR_COMMERCIAL_TOWER.pdf",
            created_by_user_id=admin_user.id,
            status=EXPORT_STATUS_SUCCEEDED,
        )
        db.add(export)
        db.flush()
    else:
        export.filename = "BANK_PACK__AL_NOOR_COMMERCIAL_TOWER.pdf"
        export.content_type = "application/pdf"
        export.status = EXPORT_STATUS_SUCCEEDED
        if not export.minio_key:
            export.minio_key = f"org/{demo_org.id}/cases/{case.id}/exports/{uuid.uuid4()}/BANK_PACK__AL_NOOR_COMMERCIAL_TOWER.pdf"

    put_object_bytes(export.minio_key, export_bytes, "application/pdf")

    db.commit()
    return {
        "org_id": str(demo_org.id),
        "admin_user_id": str(admin_user.id),
        "case_id": str(case.id),
    }
