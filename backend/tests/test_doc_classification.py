import uuid
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.models.document import Document, get_document_type, ClassificationStatus, DocumentClassificationLog, DocumentType


def test_corrected_overrides_predicted():
    d = Document(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        uploader_user_id=uuid.uuid4(),
        original_filename="sale_deed.pdf",
        content_type="application/pdf",
        size_bytes=100,
        minio_key_original="k",
        predicted_doc_type=DocumentType.SALE_DEED.value,
        corrected_doc_type=DocumentType.REGISTRY_DEED.value,
        classification_status=ClassificationStatus.CORRECTED.value,
    )
    assert get_document_type(d) == DocumentType.REGISTRY_DEED.value


def test_verified_status_persists_flag():
    d = Document(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        uploader_user_id=uuid.uuid4(),
        original_filename="doc.pdf",
        content_type="application/pdf",
        size_bytes=10,
        minio_key_original="k",
        predicted_doc_type=DocumentType.UNKNOWN.value,
        classification_status=ClassificationStatus.VERIFIED.value,
    )
    assert d.classification_status == ClassificationStatus.VERIFIED.value


def test_confidence_field_available():
    d = Document(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        uploader_user_id=uuid.uuid4(),
        original_filename="doc.pdf",
        content_type="application/pdf",
        size_bytes=10,
        minio_key_original="k",
        classification_confidence=0.82,
    )
    assert float(d.classification_confidence) == 0.82


def test_classification_log_model_init():
    log = DocumentClassificationLog(
        document_id=uuid.uuid4(),
        predicted_doc_type=DocumentType.FARD.value,
        corrected_doc_type=None,
        confidence=0.6,
    )
    assert str(log.predicted_doc_type) == DocumentType.FARD.value
