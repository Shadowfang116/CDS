const ARABIC_SCRIPT_RE =
  /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;

export function hasArabicScript(value: string | null | undefined): boolean {
  return Boolean(value && ARABIC_SCRIPT_RE.test(value));
}

export function urduTextProps(value: string | null | undefined) {
  return {
    lang: hasArabicScript(value) ? ("ur" as const) : undefined,
    dir: "auto" as const,
  };
}
