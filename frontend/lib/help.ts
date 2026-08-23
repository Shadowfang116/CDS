export const HELP_OPEN_EVENT = "bdp:open-help";

export function openHelp() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(HELP_OPEN_EVENT));
}
