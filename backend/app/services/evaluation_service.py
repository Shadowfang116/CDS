"""Golden Case Evaluation service.

Matches actual exceptions/CPs against golden-standard expectations using:
  1. Exact rule_id match (preferred)
  2. Normalized Jaccard similarity on title + text (fallback, threshold 0.30)

Computes critical_recall, overall_recall, and precision, then persists
EvaluationRun + EvaluationFinding rows.
"""
import re
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationFinding, EvaluationRun, GoldenCaseExpectation
from app.models.rules import ConditionPrecedent, Exception_

SIMILARITY_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _tokenize(text: str | None) -> set[str]:
    """Lower-case, strip punctuation, return word tokens longer than 2 chars."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return {w for w in cleaned.split() if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _similarity(exp_title: str | None, exp_text: str | None,
                act_title: str | None, act_text: str | None) -> float:
    title_score = _jaccard(_tokenize(exp_title), _tokenize(act_title))
    text_score = _jaccard(_tokenize(exp_text), _tokenize(act_text)) if exp_text else 0.0
    # Weight title more heavily; fall back to text score
    return max(title_score, text_score * 0.8)


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

def run_evaluation(
    db: Session,
    org_id: uuid.UUID,
    case_id: uuid.UUID,
    created_by: uuid.UUID,
) -> EvaluationRun:
    """Run a golden case evaluation and persist all results.

    Returns the completed (or failed) EvaluationRun.
    """
    start_ts = time.monotonic()

    run = EvaluationRun(
        org_id=org_id,
        case_id=case_id,
        created_by=created_by,
        status="running",
    )
    db.add(run)
    db.flush()  # get run.id before commit

    try:
        expectations = (
            db.query(GoldenCaseExpectation)
            .filter(
                GoldenCaseExpectation.org_id == org_id,
                GoldenCaseExpectation.case_id == case_id,
            )
            .all()
        )

        actuals_exc = (
            db.query(Exception_)
            .filter(Exception_.org_id == org_id, Exception_.case_id == case_id)
            .all()
        )
        actuals_cp = (
            db.query(ConditionPrecedent)
            .filter(ConditionPrecedent.org_id == org_id, ConditionPrecedent.case_id == case_id)
            .all()
        )

        findings: list[EvaluationFinding] = []
        matched_exc_ids: set[uuid.UUID] = set()
        matched_cp_ids: set[uuid.UUID] = set()

        for exp in expectations:
            candidates = actuals_exc if exp.finding_type == "exception" else actuals_cp
            already_matched = matched_exc_ids if exp.finding_type == "exception" else matched_cp_ids

            best_actual = None
            best_score = 0.0
            exact_match = False

            for actual in candidates:
                if actual.id in already_matched:
                    continue

                # 1. Exact rule_id match
                if exp.expected_rule_id and actual.rule_id == exp.expected_rule_id:
                    best_actual = actual
                    best_score = 1.0
                    exact_match = True
                    break

                # 2. Similarity fallback
                if exp.finding_type == "exception":
                    act_title = actual.title
                    act_text = actual.description
                else:
                    act_title = actual.rule_id   # CP has no separate title field
                    act_text = actual.text

                score = _similarity(exp.expected_title, exp.expected_text, act_title, act_text)
                if score > best_score:
                    best_score = score
                    best_actual = actual

            if best_actual and (exact_match or best_score >= SIMILARITY_THRESHOLD):
                already_matched.add(best_actual.id)

                if exp.finding_type == "exception":
                    act_title = best_actual.title
                    act_text = best_actual.description
                    act_sev = best_actual.severity
                    act_rule = best_actual.rule_id
                else:
                    act_title = None
                    act_text = best_actual.text
                    act_sev = best_actual.severity
                    act_rule = best_actual.rule_id

                findings.append(EvaluationFinding(
                    evaluation_run_id=run.id,
                    expectation_id=exp.id,
                    finding_type=exp.finding_type,
                    expected_rule_id=exp.expected_rule_id,
                    actual_rule_id=act_rule,
                    expected_title=exp.expected_title,
                    actual_title=act_title,
                    expected_text=exp.expected_text,
                    actual_text=act_text,
                    expected_severity=exp.expected_severity,
                    actual_severity=act_sev,
                    match_status="matched",
                    similarity_score=None if exact_match else round(best_score, 4),
                ))
            else:
                findings.append(EvaluationFinding(
                    evaluation_run_id=run.id,
                    expectation_id=exp.id,
                    finding_type=exp.finding_type,
                    expected_rule_id=exp.expected_rule_id,
                    actual_rule_id=None,
                    expected_title=exp.expected_title,
                    actual_title=None,
                    expected_text=exp.expected_text,
                    actual_text=None,
                    expected_severity=exp.expected_severity,
                    actual_severity=None,
                    match_status="missed",
                    similarity_score=None,
                ))

        # Extra actuals (not matched to any expectation)
        for actual in actuals_exc:
            if actual.id not in matched_exc_ids:
                findings.append(EvaluationFinding(
                    evaluation_run_id=run.id,
                    expectation_id=None,
                    finding_type="exception",
                    expected_rule_id=None,
                    actual_rule_id=actual.rule_id,
                    expected_title=None,
                    actual_title=actual.title,
                    expected_text=None,
                    actual_text=actual.description,
                    expected_severity=None,
                    actual_severity=actual.severity,
                    match_status="extra",
                    similarity_score=None,
                ))

        for actual in actuals_cp:
            if actual.id not in matched_cp_ids:
                findings.append(EvaluationFinding(
                    evaluation_run_id=run.id,
                    expectation_id=None,
                    finding_type="cp",
                    expected_rule_id=None,
                    actual_rule_id=actual.rule_id,
                    expected_title=None,
                    actual_title=None,
                    expected_text=None,
                    actual_text=actual.text,
                    expected_severity=None,
                    actual_severity=actual.severity,
                    match_status="extra",
                    similarity_score=None,
                ))

        for f in findings:
            db.add(f)

        # Metrics
        total_expected = len(expectations)
        matched_count = sum(1 for f in findings if f.match_status == "matched")
        missed_count = sum(1 for f in findings if f.match_status == "missed")
        extra_count = sum(1 for f in findings if f.match_status == "extra")
        total_actual = len(actuals_exc) + len(actuals_cp)

        critical_ids = {e.id for e in expectations if e.is_critical}
        critical_total = len(critical_ids)
        critical_matched = sum(
            1 for f in findings
            if f.match_status == "matched" and f.expectation_id in critical_ids
        )

        run.completed_at = datetime.utcnow()
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.critical_recall = (critical_matched / critical_total) if critical_total else None
        run.overall_recall = (matched_count / total_expected) if total_expected else None
        run.precision = (matched_count / total_actual) if total_actual else None
        run.expected_count = total_expected
        run.matched_count = matched_count
        run.missed_count = missed_count
        run.extra_count = extra_count
        run.status = "completed"

        db.commit()
        db.refresh(run)
        return run

    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        raise
