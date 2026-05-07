export const FIELD_LABELS: Record<string, { label: string; subtitle: string }> = {
  'party.name.raw': {
    label: 'Transferor / Seller',
    subtitle: 'Name of current owner transferring the property',
  },
  'property.scheme_name': {
    label: 'Housing Scheme / Society',
    subtitle: 'Name of the registered housing society or scheme',
  },
  'property.phase': {
    label: 'Phase',
    subtitle: 'Phase number within the housing scheme',
  },
  'property.block': {
    label: 'Block',
    subtitle: 'Block identifier within the phase',
  },
  'property.plot_no': {
    label: 'Plot Number',
    subtitle: 'Unique plot number as registered',
  },
  'document.type': {
    label: 'Document Type',
    subtitle: 'Type of legal document (e.g. Sale Deed, Transfer Letter)',
  },
  'ownership.type': {
    label: 'Title Type',
    subtitle: 'Nature of ownership title (freehold, leasehold, etc.)',
  },
};

export function getFieldLabelMeta(fieldKey: string): { label: string; subtitle: string } {
  const mapped = FIELD_LABELS[fieldKey];
  if (mapped) {
    return mapped;
  }

  const parts = fieldKey.split('.');
  const fallback = parts[parts.length - 1]
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

  return {
    label: fallback,
    subtitle: 'Review extracted value and confirm against source document',
  };
}
