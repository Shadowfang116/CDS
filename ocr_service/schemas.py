from typing import Literal

from pydantic import BaseModel, Field


class WordBox(BaseModel):
    text: str
    confidence: float | None = None
    bbox: list[float] = Field(default_factory=list)


class OcrRequest(BaseModel):
    document_id: str
    pages: list[str]
    engine: Literal["surya", "tesseract"] = "surya"


class OcrPageResult(BaseModel):
    page_num: int = 0
    text: str = ""
    confidence: float | None = None
    quality_score: float | None = None
    quality_level: Literal["good", "fair", "poor", "unusable", "unavailable"] = "unavailable"
    warning_reason: str | None = None
    engine_used: str
    word_boxes: list[WordBox] = Field(default_factory=list)


class OcrResponse(BaseModel):
    document_id: str
    pages: list[OcrPageResult]
