"""LayoutXLM token-classification inference module with safe optional imports."""
import logging
import os
from typing import List, Tuple, Dict, Any, Optional
import io

logger = logging.getLogger(__name__)

# Module-level cache for loaded model
_model_cache: Optional[Dict[str, Any]] = None


def _is_mojibake_or_corrupted(token: str) -> bool:
    """Check if token looks corrupted (box drawing chars, etc.).
    
    Reused from extractors.py to maintain consistency.
    """
    if not token:
        return True
    
    # Check for box drawing characters (common OCR errors)
    box_chars = ['─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '═', '║', '╔', '╗', '╚', '╝']
    if any(char in token for char in box_chars):
        return True
    
    # Check if token is mostly non-printable or control characters
    if len(token) > 0:
        printable_ratio = sum(1 for c in token if c.isprintable()) / len(token)
        if printable_ratio < 0.5:
            return True
    
    return False


def load_layoutxlm(model_name_or_path: str, device: str = "cpu") -> Tuple[Any, Any, Dict[str, int], Optional[str]]:
    """
    Load LayoutXLM model and processor with safe imports.
    
    Args:
        model_name_or_path: HuggingFace model path or name
        device: Device to use ("cpu" or "cuda")
        
    Returns:
        Tuple of (processor, model, id2label, error_message)
        If loading fails, returns (None, None, {}, error_message)
    """
    global _model_cache
    
    # Check cache first
    cache_key = f"{model_name_or_path}:{device}"
    if _model_cache and _model_cache.get("cache_key") == cache_key:
        logger.debug(f"Using cached LayoutXLM model: {cache_key}")
        return (
            _model_cache["processor"],
            _model_cache["model"],
            _model_cache["id2label"],
            None
        )
    
    # Try imports inside function (safe)
    try:
        from transformers import AutoProcessor, AutoModelForTokenClassification
        import torch
        from PIL import Image
    except ImportError as e:
        error_msg = f"LayoutXLM dependencies not installed: {str(e)}"
        logger.warning(error_msg)
        return None, None, {}, error_msg
    
    try:
        logger.info(f"Loading LayoutXLM model from: {model_name_or_path}")
        
        # Load processor
        processor = AutoProcessor.from_pretrained(
            model_name_or_path,
            trust_remote_code=True,
        )
        
        # Load model
        model = AutoModelForTokenClassification.from_pretrained(
            model_name_or_path,
            trust_remote_code=True,
        )
        
        # Move to device
        model.to(device)
        model.eval()  # Set to evaluation mode
        
        # Get label mappings
        id2label = model.config.id2label if hasattr(model.config, 'id2label') else {}
        label2id = model.config.label2id if hasattr(model.config, 'label2id') else {}
        
        # Cache the loaded model
        _model_cache = {
            "cache_key": cache_key,
            "processor": processor,
            "model": model,
            "id2label": id2label,
            "label2id": label2id,
        }
        
        logger.info(f"LayoutXLM model loaded successfully: {model_name_or_path}")
        return processor, model, id2label, None
        
    except Exception as e:
        error_msg = f"Failed to load LayoutXLM model: {str(e)}"
        logger.error(error_msg)
        return None, None, {}, error_msg


def _normalize_bio_label(label: str) -> str:
    """Normalize BIO tags by stripping B- and I- prefixes."""
    if label.startswith("B-"):
        return label[2:]
    elif label.startswith("I-"):
        return label[2:]
    return label


def _compute_bbox_union(boxes: List[List[int]], indices: List[int]) -> List[int]:
    """Compute union bounding box from boxes at given indices."""
    if not indices or not boxes:
        return [0, 0, 0, 0]
    
    selected_boxes = [boxes[i] for i in indices if i < len(boxes)]
    if not selected_boxes:
        return [0, 0, 0, 0]
    
    min_x1 = min(box[0] for box in selected_boxes)
    min_y1 = min(box[1] for box in selected_boxes)
    max_x2 = max(box[2] for box in selected_boxes)
    max_y2 = max(box[3] for box in selected_boxes)
    
    return [min_x1, min_y1, max_x2, max_y2]


def infer_layoutxlm_entities(
    image_bytes: bytes,
    words: List[str],
    boxes_norm_1000: List[List[int]],
    options: Any,  # ExtractOptions
) -> Tuple[List[Any], Dict[str, Any]]:  # Returns List[ExtractedEntityData-like], metadata dict
    """
    Run LayoutXLM token-classification inference on image + OCR words/boxes.
    
    Args:
        image_bytes: Image bytes (PNG/JPEG)
        words: List of OCR words
        boxes_norm_1000: Per-word bounding boxes in 0-1000 normalized coordinates
        options: ExtractOptions with model configuration
        
    Returns:
        Tuple of (entities_list, metadata_dict)
        If model not available or inference fails, returns ([], {"model_loaded": False, "error": "..."})
    """
    from extractors import ExtractedEntityData, _get_snippet
    from schemas import VALID_LABELS
    
    # Determine model path
    model_name_or_path = options.model_name_or_path
    if not model_name_or_path:
        model_name_or_path = os.getenv("HF_LAYOUTXLM_MODEL_PATH", "")
    
    if not model_name_or_path:
        return [], {
            "model_loaded": False,
            "error": "No model path provided (set model_name_or_path in options or HF_LAYOUTXLM_MODEL_PATH env)"
        }
    
    device = os.getenv("HF_DEVICE", "cpu")
    
    # Load model (with safe imports)
    processor, model, id2label, error = load_layoutxlm(model_name_or_path, device)
    
    if processor is None or model is None:
        return [], {
            "model_loaded": False,
            "error": error or "Model loading failed"
        }
    
    # P12: Skip LayoutXLM if boxes are None (text-only OCR)
    if boxes_norm_1000 is None:
        logger.warning(
            f"LayoutXLM skipped: boxes are None (text-only OCR). "
            f"Falling back to rules-v1 extractor."
        )
        return [], {
            "model_loaded": True,
            "model_name_or_path": model_name_or_path,
            "error": "LayoutXLM requires bounding boxes; text-only OCR detected, use rules-v1 extractor"
        }
    
    if not words or not boxes_norm_1000 or len(words) != len(boxes_norm_1000):
        return [], {
            "model_loaded": True,
            "model_name_or_path": model_name_or_path,
            "error": "Invalid input: words and boxes must be non-empty and same length"
        }
    
    try:
        # Build PIL image from bytes
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Prepare inputs for processor
        # Note: processor expects boxes in format [[x1, y1, x2, y2], ...]
        encoding = processor(
            images=image,
            words=words,
            boxes=boxes_norm_1000,
            return_tensors="pt",
            truncation=True,
            padding=True,
        )
        
        # Move inputs to device
        encoding = {k: v.to(device) if hasattr(v, 'to') else v for k, v in encoding.items()}
        
        # Run inference
        import torch
        with torch.no_grad():
            outputs = model(**encoding)
        
        # Get predictions (logits)
        logits = outputs.logits  # Shape: (batch_size, sequence_length, num_labels)
        probs = torch.nn.functional.softmax(logits, dim=-1)
        predictions = torch.argmax(probs, dim=-1)
        
        # Get word_ids mapping (which word each token corresponds to)
        word_ids = encoding.get('word_ids', [])
        if word_ids is None or len(word_ids) == 0:
            # Fallback: assume sequential if word_ids not available
            word_ids = list(range(len(words)))
        
        # Map predictions to words
        word_predictions = {}  # word_idx -> (label_id, confidence)
        
        for token_idx, (pred_label_id, prob_dist) in enumerate(zip(predictions[0], probs[0])):
            word_id = word_ids[token_idx] if token_idx < len(word_ids) else None
            
            # Skip special tokens (word_id is None)
            if word_id is None:
                continue
            
            # Get label string
            label_str = id2label.get(int(pred_label_id), "O")
            normalized_label = _normalize_bio_label(label_str)
            
            # Only accept labels in VALID_LABELS
            if normalized_label not in VALID_LABELS:
                normalized_label = "O"
            
            # Get confidence (max probability for this token)
            confidence = float(prob_dist[pred_label_id])
            
            # Keep highest confidence prediction per word (if multiple tokens map to same word)
            if word_id not in word_predictions or confidence > word_predictions[word_id][1]:
                word_predictions[word_id] = (normalized_label, confidence)
        
        # Get confidence thresholds from options
        min_confidence = options.min_entity_confidence if options.min_entity_confidence is not None else 0.60
        min_confidence_cnic = options.min_entity_confidence_cnic if options.min_entity_confidence_cnic is not None else 0.70
        return_low_confidence = options.return_low_confidence if options.return_low_confidence is not None else False
        
        # Convert word predictions to entity spans
        entities = []
        current_span = None  # (label, start_idx, confidences)
        
        def create_entity_from_span(span_label, span_start, span_end, span_confs):
            """Helper to create entity from span with guardrails."""
            token_indices = list(range(span_start, span_end))
            
            # P19: Check for corruption in ANY token in span (strict guard)
            entity_words = [words[i] for i in token_indices]
            if any(_is_mojibake_or_corrupted(word) for word in entity_words):
                return None  # Drop entity if any token is corrupted
            
            # P19: Build value strictly from OCR tokens (token-copy only)
            value = " ".join(entity_words)
            
            # Compute bbox union (normalized)
            bbox_norm_1000 = _compute_bbox_union(boxes_norm_1000, token_indices)
            
            # Average confidence
            avg_confidence = sum(span_confs) / len(span_confs) if span_confs else 0.0
            
            # P19: Apply confidence threshold
            threshold = min_confidence_cnic if span_label == "CNIC" else min_confidence
            if avg_confidence < threshold and not return_low_confidence:
                return None  # Drop entity below threshold
            
            # Get snippet (reuse helper from extractors)
            snippet = _get_snippet(words, token_indices, window=5)
            
            entity = ExtractedEntityData(
                label=span_label,
                value=value,  # P19: Always built from OCR tokens only
                confidence=avg_confidence,
                token_indices=token_indices,
                bbox=[0.0, 0.0, 0.0, 0.0],  # Pixel bbox will be computed from OCR boxes in main.py
                bbox_norm_1000=bbox_norm_1000,
            )
            
            # P19: Add low_confidence flag (pack into entity metadata via attribute if needed)
            # We'll add this as an attribute on the entity object
            entity.low_confidence = avg_confidence < threshold
            
            return entity
        
        for word_idx in range(len(words)):
            if word_idx not in word_predictions:
                label = "O"
                confidence = 0.0
            else:
                label, confidence = word_predictions[word_idx]
            
            if label != "O":
                if current_span and current_span[0] == label:
                    # Extend current span
                    current_span = (label, current_span[1], current_span[2] + [confidence])
                else:
                    # Start new span (save previous if exists)
                    if current_span and current_span[0] != "O":
                        span_label, span_start, span_confs = current_span
                        span_end = word_idx
                        entity = create_entity_from_span(span_label, span_start, span_end, span_confs)
                        if entity:
                            entities.append(entity)
                    
                    # Start new span
                    current_span = (label, word_idx, [confidence])
            else:
                # Label is O, end current span if exists
                if current_span and current_span[0] != "O":
                    span_label, span_start, span_confs = current_span
                    span_end = word_idx
                    entity = create_entity_from_span(span_label, span_start, span_end, span_confs)
                    if entity:
                        entities.append(entity)
                
                current_span = None
        
        # Handle trailing span
        if current_span and current_span[0] != "O":
            span_label, span_start, span_confs = current_span
            span_end = len(words)
            entity = create_entity_from_span(span_label, span_start, span_end, span_confs)
            if entity:
                entities.append(entity)
        
        # Count entities by label
        entities_by_label = {}
        for entity in entities:
            entities_by_label[entity.label] = entities_by_label.get(entity.label, 0) + 1
        
        logger.info(
            f"LayoutXLM inference completed: entities={len(entities)} "
            f"entities_by_label={entities_by_label}"
        )
        
        return entities, {
            "model_loaded": True,
            "model_name_or_path": model_name_or_path,
            "entities_by_label": entities_by_label,
        }
        
    except Exception as e:
        error_msg = f"LayoutXLM inference failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [], {
            "model_loaded": True,
            "model_name_or_path": model_name_or_path,
            "error": error_msg
        }

