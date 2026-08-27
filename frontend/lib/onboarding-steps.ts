export type OnboardingStep = {
  id: string;
  target: string;
  title: string;
  description: string;
  actionHint: string;
};

export const ONBOARDING_STORAGE_KEY = 'bdp_onboarding_done';

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: 'dashboard',
    target: '[data-tour="dashboard"]',
    title: 'Your review queue',
    description: 'The dashboard is your starting point. It shows which matters need you, which are blocked by missing evidence, and which are ready for a decision.',
    actionHint: 'Start with “Needs me” and follow the next action shown on each matter.',
  },
  {
    id: 'new-matter',
    target: '[data-tour="new-matter"]',
    title: 'Create a matter',
    description: 'Enter a borrower or file name, choose the property type, and attach the available title documents. The workspace opens automatically after creation.',
    actionHint: 'You can create the matter first and add more documents later.',
  },
  {
    id: 'case-list',
    target: '[data-tour="case-list"]',
    title: 'Open a matter',
    description: 'Each row is a separate matter. Open one to see its documents, extracted information, open risks, conditions, and current decision status in one workspace.',
    actionHint: 'Use the matter’s next action to know what to do first.',
  },
  {
    id: 'matter-workspace',
    target: '[data-tour="matter-workspace"]',
    title: 'Work through the evidence',
    description: 'The matter workspace keeps the file, source documents, extracted fields, risks, and decision actions together. Always verify important OCR values against the source document.',
    actionHint: 'Resolve or formally waive findings, complete conditions, then submit for approval.',
  },
];
