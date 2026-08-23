# CDS workbench design

Inbox and Matter are operational surfaces. Login keeps the atmospheric treatment and Source Serif 4 Display. The workbench does not.

## Worlds

- **Login:** cinematic, Source Serif, atmosphere only here.
- **Inbox:** quiet queue. Needs me / Blocked / Waiting / Ready / Aging.
- **Matter:** File | Evidence | Work. Status and decision are separate facts. Next action is computed.

## Type

Switzer for operational UI. Array only for instrument metadata (`cds-meta`, matter ids, timestamps).

## Jobs

File (do we have it), Confirm (is it proven), Clear (what blocks), Decide (can the Bank proceed). Exception and CP stay distinct objects; the Findings list is one UX over two APIs.

## Constraints

OCR values are Proposed until Confirm. Waive is data-driven (`waivable` and not hard-stop). Submit for Approval is a human action. Maker/checker is enforced in the API, including Admin. Draft pack is labelled not approved. Issued pack is versioned. FAIL pack is not a clearance.
