from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

HIGH_RISK_FIELDS = {
    "owner_name",
    "property_area",
    "khasra_number",
    "price",
    "party.buyer.names",
    "party.seller.names",
    "property.khasra_numbers",
    "property.plot_number",
    "consideration.amount",
}


@dataclass
class PageResult:
    page_num: int
    text: str
    confidence: float | None
    quality_score: float | None
    quality_level: str
    warning_reason: str | None
    engine_used: str


@dataclass
class OcrPipelineResult:
    document_id: str
    pages: list[PageResult] = field(default_factory=list)
    overall_quality: float | None = None
    quality_level: str = "unavailable"
    autofill_eligible: bool = False


def _level_from_score(score: float | None) -> str:
    if score is None:
        return "unavailable"
    if score >= 0.7:
        return "good"
    if score >= 0.45:
        return "fair"
    if score >= 0.3:
        return "poor"
    return "unusable"


def _downgrade_quality(level: str) -> str:
    if level == "good":
        return "fair"
    if level == "fair":
        return "poor"
    if level == "poor":
        return "unusable"
    return level


def _aggregate_quality(pages: list[PageResult]) -> tuple[float | None, str]:
    scores = [page.quality_score for page in pages if page.quality_score is not None]
    if not scores:
        return None, "unavailable"

    overall_quality = sum(scores) / len(scores)
    quality_level = _level_from_score(overall_quality)
    poor_pages = sum(1 for page in pages if page.quality_level in {"poor", "unusable"})

    if poor_pages and quality_level == "good":
        quality_level = "fair"
    if poor_pages > max(1, len(pages) // 2):
        quality_level = _downgrade_quality(quality_level)

    return overall_quality, quality_level


async def run_ocr_pipeline(
    document_id: str,
    page_images: list[str],
    engine: str = "surya",
) -> OcrPipelineResult:
    service_url = getattr(settings, "OCR_SERVICE_URL", "http://localhost:8001").rstrip("/")
    request_payload = {
        "document_id": document_id,
        "pages": page_images,
        "engine": engine,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{service_url}/ocr", json=request_payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("OCR pipeline request failed for document %s: %s", document_id, exc)
        unavailable_pages = [
            PageResult(
                page_num=index,
                text="",
                confidence=0.0,
                quality_score=0.0,
                quality_level="unavailable",
                warning_reason="OCR service unavailable",
                engine_used=engine,
            )
            for index, _ in enumerate(page_images, start=1)
        ]
        return OcrPipelineResult(
            document_id=document_id,
            pages=unavailable_pages,
            overall_quality=0.0,
            quality_level="unavailable",
            autofill_eligible=False,
        )

    payload = response.json()
    pages = [
        PageResult(
            page_num=page_payload["page_num"],
            text=page_payload.get("text", ""),
            confidence=page_payload.get("confidence"),
            quality_score=page_payload.get("quality_score"),
            quality_level=page_payload.get("quality_level", "unavailable"),
            warning_reason=page_payload.get("warning_reason"),
            engine_used=page_payload.get("engine_used", engine),
        )
        for page_payload in payload.get("pages", [])
    ]

    overall_quality, quality_level = _aggregate_quality(pages)
    return OcrPipelineResult(
        document_id=document_id,
        pages=pages,
        overall_quality=overall_quality,
        quality_level=quality_level,
        autofill_eligible=quality_level in {"good", "fair"},
    )
