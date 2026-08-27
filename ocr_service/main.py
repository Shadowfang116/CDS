import asyncio
import base64
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import numpy as np
from fastapi import FastAPI, HTTPException
from PIL import Image

from engines.tesseract_engine import run_tesseract
from preprocessing import preprocess_page
from quality import score_page
from schemas import OcrPageResult, OcrRequest, OcrResponse

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="OCR Service", version="0.1.0")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ocr_service", "default_engine": "tesseract", "engine": "tesseract"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s", name, raw_value, default)
        return default
    return max(1, value)


REQUESTED_DEFAULT_ENGINE = "tesseract"
OCR_MAX_CONCURRENT_PAGES = _env_int("OCR_MAX_CONCURRENT_PAGES", 2)
OCR_MAX_WORKERS = _env_int("OCR_MAX_WORKERS", 1)
_THREAD_POOL_EXECUTOR: ThreadPoolExecutor | None = None


def _normalize_engine_name(engine_name: str | None) -> str:
    return "tesseract"


def _resolve_engine_name(engine_name: str | None) -> str:
    return "tesseract"


@app.on_event("startup")
async def startup_event() -> None:
    global _THREAD_POOL_EXECUTOR

    loop = asyncio.get_running_loop()
    if _THREAD_POOL_EXECUTOR is None:
        _THREAD_POOL_EXECUTOR = ThreadPoolExecutor(
            max_workers=OCR_MAX_WORKERS,
            thread_name_prefix="ocr-page",
        )
        loop.set_default_executor(_THREAD_POOL_EXECUTOR)

    logger.info(
        "OCR startup engine=%s max_concurrent_pages=%s max_workers=%s",
        REQUESTED_DEFAULT_ENGINE,
        OCR_MAX_CONCURRENT_PAGES,
        OCR_MAX_WORKERS,
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _THREAD_POOL_EXECUTOR

    if _THREAD_POOL_EXECUTOR is not None:
        _THREAD_POOL_EXECUTOR.shutdown(wait=False)
        _THREAD_POOL_EXECUTOR = None


def _decode_page_source(source: str) -> np.ndarray:
    if not source:
        raise ValueError("Page source is empty")

    if os.path.exists(source):
        with open(source, "rb") as handle:
            raw_bytes = handle.read()
    else:
        payload = source.split(",", 1)[1] if source.startswith("data:") and "," in source else source
        try:
            raw_bytes = base64.b64decode(payload, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Page source is neither a valid file path nor base64 image data") from exc

    image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    return np.array(image)


def _select_engine(engine_name: str) -> Callable[[np.ndarray], OcrPageResult]:
    return run_tesseract


def _process_page_sync(page_num: int, source: str, engine_name: str) -> OcrPageResult:
    image = _decode_page_source(source)
    processed = preprocess_page(image)
    engine = _select_engine("tesseract")
    page_result = engine(processed)

    if page_result.quality_level != "unavailable":
        quality = score_page(page_result.text, page_result.word_boxes)
        page_result.quality_score = quality.quality_score
        page_result.quality_level = quality.quality_level
        if quality.warning_reason and not page_result.warning_reason:
            page_result.warning_reason = quality.warning_reason
    else:
        page_result.quality_score = 0.0

    page_result.page_num = page_num
    return page_result


@app.post("/ocr", response_model=OcrResponse)
async def run_ocr(request: OcrRequest) -> OcrResponse:
    if not request.pages:
        raise HTTPException(status_code=400, detail="At least one page image is required")

    effective_engine = "tesseract"
    batch_size = min(OCR_MAX_CONCURRENT_PAGES, len(request.pages))
    logger.info(
        "OCR request document_id=%s page_count=%s engine=%s batch_size=%s",
        request.document_id,
        len(request.pages),
        effective_engine,
        batch_size,
    )

    pages: list[OcrPageResult] = []
    for start_index in range(0, len(request.pages), batch_size):
        batch = list(enumerate(request.pages[start_index:start_index + batch_size], start=start_index + 1))
        tasks = [
            asyncio.to_thread(_process_page_sync, page_num, source, request.engine)
            for page_num, source in batch
        ]
        pages.extend(await asyncio.gather(*tasks))

    return OcrResponse(document_id=request.document_id, pages=pages)

