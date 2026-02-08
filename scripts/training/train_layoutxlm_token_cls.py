#!/usr/bin/env python3
"""
Train LayoutXLM token-classification model using Transformers Trainer.

Usage:
    python train_layoutxlm_token_cls.py \
        --model microsoft/layoutxlm-base \
        --train_data datasets/train.jsonl \
        --val_data datasets/val.jsonl \
        --output_dir models/layoutxlm-tokencls-v1 \
        --epochs 5 \
        --lr 5e-5 \
        --batch_size 2 \
        --grad_accum 8
"""
import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any
import torch
from transformers import (
    AutoProcessor,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
)
from datasets import Dataset
from seqeval.metrics import precision_score, recall_score, f1_score, classification_report
import numpy as np


VALID_LABELS = ["PERSON_NAME", "CNIC", "PLOT_NO", "SCHEME_NAME", "REGISTRY_NO", "DATE", "AMOUNT"]
ALL_LABELS = ["O"] + [f"{prefix}-{label}" for prefix in ["B", "I"] for label in VALID_LABELS]


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load JSONL file."""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def prepare_dataset(
    data: List[Dict[str, Any]],
    processor: AutoProcessor,
    max_length: int = 512
) -> Dataset:
    """Prepare dataset for training.
    
    Args:
        data: List of dataset entries (words, bboxes_norm_1000, labels)
        processor: LayoutXLM processor
        max_length: Maximum sequence length
        
    Returns:
        HuggingFace Dataset
    """
    images = []
    words_list = []
    boxes_list = []
    labels_list = []
    
    for entry in data:
        image_path = entry["image_path"]
        
        # Load image
        from PIL import Image
        if os.path.exists(image_path):
            image = Image.open(image_path).convert("RGB")
        else:
            # If image not found, create a dummy image (training may still work with boxes/words)
            print(f"Warning: Image not found: {image_path}, using dummy")
            image = Image.new("RGB", (1000, 1000), color="white")
        
        images.append(image)
        words_list.append(entry["words"])
        boxes_list.append(entry["bboxes_norm_1000"])
        labels_list.append(entry["labels"])
    
    # Process with processor (batch processing)
    # Note: processor expects lists, so we process one by one and then combine
    all_input_ids = []
    all_attention_mask = []
    all_bbox = []
    all_labels = []
    
    for image, words, boxes, labels in zip(images, words_list, boxes_list, labels_list):
        encoding = processor(
            images=image,
            words=words,
            boxes=boxes,
            word_labels=labels,
            padding="max_length",
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        
        all_input_ids.append(encoding["input_ids"].squeeze(0).tolist())
        all_attention_mask.append(encoding["attention_mask"].squeeze(0).tolist())
        all_bbox.append(encoding["bbox"].squeeze(0).tolist())
        
        # Labels are encoded as word_labels by processor
        if "word_labels" in encoding:
            all_labels.append(encoding["word_labels"].squeeze(0).tolist())
        else:
            # Fallback: convert labels to IDs manually
            label2id = {label: i for i, label in enumerate(ALL_LABELS)}
            label_ids = [label2id.get(label, 0) for label in labels]
            # Pad to max_length
            label_ids = label_ids[:max_length] + [0] * (max_length - len(label_ids))
            all_labels.append(label_ids)
    
    # Convert to dataset
    dataset_dict = {
        "input_ids": all_input_ids,
        "attention_mask": all_attention_mask,
        "bbox": all_bbox,
        "labels": all_labels,
    }
    
    return Dataset.from_dict(dataset_dict)


def compute_metrics(eval_pred):
    """Compute precision/recall/F1 using seqeval."""
    predictions, labels = eval_pred
    
    # Convert predictions to labels
    predictions = np.argmax(predictions, axis=2)
    
    # Remove ignored index (special tokens)
    true_predictions = []
    true_labels = []
    
    # Get label mapping from processor/tokenizer
    # This is a simplification; in practice, you'd need to map token-level predictions to word-level labels
    # For now, we'll assume the labels are aligned
    
    # Convert to label strings
    id2label = {i: label for i, label in enumerate(ALL_LABELS)}
    
    for prediction, label in zip(predictions, labels):
        pred_labels = [id2label[p] if p < len(id2label) else "O" for p in prediction]
        true_labels_list = [id2label[l] if l < len(id2label) else "O" for l in label if l != -100]
        
        # Align lengths
        min_len = min(len(pred_labels), len(true_labels_list))
        true_predictions.append(pred_labels[:min_len])
        true_labels.append(true_labels_list[:min_len])
    
    # Compute metrics
    precision = precision_score(true_labels, true_predictions)
    recall = recall_score(true_labels, true_predictions)
    f1 = f1_score(true_labels, true_predictions)
    
    # Detailed report
    report = classification_report(true_labels, true_predictions, output_dict=True)
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "report": report,
    }


def main():
    parser = argparse.ArgumentParser(description="Train LayoutXLM token-classification model")
    parser.add_argument("--model", default="microsoft/layoutxlm-base", help="Base model name")
    parser.add_argument("--train_data", required=True, help="Training JSONL file")
    parser.add_argument("--val_data", required=True, help="Validation JSONL file")
    parser.add_argument("--output_dir", required=True, help="Output directory for trained model")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=2, help="Batch size (CPU-friendly)")
    parser.add_argument("--grad_accum", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--max_steps", type=int, help="Maximum training steps (optional)")
    parser.add_argument("--fp16", action="store_true", help="Enable mixed precision (CUDA only)")
    parser.add_argument("--max_length", type=int, default=512, help="Maximum sequence length")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Check CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    if args.fp16 and device == "cpu":
        print("Warning: fp16 requested but CUDA not available, disabling fp16")
        args.fp16 = False
    
    # Load processor
    print(f"Loading processor from: {args.model}")
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=True)
    
    # Create label mappings
    id2label = {i: label for i, label in enumerate(ALL_LABELS)}
    label2id = {label: i for i, label in enumerate(ALL_LABELS)}
    
    # Load model
    print(f"Loading model from: {args.model}")
    model = AutoModelForTokenClassification.from_pretrained(
        args.model,
        num_labels=len(ALL_LABELS),
        id2label=id2label,
        label2id=label2id,
        trust_remote_code=True,
    )
    model.to(device)
    
    # Load datasets
    print(f"Loading training data from: {args.train_data}")
    train_data = load_jsonl(args.train_data)
    print(f"  Loaded {len(train_data)} examples")
    
    print(f"Loading validation data from: {args.val_data}")
    val_data = load_jsonl(args.val_data)
    print(f"  Loaded {len(val_data)} examples")
    
    # Prepare datasets
    print("Preparing training dataset...")
    train_dataset = prepare_dataset(train_data, processor, max_length=args.max_length)
    
    print("Preparing validation dataset...")
    val_dataset = prepare_dataset(val_data, processor, max_length=args.max_length)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        fp16=args.fp16,
        logging_dir=os.path.join(args.output_dir, "logs"),
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        max_steps=args.max_steps,
        save_total_limit=3,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )
    
    # Train
    print("\nStarting training...")
    trainer.train()
    
    # Save model
    print(f"\nSaving model to: {args.output_dir}")
    trainer.save_model()
    processor.save_pretrained(args.output_dir)
    
    # Final evaluation
    print("\nRunning final evaluation...")
    eval_results = trainer.evaluate()
    
    print("\n=== Final Metrics ===")
    print(f"Precision: {eval_results.get('eval_precision', 0):.4f}")
    print(f"Recall: {eval_results.get('eval_recall', 0):.4f}")
    print(f"F1: {eval_results.get('eval_f1', 0):.4f}")
    
    # Print detailed report if available
    if "eval_report" in eval_results:
        print("\n=== Per-Label Metrics ===")
        report = eval_results["eval_report"]
        if isinstance(report, dict):
            for label in VALID_LABELS:
                if label in report:
                    print(f"{label}: P={report[label].get('precision', 0):.4f} "
                          f"R={report[label].get('recall', 0):.4f} "
                          f"F1={report[label].get('f1-score', 0):.4f}")
    
    print(f"\nModel saved to: {args.output_dir}")
    print("Training complete!")


if __name__ == "__main__":
    main()

