from __future__ import annotations

import copy
import uuid
from pathlib import Path
from typing import Any

import yaml

from app.services.extractors.document_facts import DocumentFact
from app.services.rule_engine import CaseContext

REPO_ROOT = Path(__file__).resolve().parents[3]
RULEPACK_PATH = REPO_ROOT / "docs" / "05_rulepack_v1.yaml"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
METRICS_PATH = REPO_ROOT / "docs" / "rule_engine" / "rule_metrics.md"

BASE_DOC_TYPES = [
    "CNIC Copy",
    "Photograph",
    "Salary Slip",
    "Utility Bill",
    "Co-applicant CNIC",
    "Possession Letter",
    "Site Report",
    "Society NOC",
    "CLU",
    "Membership Letter",
    "Building Plan",
    "Board Resolution",
    "dha_ndc",
    "site_plan",
    "approved_map",
    "completion_certificate",
    "registry_deed",
    "estamp_certificate",
    "fard",
    "mutation_entry",
    "society_transfer",
    "society_mortgage_permission",
    "society_ndc",
    "lda_layout_plan",
    "commercialization_letter",
    "ruda_noc",
    "cantonment_noc",
    "municipal_dues_clearance",
    "pt1",
]

BASE_DOSSIER = {
    "property.constructed": ["false"],
    "property.use_type": ["residential"],
    "property.possession_status": ["known"],
    "bank_requires_mutation": ["false"],
    "policy_requires_pt1": ["false"],
    "party.cnic": ["35202-1234567-1"],
    "registry.registry_number": ["12345"],
    "registry.registry_date": ["2024-01-15"],
    "transaction.consideration_amount": ["10000000"],
    "stamp.stamp_basis_amount": ["10000000"],
    "property.khasra_numbers": ["12/34"],
    "property.khewat_number": ["56"],
}

BASE_VERIFICATIONS = {
    "e_stamp": "Verified",
    "registry_rod": "Verified",
}

BASE_CASES: dict[str, dict[str, Any]] = {
    "clean_urban": {
        "regime": "SOCIETY",
        "dossier": BASE_DOSSIER,
        "doc_types": BASE_DOC_TYPES,
        "pages": [],
        "verifications": BASE_VERIFICATIONS,
        "ocr_complete": True,
    },
    "clean_constructed": {
        "regime": "SOCIETY",
        "dossier": {
            **BASE_DOSSIER,
            "property.constructed": ["true"],
        },
        "doc_types": BASE_DOC_TYPES,
        "pages": [],
        "verifications": BASE_VERIFICATIONS,
        "ocr_complete": True,
    },
    "clean_revenue": {
        "regime": "REVENUE",
        "dossier": BASE_DOSSIER,
        "doc_types": BASE_DOC_TYPES,
        "pages": [],
        "verifications": BASE_VERIFICATIONS,
        "ocr_complete": True,
    },
    "clean_ruda": {
        "regime": "RUDA",
        "dossier": BASE_DOSSIER,
        "doc_types": BASE_DOC_TYPES,
        "pages": [],
        "verifications": BASE_VERIFICATIONS,
        "ocr_complete": True,
    },
    "clean_cantonment": {
        "regime": "CANTONMENT",
        "dossier": BASE_DOSSIER,
        "doc_types": BASE_DOC_TYPES,
        "pages": [],
        "verifications": BASE_VERIFICATIONS,
        "ocr_complete": True,
    },
}


def _copy_dict_lists(data: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: list(values) for key, values in data.items()}


def load_fixture(path: Path) -> dict[str, Any]:
    fixture = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base_name = fixture.get("base")
    if not base_name:
        return fixture

    if base_name not in BASE_CASES:
        raise ValueError(f"Unknown fixture base '{base_name}' in {path.name}")

    merged = copy.deepcopy(BASE_CASES[base_name])
    if "regime" in fixture:
        merged["regime"] = fixture["regime"]

    dossier = _copy_dict_lists(merged.get("dossier", {}))
    if fixture.get("dossier"):
        dossier = {key: list(values) for key, values in fixture["dossier"].items()}
    for key, values in (fixture.get("dossier_updates") or {}).items():
        dossier[key] = list(values)
    merged["dossier"] = dossier

    if "doc_types" in fixture:
        doc_types = list(fixture["doc_types"])
    else:
        doc_types = list(merged.get("doc_types", []))
    removals = set(fixture.get("doc_types_remove") or [])
    doc_types = [doc_type for doc_type in doc_types if doc_type not in removals]
    doc_types.extend(fixture.get("doc_types_add") or [])
    merged["doc_types"] = doc_types

    if "pages" in fixture:
        pages = list(fixture["pages"])
    else:
        pages = list(merged.get("pages", []))
    pages.extend(fixture.get("pages_add") or [])
    merged["pages"] = pages

    verifications = dict(merged.get("verifications", {}))
    verifications.update(fixture.get("verifications") or {})
    merged["verifications"] = verifications
    merged["ocr_complete"] = fixture.get("ocr_complete", merged.get("ocr_complete", True))

    for key in (
        "name",
        "expect_triggered",
        "expect_not_triggered",
        "expected_decision",
        "expect_error",
        "expect_evidence_for",
        "borrower_type",
        "transaction_type",
        "facts",
        "documents",
    ):
        if key in fixture:
            merged[key] = fixture[key]

    return merged


def load_all_fixtures() -> list[dict[str, Any]]:
    return [load_fixture(path) for path in sorted(FIXTURES_DIR.glob("*.yaml"))]


class _FixtureDocument:
    def __init__(self, doc_id: uuid.UUID, filename: str, doc_type: str | None):
        self.id = doc_id
        self.original_filename = filename
        self.doc_type = doc_type


def make_context(
    *,
    name: str,
    regime: str | None,
    dossier: dict[str, list[str]] | None = None,
    doc_types: list[str] | None = None,
    pages: list[dict[str, Any]] | None = None,
    verifications: dict[str, str] | None = None,
    ocr_complete: bool = True,
    borrower_type: str | None = None,
    transaction_type: str | None = None,
    facts: list[dict[str, Any]] | None = None,
    documents: list[dict[str, Any]] | None = None,
) -> CaseContext:
    org_id = uuid.uuid5(uuid.NAMESPACE_URL, f"org:{name}")
    case_id = uuid.uuid5(uuid.NAMESPACE_URL, f"case:{name}")
    dossier_data = _copy_dict_lists(dossier or {})
    if regime is not None:
        dossier_data["property.regime"] = [regime]
    if borrower_type:
        dossier_data["case.borrower_type"] = [borrower_type]
    if transaction_type:
        dossier_data["case.transaction_type"] = [transaction_type]

    page_rows = []
    doc_filenames: list[str] = []
    seen_docs: set[str] = set()
    doc_objects: list[_FixtureDocument] = []
    for entry in pages or []:
        doc_name = entry.get("doc", "fixture.pdf")
        if doc_name not in seen_docs:
            seen_docs.add(doc_name)
            doc_filenames.append(doc_name)
        doc_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{name}:{doc_name}")
        page_rows.append((doc_id, int(entry.get("page", 1)), entry.get("text", "")))

    for entry in documents or []:
        filename = entry.get("filename") or entry.get("doc") or "fixture.pdf"
        doc_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{name}:{filename}")
        doc_objects.append(_FixtureDocument(doc_id, filename, entry.get("doc_type")))
        if filename not in seen_docs:
            seen_docs.add(filename)
            doc_filenames.append(filename)

    document_facts = [
        DocumentFact(
            key=str(item.get("key") or ""),
            value=str(item.get("value") or ""),
            page_number=int(item.get("page") or 1),
            snippet=str(item.get("snippet") or item.get("value") or ""),
            doc_type=item.get("doc_type"),
            document_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}:{item.get('doc', 'fact')}:{item.get('page', 1)}")),
        )
        for item in facts or []
        if item.get("key") and item.get("value")
    ]

    return CaseContext(
        org_id=org_id,
        case_id=case_id,
        dossier=dossier_data,
        doc_types=list(doc_types or []),
        doc_filenames=doc_filenames,
        documents=doc_objects,  # type: ignore[arg-type]
        pages=page_rows,
        verifications=dict(verifications or {}),
        ocr_complete=ocr_complete,
        borrower_type=borrower_type,
        transaction_type=transaction_type,
        document_facts=document_facts,
    )


def make_context_from_fixture(fixture: dict[str, Any]) -> CaseContext:
    return make_context(
        name=fixture["name"],
        regime=fixture.get("regime"),
        dossier=fixture.get("dossier", {}),
        doc_types=fixture.get("doc_types", []),
        pages=fixture.get("pages", []),
        verifications=fixture.get("verifications", {}),
        ocr_complete=fixture.get("ocr_complete", True),
        borrower_type=fixture.get("borrower_type"),
        transaction_type=fixture.get("transaction_type"),
        facts=fixture.get("facts") or [],
        documents=fixture.get("documents") or [],
    )
