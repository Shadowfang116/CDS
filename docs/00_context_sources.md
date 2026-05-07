# Context sources (CDS)

**Covenant Diligence Systems (CDS)** agents and developers should resolve ambiguity in this order.

## 1. `docs/` (search here first when unclear)

This directory is the **primary architectural memory** shipped with the product.

| Document | Use |
|----------|-----|
| [01_architecture.md](01_architecture.md) | System shape, components, data flow |
| [02_security_baseline.md](02_security_baseline.md) | Security and compliance expectations |
| [04_rulepack_method.md](04_rulepack_method.md) | How rules are authored and evaluated |
| [05_rulepack_v1.yaml](05_rulepack_v1.yaml) | Rule definitions consumed by the engine |
| [06_evidence_library.yaml](06_evidence_library.yaml) | Evidence typing / library |
| [03_bank_it_pack.md](03_bank_it_pack.md) | Bank pack / IT pack expectations |
| `docs/ops/*`, pilot playbooks | Runbooks and operational checklists |

## 2. Graphify outputs (if present)

At the **workspace root** (parent of this inner `bank-diligence-platform/` folder):

- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`

Regenerate from the inner repo:

```bash
python scripts/dev/generate_graphify_out.py
```

**Do not** treat Obsidian’s `.obsidian/graph.json` as Graphify output.

## 3. Codebase (ground truth for runtime)

Confirm behavior in:

- `backend/app/` — FastAPI routes, services, models, workers
- `frontend/` — Next.js App Router UI and API client

## Optional Obsidian vault

If your team uses a separate vault, see [OBSIDIAN_VAULT.md](../../OBSIDIAN_VAULT.md) at the workspace root for the canonical optional path and symlink notes.
