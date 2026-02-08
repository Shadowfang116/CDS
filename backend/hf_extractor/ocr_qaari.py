"""Qaari OCR module for Urdu-heavy document transcription (optional VLM-based OCR)."""
import logging
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Module-level cache for loaded model
_model_cache: Optional[Dict[str, Any]] = None


def qaari_transcribe(
    image: Any,  # PIL.Image
    model_name_or_path: str,
    device: str = "cpu"
) -> Dict[str, Any]:
    """
    Transcribe image text using Qaari vision-language model.
    
    Args:
        image: PIL.Image object
        model_name_or_path: HuggingFace model path or name (e.g., "oddadmix/Qaari-0.1-Urdu-OCR-VL-2B-Instruct")
        device: Device to use ("cpu" or "cuda")
        
    Returns:
        Dict with:
            - text: str (transcribed text)
            - engine: "qaari_vl"
            - page_confidence: float (0.0-1.0)
            - model_name_or_path: str
            - ocr_text_only: True (always True for Qaari)
    """
    global _model_cache
    
    # Check cache first
    cache_key = f"{model_name_or_path}:{device}"
    if _model_cache and _model_cache.get("cache_key") == cache_key:
        logger.debug(f"Using cached Qaari model: {cache_key}")
        processor = _model_cache["processor"]
        model = _model_cache["model"]
    else:
        # Safe imports inside function
        try:
            from transformers import AutoProcessor, AutoModelForVision2Seq
            import torch
        except ImportError as e:
            error_msg = f"Qaari dependencies not installed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            logger.info(f"Loading Qaari model from: {model_name_or_path}")
            
            # Load processor
            processor = AutoProcessor.from_pretrained(
                model_name_or_path,
                trust_remote_code=True,
            )
            
            # Load model
            model = AutoModelForVision2Seq.from_pretrained(
                model_name_or_path,
                trust_remote_code=True,
            )
            
            # Move to device
            model.to(device)
            model.eval()  # Set to evaluation mode
            
            # Cache the loaded model
            _model_cache = {
                "cache_key": cache_key,
                "processor": processor,
                "model": model,
            }
            
            logger.info(f"Qaari model loaded successfully: {model_name_or_path}")
            
        except Exception as e:
            error_msg = f"Failed to load Qaari model: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    try:
        # Prepare prompt (deterministic, minimal, transcription-only)
        prompt = "Transcribe the text in this image exactly. Return only the raw text. Do not add explanations."
        
        # Process image and prompt
        inputs = processor(images=image, text=prompt, return_tensors="pt")
        
        # Move inputs to device
        inputs = {k: v.to(device) if hasattr(v, 'to') else v for k, v in inputs.items()}
        
        # Run inference
        import torch
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=512)
        
        # Decode output
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Clean up generated text (remove prompt artifacts if any)
        text = generated_text.strip()
        
        # Confidence heuristic: deterministic based on text length
        # min(0.70, max(0.30, len(text)/2000))
        text_length = len(text)
        confidence = min(0.70, max(0.30, text_length / 2000.0))
        
        logger.info(
            f"Qaari transcription completed: "
            f"text_length={text_length} confidence={confidence:.3f}"
        )
        
        return {
            "text": text,
            "engine": "qaari_vl",
            "page_confidence": confidence,
            "model_name_or_path": model_name_or_path,
            "ocr_text_only": True,
        }
        
    except Exception as e:
        error_msg = f"Qaari transcription failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg)

