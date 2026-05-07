import rulesEvidenceLibrary from './rules_evidence.json';

type RuleEvidenceDefinitionSource = {
  required_evidence: string[];
  acceptable_substitutes: string[];
  closure_guidance?: string;
  cp_recommended_text?: string;
};

export type RuleEvidenceDefinition = {
  required_evidence: string[];
  acceptable_substitutes: string[];
  closure_guidance?: string;
  cp_recommended_text?: string;
  reviewer_confirmation_required: boolean;
};

const DEFAULT_REQUIRED_EVIDENCE = 'Supporting annexure confirmed by reviewer';
const DEFAULT_CLOSURE_GUIDANCE =
  'Reviewer confirmation required. Obtain supporting annexure, authority verification, or other documentary basis acceptable to the Bank before closure.';
const DEFAULT_CP_RECOMMENDED_TEXT =
  'Prior to approval / disbursement, the borrower shall provide supporting annexure and reviewer confirmation acceptable to the Bank for this issue.';

const RULE_ID_ALIASES: Record<string, string> = {
  LDA_001: 'LAYOUT_APPROVAL_MISSING',
  REG_001: 'MISSING_REGISTERED_SALE_DEED',
  TPA_CHAIN_GAP_001: 'TITLE_CHAIN_GAP',
  TPA_NOTICE_POSSESSION_001: 'POSSESSION_EVIDENCE_MISSING',
  TPA_CAPACITY_001: 'CAPACITY_OR_AUTHORITY_ISSUE',
  SOC_001: 'SOCIETY_NOC_MISSING',
  SOC_002: 'SOCIETY_TRANSFER_MEMBERSHIP_ISSUE',
  RUDA_001: 'AUTHORITY_APPROVAL_DEPENDENCY',
  CANT_001: 'CANTONMENT_NOC_MISSING',
};

const RULE_EVIDENCE_LIBRARY = rulesEvidenceLibrary as Record<string, RuleEvidenceDefinitionSource>;

export const RULE_EVIDENCE_MAP: Record<string, RuleEvidenceDefinitionSource> = RULE_EVIDENCE_LIBRARY;

function normalizeFallbackEvidence(fallbackEvidence?: string | string[] | null): string[] {
  if (Array.isArray(fallbackEvidence)) {
    return fallbackEvidence.map((value) => String(value).trim()).filter(Boolean);
  }

  if (typeof fallbackEvidence !== 'string' || !fallbackEvidence.trim()) {
    return [];
  }

  return fallbackEvidence
    .split(/[;,]/)
    .map((value) => value.trim())
    .filter(Boolean);
}

function resolveRuleId(ruleId?: string | null): string | undefined {
  if (!ruleId) {
    return undefined;
  }

  return RULE_ID_ALIASES[ruleId] ?? ruleId;
}

export function getRuleEvidenceDefinition(
  ruleId?: string | null,
  fallbackEvidence?: string | string[] | null
): RuleEvidenceDefinition {
  const resolvedRuleId = resolveRuleId(ruleId);
  const configured = resolvedRuleId ? RULE_EVIDENCE_LIBRARY[resolvedRuleId] : undefined;
  const fallbackRequired = normalizeFallbackEvidence(fallbackEvidence);
  const reviewerConfirmationRequired = !configured;

  return {
    required_evidence:
      configured?.required_evidence?.length
        ? configured.required_evidence
        : fallbackRequired.length
          ? fallbackRequired
          : [DEFAULT_REQUIRED_EVIDENCE],
    acceptable_substitutes: configured?.acceptable_substitutes ?? [],
    closure_guidance: configured?.closure_guidance ?? DEFAULT_CLOSURE_GUIDANCE,
    cp_recommended_text: configured?.cp_recommended_text ?? DEFAULT_CP_RECOMMENDED_TEXT,
    reviewer_confirmation_required: reviewerConfirmationRequired,
  };
}

export function hasEvidenceRequirement(
  ruleId?: string | null,
  fallbackEvidence?: string | string[] | null
): boolean {
  const definition = getRuleEvidenceDefinition(ruleId, fallbackEvidence);
  return definition.required_evidence.length > 0 || definition.acceptable_substitutes.length > 0;
}

export function isEvidenceSatisfied(evidenceRefs?: Array<unknown> | null): boolean {
  return Array.isArray(evidenceRefs) && evidenceRefs.length > 0;
}
