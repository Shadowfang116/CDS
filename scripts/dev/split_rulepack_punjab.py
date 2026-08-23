"""One-shot splitter: active Punjab pack vs archived generic KYC rules."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "05_rulepack_v1.yaml"
ARCHIVE_IDS = {"KYC-02", "KYC-05", "KYC-07", "KYC-10"}


def rule_id(block: str) -> str | None:
    match = re.search(r'- id: "([^"]+)"', block)
    return match.group(1) if match else None


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    parts = re.split(r"(?=  - id: )", src)
    rules = parts[1:]
    keep = [block for block in rules if rule_id(block) not in ARCHIVE_IDS]
    archived = [block for block in rules if rule_id(block) in ARCHIVE_IDS]
    missing = ARCHIVE_IDS - {rule_id(block) for block in archived}
    if missing:
        raise SystemExit(f"missing archive rules: {missing}")

    out_dir = ROOT / "docs" / "rulepacks"
    (out_dir / "archive").mkdir(parents=True, exist_ok=True)
    active_header = (
        "# CDS active Punjab mortgage rulepack\n"
        "# Production RULEPACK_PATH points here. Archived KYC photo/salary/utility/co-applicant\n"
        "# rules live in docs/rulepacks/archive/generic_mvp_legacy.yaml.\n"
        "# Compatibility pack for tests: docs/05_rulepack_v1.yaml\n"
        "\n"
        'version: "1.0"\n'
        'description: "Punjab mortgage due diligence — active pack"\n'
        "\n"
        "rules:\n"
    )
    archive_header = (
        "# Archived generic MVP KYC rules (photo, salary/income, utility, co-applicant).\n"
        "# Not loaded by production RULEPACK_PATH. Kept for tests via docs/05_rulepack_v1.yaml.\n"
        "\n"
        'version: "1.0"\n'
        'description: "Archived generic MVP KYC rules"\n'
        "\n"
        "rules:\n"
    )
    (out_dir / "punjab_mortgage_v1.yaml").write_text(active_header + "".join(keep), encoding="utf-8")
    (out_dir / "archive" / "generic_mvp_legacy.yaml").write_text(
        archive_header + "".join(archived), encoding="utf-8"
    )
    gold = [rule_id(block) for block in keep if (rule_id(block) or "").startswith("GOLD-")]
    print(f"keep={len(keep)} archive={len(archived)} gold={gold}")


if __name__ == "__main__":
    main()
