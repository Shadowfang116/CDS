export const HELP_OPEN_EVENT = "bdp:open-help";
export const ONBOARDING_OPEN_EVENT = "bdp:start-onboarding-tour";

export function openHelp() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(HELP_OPEN_EVENT));
}

export function startOnboarding() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(ONBOARDING_OPEN_EVENT));
}
