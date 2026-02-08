"""OCR router with confidence-driven fallback selection."""
import logging
import os
import io
from typing import Dict, Any, List, Optional

from schemas import ExtractOptions
from ocr_tesseract import ocr_words_and_boxes

logger = logging.getLogger(__name__)


def choose_ocr(image_bytes: bytes, options: ExtractOptions) -> Dict[str, Any]:
    """
    Choose OCR method with confidence-driven fallback.
    
    Logic:
    1. Run PRIMARY OCR (tesseract psm=6, oem=1)
    2. If fallback enabled and primary confidence < threshold OR too few words:
       - Run FALLBACK OCR (tesseract psm=11 for sparse text)
    3. If baseline OCR is poor AND Qaari enabled:
       - Run Qaari transcription (text-only, no boxes)
    4. Select best result by confidence, then word count
    
    Args:
        image_bytes: Image bytes (PNG/JPEG)
        options: Extraction options with OCR routing parameters
        
    Returns:
        Dict with selected OCR result plus routing metadata:
        - selected_engine: "tesseract" or "qaari_vl"
        - selected_engine_params: {"psm": int, "oem": int, "lang": str} or {"model": str, "device": str}
        - selected_page_confidence: float
        - used_fallback: bool
        - qaari_used: bool (if Qaari was invoked)
        - ocr_text_only: bool (if Qaari was used)
        - attempts: List[Dict] of all OCR attempts
        - Plus all fields from ocr_words_and_boxes result OR Qaari result
    """
    # Determine language pack
    lang_hint = options.language_hint or "en"
    if lang_hint == "ur":
        lang = "urd+eng"
    elif lang_hint == "en":
        lang = "eng"
    else:  # "mixed" or default
        lang = "eng+urd"
    
    # Get OCR routing options with defaults
    min_confidence = options.min_ocr_confidence if options.min_ocr_confidence is not None else 0.55
    enable_fallback = options.enable_ocr_fallback if options.enable_ocr_fallback is not None else True
    force_fallback = options.force_ocr_fallback if options.force_ocr_fallback is not None else False
    
    attempts: List[Dict[str, Any]] = []
    
    # PRIMARY OCR: tesseract psm=6 (uniform block of text), oem=1 (LSTM)
    primary_result = ocr_words_and_boxes(image_bytes, lang=lang, psm=6, oem=1)
    attempts.append({
        "psm": 6,
        "oem": 1,
        "lang": lang,
        "word_count": len(primary_result["words"]),
        "page_confidence": primary_result["page_confidence"],
    })
    
    primary_confidence = primary_result["page_confidence"]
    primary_word_count = len(primary_result["words"])
    
    logger.debug(
        f"OCR primary: psm=6 lang={lang} "
        f"confidence={primary_confidence:.3f} words={primary_word_count}"
    )
    
    # Determine if fallback should trigger
    should_fallback = force_fallback or (
        enable_fallback and (
            primary_confidence < min_confidence or
            primary_word_count < 10
        )
    )
    
    fallback_result = None
    
    if should_fallback:
        logger.info(
            f"OCR fallback triggered: force={force_fallback} "
            f"enable={enable_fallback} "
            f"primary_conf={primary_confidence:.3f} min={min_confidence} "
            f"primary_words={primary_word_count}"
        )
        
        # FALLBACK OCR: tesseract psm=11 (sparse text)
        fallback_result = ocr_words_and_boxes(image_bytes, lang=lang, psm=11, oem=1)
        attempts.append({
            "psm": 11,
            "oem": 1,
            "lang": lang,
            "word_count": len(fallback_result["words"]),
            "page_confidence": fallback_result["page_confidence"],
        })
        
        fallback_confidence = fallback_result["page_confidence"]
        fallback_word_count = len(fallback_result["words"])
        
        logger.debug(
            f"OCR fallback: psm=11 lang={lang} "
            f"confidence={fallback_confidence:.3f} words={fallback_word_count}"
        )
        
        # Select best result: higher confidence wins; if tie, more words wins
        if fallback_confidence > primary_confidence or (
            fallback_confidence == primary_confidence and fallback_word_count > primary_word_count
        ):
            selected = fallback_result
            used_fallback = True
            logger.info(
                f"OCR selected fallback: conf={fallback_confidence:.3f} words={fallback_word_count} "
                f"(primary: conf={primary_confidence:.3f} words={primary_word_count})"
            )
        else:
            selected = primary_result
            used_fallback = False
            logger.info(
                f"OCR selected primary: conf={primary_confidence:.3f} words={primary_word_count} "
                f"(fallback: conf={fallback_confidence:.3f} words={fallback_word_count})"
            )
    else:
        selected = primary_result
        used_fallback = False
    
    # P12: Check if Qaari fallback should be invoked
    qaari_used = False
    ocr_text_only = False
    qaari_model_name_or_path = None
    
    # Determine if Qaari should be invoked
    selected_conf = selected["page_confidence"]
    selected_word_count = len(selected["words"])
    
    # Check enable_qaari from options or environment
    enable_qaari = options.enable_qaari if options.enable_qaari is not None else False
    if not enable_qaari:
        enable_qaari_env = os.getenv("HF_ENABLE_QAARI", "false").lower()
        enable_qaari = enable_qaari_env in ("true", "1", "yes")
    
    # Get Qaari model path from options or environment
    qaari_model_path = options.qaari_model_name_or_path
    if not qaari_model_path:
        qaari_model_path = os.getenv("HF_QAARI_MODEL_PATH", "")
    
    should_try_qaari = (
        enable_qaari and
        qaari_model_path and
        (selected_conf < min_confidence or selected_word_count < 10)
    )
    
    if should_try_qaari:
        logger.info(
            f"Qaari fallback triggered: baseline_conf={selected_conf:.3f} "
            f"baseline_words={selected_word_count} min_conf={min_confidence}"
        )
        
        try:
            from PIL import Image
            from ocr_qaari import qaari_transcribe
            
            device = os.getenv("HF_DEVICE", "cpu")
            
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Run Qaari transcription
            qaari_result = qaari_transcribe(image, qaari_model_path, device)
            
            # Tokenize Qaari text into words (whitespace tokenization, preserve Urdu tokens)
            qaari_text = qaari_result["text"]
            qaari_words = qaari_text.split() if qaari_text else []
            
            # Build Qaari OCR result (text-only, no boxes)
            qaari_ocr_result = {
                "engine": "qaari_vl",
                "engine_params": {
                    "model": qaari_model_path,
                    "device": device,
                },
                "page_confidence": qaari_result["page_confidence"],
                "words": qaari_words,
                "boxes": None,  # No boxes for text-only OCR
                "word_confidences": None,
                "normalized": False,
                "image_width": selected.get("image_width", 0),
                "image_height": selected.get("image_height", 0),
            }
            
            attempts.append({
                "engine": "qaari_vl",
                "model": qaari_model_path,
                "word_count": len(qaari_words),
                "page_confidence": qaari_result["page_confidence"],
            })
            
            # Prefer Qaari ONLY when baseline is below thresholds
            if selected_conf < min_confidence or selected_word_count < 10:
                selected = qaari_ocr_result
                qaari_used = True
                ocr_text_only = True
                qaari_model_name_or_path = qaari_model_path
                used_fallback = True  # Qaari is a fallback
                
                logger.info(
                    f"OCR selected Qaari: conf={qaari_result['page_confidence']:.3f} "
                    f"words={len(qaari_words)} "
                    f"(baseline: conf={selected_conf:.3f} words={selected_word_count})"
                )
            else:
                logger.info(
                    f"OCR kept baseline (Qaari available but baseline sufficient): "
                    f"baseline_conf={selected_conf:.3f} baseline_words={selected_word_count}"
                )
                
        except ImportError:
            logger.warning("Qaari module not available (VLM deps not installed)")
        except Exception as e:
            logger.error(f"Qaari fallback failed: {str(e)}", exc_info=True)
            # Continue with baseline OCR result
    
    # Build result with routing metadata
    result = {
        **selected,  # Include all fields from selected OCR result
        "selected_engine": selected["engine"],
        "selected_engine_params": selected["engine_params"],
        "selected_page_confidence": selected["page_confidence"],
        "used_fallback": used_fallback,
        "qaari_used": qaari_used,
        "ocr_text_only": ocr_text_only,
        "qaari_model_name_or_path": qaari_model_name_or_path,
        "attempts": attempts,
    }
    
    return result

