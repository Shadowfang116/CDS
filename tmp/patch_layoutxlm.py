MARKER = "            # P19: Add low_confidence flag (pack into entity metadata via attribute if needed)"
REPLACEMENT = '''            # P19: Add low_confidence flag (pack into entity metadata via attribute if needed)
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
'''
import sys
p = sys.argv[1]
text = open(p, 'r', encoding='utf-8').read()
idx = text.find(MARKER)
if idx == -1:
    print("MARKER not found; no change")
    raise SystemExit(0)
new_text = text[:idx] + REPLACEMENT
open(p, 'w', encoding='utf-8', newline='\n').write(new_text)
print("patched", p)
