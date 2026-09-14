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
    description: 'The dashboard is your starting point. It shows which cases need you, which are blocked by missing evidence, and which are ready for a decision.',
    actionHint: 'Start with “Needs me” and follow the next action shown on each case.',
  },
  {
    id: 'new-matter',
    target: '[data-tour="new-matter"]',
    title: 'Create a case',
    description: 'Enter a borrower or file name, choose the property type, and attach the available title documents. The workspace opens automatically after creation.',
    actionHint: 'You can create the case first and add more documents later.',
  },
  {
    id: 'case-list',
    target: '[data-tour="case-list"]',
    title: 'Open a case',
    description: 'Each row is a separate case. Open one to see its documents, extracted information, open risks, approval needs, and current decision status in one workspace.',
    actionHint: 'Use the case’s next action to know what to do first.',
  },
  {
    id: 'matter-workspace',
    target: '[data-tour="matter-workspace"]',
    title: 'Work through the evidence',
    description: 'The case workspace keeps the file, source documents, extracted fields, risks, and decision actions together. Always review important scanned text against the source document.',
    actionHint: 'Resolve or formally waive findings, complete conditions, then submit for approval.',
  },
];
