#!/usr/bin/env python3
"""
Evaluate a trained LayoutXLM token-classification model.

Usage:
    python eval_layoutxlm_token_cls.py \
        --model models/layoutxlm-tokencls-v1 \
        --eval_data datasets/val.jsonl \
        --output_metrics metrics.json
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any
import torch
from transformers import AutoProcessor, AutoModelForTokenClassification
from datasets import Dataset
from seqeval.metrics import precision_score, recall_score, f1_score, classification_report
import numpy as np


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load JSONL file."""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def evaluate_model(
    model_dir: str,
    eval_data: List[Dict[str, Any]],
    device: str = "cpu"
) -> Dict[str, Any]:
    """Evaluate model on dataset.
    
    Args:
        model_dir: Directory containing trained model
        eval_data: List of evaluation examples
        device: Device to use
        
    Returns:
        Dictionary of metrics
    """
    # Load processor and model
    processor = AutoProcessor.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForTokenClassification.from_pretrained(model_dir, trust_remote_code=True)
    model.to(device)
    model.eval()
    
    # Get label mappings
    id2label = model.config.id2label
    
    # Prepare data
    all_predictions = []
    all_labels = []
    
    from PIL import Image
    
    for entry in eval_data:
        image_path = entry["image_path"]
        words = entry["words"]
        boxes = entry["bboxes_norm_1000"]
        true_labels = entry["labels"]
        
        # Load image
        if Path(image_path).exists():
            image = Image.open(image_path).convert("RGB")
        else:
            image = Image.new("RGB", (1000, 1000), color="white")
        
        # Process
        encoding = processor(
            images=image,
            words=words,
            boxes=boxes,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=512,
        )
        
        # Move to device
        encoding = {k: v.to(device) if hasattr(v, 'to') else v for k, v in encoding.items()}
        
        # Predict
        with torch.no_grad():
            outputs = model(**encoding)
            predictions = torch.argmax(outputs.logits, dim=-1)
        
        # Convert to labels
        pred_labels = [id2label[p.item()] if p.item() in id2label else "O" for p in predictions[0]]
        true_labels_list = true_labels
        
        # Align lengths (handle truncation)
        min_len = min(len(pred_labels), len(true_labels_list))
        all_predictions.append(pred_labels[:min_len])
        all_labels.append(true_labels_list[:min_len])
    
    # Compute metrics
    precision = precision_score(all_labels, all_predictions)
    recall = recall_score(all_labels, all_predictions)
    f1 = f1_score(all_labels, all_predictions)
    
    # Detailed report
    report = classification_report(all_labels, all_predictions, output_dict=True)
    
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "report": report,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate LayoutXLM token-classification model")
    parser.add_argument("--model", required=True, help="Model directory")
    parser.add_argument("--eval_data", required=True, help="Evaluation JSONL file")
    parser.add_argument("--output_metrics", help="Output JSON file for metrics")
    
    args = parser.parse_args()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load evaluation data
    print(f"Loading evaluation data from: {args.eval_data}")
    eval_data = load_jsonl(args.eval_data)
    print(f"  Loaded {len(eval_data)} examples")
    
    # Evaluate
    print("\nRunning evaluation...")
    metrics = evaluate_model(args.model, eval_data, device=device)
    
    # Print results
    print("\n=== Evaluation Metrics ===")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1: {metrics['f1']:.4f}")
    
    # Per-label metrics
    print("\n=== Per-Label Metrics ===")
    report = metrics.get("report", {})
    VALID_LABELS = ["PERSON_NAME", "CNIC", "PLOT_NO", "SCHEME_NAME", "REGISTRY_NO", "DATE", "AMOUNT"]
    
    for label in VALID_LABELS:
        # Check both B- and I- prefixes
        b_label = f"B-{label}"
        i_label = f"I-{label}"
        
        b_metrics = report.get(b_label, {})
        i_metrics = report.get(i_label, {})
        
        if b_metrics or i_metrics:
            # Aggregate B- and I- metrics
            precision = (b_metrics.get("precision", 0) + i_metrics.get("precision", 0)) / 2 if (b_metrics and i_metrics) else (b_metrics.get("precision", 0) or i_metrics.get("precision", 0))
            recall = (b_metrics.get("recall", 0) + i_metrics.get("recall", 0)) / 2 if (b_metrics and i_metrics) else (b_metrics.get("recall", 0) or i_metrics.get("recall", 0))
            f1 = (b_metrics.get("f1-score", 0) + i_metrics.get("f1-score", 0)) / 2 if (b_metrics and i_metrics) else (b_metrics.get("f1-score", 0) or i_metrics.get("f1-score", 0))
            
            print(f"{label}: P={precision:.4f} R={recall:.4f} F1={f1:.4f}")
    
    # Save metrics
    if args.output_metrics:
        print(f"\nSaving metrics to: {args.output_metrics}")
        with open(args.output_metrics, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    print("\nEvaluation complete!")


if __name__ == "__main__":
    main()

