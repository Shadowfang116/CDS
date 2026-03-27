/** Phase 10: OCR Review types */
export interface OcrReviewData {
  page_id: string;
  page_number: number;
  image_url: string;
  ocr: {
    text: string;
    source: "override" | "ocr";
    confidence: number | null;
    has_override: boolean;
    override: {
      user_id: string | null;
      updated_at: string | null;
      reason: string | null;
    } | null;
  };
  meta: Record<string, any>;
}

export interface OcrOverrideRequest {
  override_text: string;
  reason?: string;
}

export interface OcrRerunOptions {
  force_profile?: "basic" | "enhanced";
  force_detect?: boolean;
  force_lang?: "urd" | "urd+eng" | "eng";
  force_layout?: boolean;
  force_pdf_text_layer?: boolean;
  engine_mode?: "tesseract" | "ensemble";
}
