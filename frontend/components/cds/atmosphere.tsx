"use client";

export function Atmosphere({
  enabled,
  behind = false,
}: {
  enabled: boolean;
  behind?: boolean;
}) {
  if (!enabled) {
    return null;
  }

  return (
    <>
      <div className={behind ? "cds-grain cds-grain--behind" : "cds-grain"} aria-hidden />
      <div className={behind ? "cds-vignette cds-vignette--behind" : "cds-vignette"} aria-hidden />
    </>
  );
}
