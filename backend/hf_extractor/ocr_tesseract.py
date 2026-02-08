"""OCR implementation using Tesseract for word-level extraction with bounding boxes."""
import base64
import io
import logging
from typing import Dict, Any, List
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


def ocr_words_and_boxes(
    image_bytes: bytes,
    lang: str = "eng+urd",
    psm: int = 6,
    oem: int = 1
) -> Dict[str, Any]:
    """
    Perform OCR on image bytes and return words with bounding boxes.
    
    Args:
        image_bytes: Image bytes (PNG/JPEG)
        lang: Language hint (default: "eng+urd" for mixed Urdu/English)
        psm: Tesseract page segmentation mode (default: 6 = uniform block)
        oem: Tesseract OCR engine mode (default: 1 = LSTM)
        
    Returns:
        Dict with:
        - engine: "tesseract"
        - engine_params: {"psm": int, "oem": int, "lang": str}
        - page_confidence: float (0..1)
        - words: List[str]
        - boxes: List[List[float]] - pixel coordinates [x1, y1, x2, y2]
        - word_confidences: List[float] (optional)
        - normalized: False (boxes are in pixel coordinates)
        - image_width: int
        - image_height: int
    """
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Get image dimensions
        image_width, image_height = image.size
        
        # Convert to RGB if necessary (tesseract expects RGB)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Run tesseract OCR with word-level data
        # Output format: pytesseract.Output.DICT gives structured data
        custom_config = f"--oem {oem} --psm {psm}"
        ocr_data = pytesseract.image_to_data(
            image,
            lang=lang,
            output_type=pytesseract.Output.DICT,
            config=custom_config
        )
        
        # Extract words and boxes, filtering out empty/confidence==-1
        words = []
        boxes = []
        word_confidences = []
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            # Filter out empty words and low-confidence detections (conf == -1 means uncertain)
            if not text or conf == -1:
                continue
            
            # Get bounding box coordinates
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]
            
            # Convert to [x1, y1, x2, y2] format (pixel coordinates)
            x1 = float(x)
            y1 = float(y)
            x2 = float(x + w)
            y2 = float(y + h)
            
            words.append(text)
            boxes.append([x1, y1, x2, y2])
            
            # Normalize confidence to 0..1 (tesseract gives 0-100)
            normalized_conf = max(0.0, min(1.0, conf / 100.0))
            word_confidences.append(normalized_conf)
        
        # Compute page confidence as mean of word confidences
        if word_confidences:
            page_confidence = sum(word_confidences) / len(word_confidences)
        else:
            page_confidence = 0.0
        
        logger.debug(
            f"OCR completed: words={len(words)}, "
            f"page_confidence={page_confidence:.3f}, "
            f"image_size={image_width}x{image_height}, lang={lang}, psm={psm}, oem={oem}"
        )
        
        return {
            "engine": "tesseract",
            "engine_params": {
                "psm": psm,
                "oem": oem,
                "lang": lang,
            },
            "page_confidence": page_confidence,
            "words": words,
            "boxes": boxes,
            "word_confidences": word_confidences,
            "normalized": False,  # Boxes are in pixel coordinates, not normalized
            "image_width": image_width,
            "image_height": image_height,
        }
        
    except Exception as e:
        logger.error(f"OCR failed: {str(e)}")
        # Return empty result on error
        return {
            "engine": "tesseract",
            "engine_params": {
                "psm": psm,
                "oem": oem,
                "lang": lang,
            },
            "page_confidence": 0.0,
            "words": [],
            "boxes": [],
            "word_confidences": [],
            "normalized": False,
            "image_width": 0,
            "image_height": 0,
        }

