import logging
from typing import Any, Iterable

import numpy as np
from PIL import Image

from schemas import OcrPageResult, WordBox

logger = logging.getLogger(__name__)

_SURYA_AVAILABILITY_CHECKED = False
_SURYA_AVAILABLE = False
_SURYA_UNAVAILABLE_REASON = "surya-ocr availability has not been checked"
_SURYA_RUNNER: Any | None = None


def get_surya_availability() -> tuple[bool, str | None]:
    global _SURYA_AVAILABILITY_CHECKED
    global _SURYA_AVAILABLE
    global _SURYA_UNAVAILABLE_REASON
    global _SURYA_RUNNER

    if _SURYA_AVAILABILITY_CHECKED:
        return _SURYA_AVAILABLE, None if _SURYA_AVAILABLE else _SURYA_UNAVAILABLE_REASON

    _SURYA_AVAILABILITY_CHECKED = True
    try:
        import surya.ocr as surya_ocr

        runner = getattr(surya_ocr, "run_ocr", None) or getattr(surya_ocr, "ocr", None)
        if runner is None:
            _SURYA_AVAILABLE = False
            _SURYA_UNAVAILABLE_REASON = "surya.ocr has no run_ocr/ocr entrypoint"
        else:
            _SURYA_AVAILABLE = True
            _SURYA_UNAVAILABLE_REASON = ""
            _SURYA_RUNNER = runner
    except Exception as exc:  # noqa: BLE001
        _SURYA_AVAILABLE = False
        _SURYA_UNAVAILABLE_REASON = f"surya-ocr unavailable: {exc}"

    return _SURYA_AVAILABLE, None if _SURYA_AVAILABLE else _SURYA_UNAVAILABLE_REASON


def _to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image, mode="L")
    return Image.fromarray(image, mode="RGB")


def _extract_nodes(node: Any) -> Iterable[Any]:
    if node is None:
        return []

    if isinstance(node, (list, tuple)):
        items = []
        for item in node:
            items.extend(list(_extract_nodes(item)))
        return items

    if isinstance(node, dict):
        if any(key in node for key in ("text", "bbox", "polygon")):
            return [node]
        items = []
        for value in node.values():
            items.extend(list(_extract_nodes(value)))
        return items

    children = []
    for attr in ("words", "lines", "text_lines", "tokens", "pages"):
        value = getattr(node, attr, None)
        if value:
            children.extend(list(_extract_nodes(value)))

    if children:
        return children

    if any(hasattr(node, attr) for attr in ("text", "bbox", "polygon")):
        return [node]

    return []


def _node_text(node: Any) -> str:
    if isinstance(node, dict):
        return str(node.get("text", "")).strip()
    return str(getattr(node, "text", "")).strip()


def _node_confidence(node: Any) -> float | None:
    value = node.get("confidence") if isinstance(node, dict) else getattr(node, "confidence", None)
    try:
        if value is None:
            return None
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if numeric > 1.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, numeric))


def _node_bbox(node: Any) -> list[float]:
    value = node.get("bbox") if isinstance(node, dict) else getattr(node, "bbox", None)
    if value is None:
        value = node.get("polygon") if isinstance(node, dict) else getattr(node, "polygon", None)
    if value is None:
        return []

    if isinstance(value, (list, tuple)) and len(value) == 4 and not isinstance(value[0], (list, tuple)):
        return [float(item) for item in value]

    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        xs = [float(point[0]) for point in value]
        ys = [float(point[1]) for point in value]
        return [min(xs), min(ys), max(xs), max(ys)]

    return []


def run_surya(image: np.ndarray) -> OcrPageResult:
    available, unavailable_reason = get_surya_availability()
    if not available:
        return OcrPageResult(
            engine_used="surya",
            quality_level="unavailable",
            warning_reason=unavailable_reason or "surya-ocr unavailable",
            confidence=0.0,
        )

    pil_image = _to_pil(image)

    try:
        runner = _SURYA_RUNNER
        if runner is None:
            raise RuntimeError("surya-ocr runner not available")

        try:
            raw_result = runner(pil_image)
        except TypeError:
            raw_result = runner([pil_image])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Surya OCR failed: %s", exc)
        return OcrPageResult(
            engine_used="surya",
            quality_level="unavailable",
            warning_reason=f"Surya OCR failed: {exc}",
            confidence=0.0,
        )

    boxes: list[WordBox] = []
    confidences: list[float] = []
    texts: list[str] = []

    for node in _extract_nodes(raw_result):
        text = _node_text(node)
        if not text:
            continue
        confidence = _node_confidence(node)
        if confidence is not None:
            confidences.append(confidence)
        texts.append(text)
        boxes.append(
            WordBox(
                text=text,
                confidence=confidence,
                bbox=_node_bbox(node),
            )
        )

    if not texts:
        logger.warning("Surya OCR returned no text nodes; marking result unavailable")
        return OcrPageResult(
            engine_used="surya",
            quality_level="unavailable",
            warning_reason="Surya returned no text nodes",
            confidence=0.0,
        )

    average_confidence = sum(confidences) / len(confidences) if confidences else None
    return OcrPageResult(
        engine_used="surya",
        text="\n".join(texts),
        confidence=average_confidence,
        quality_level="fair",
        word_boxes=boxes,
    )
