function normalizeQualityLevel(value?: string | null): string {
  return (value ?? '').trim().toLowerCase();
}

export function formatDocumentType(value?: string | null): string {
  return value ? value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : '';
}

export function formatQualityLabel(value?: string | null): string {
  return formatDocumentType(normalizeQualityLevel(value));
}

export function getQualityToneClass(value?: string | null): string {
  switch (normalizeQualityLevel(value)) {
    case 'good':
      return 'cds-quality-good';
    case 'fair':
      return 'cds-quality-fair';
    case 'poor':
      return 'cds-quality-poor';
    case 'unusable':
      return 'cds-quality-unusable';
    default:
      return 'cds-quality-unknown';
  }
}
