from app.schemas.case import CaseCreate
from app.api.deps import CurrentUser
from app.api.routes.workbench import workbench_evaluate
from app.services.rule_engine import RuleEnginePreconditionError
from fastapi import HTTPException, Request
import asyncio
from uuid import uuid4


def test_case_intake_accepts_property_context_needed_for_rule_analysis():
    intake = CaseCreate(
        title="Synthetic sale deed",
        property_type="Society plot",
        property_regime="SOCIETY",
    )

    assert intake.property_type == "Society plot"
    assert intake.property_regime == "SOCIETY"


def test_analysis_precondition_is_actionable_when_regime_is_missing(monkeypatch):
    def raise_missing_regime(*args, **kwargs):
        raise RuleEnginePreconditionError("property.regime is required to evaluate regime-conditional rules.")

    monkeypatch.setattr("app.api.routes.workbench.evaluate_matter", raise_missing_regime)
    request = Request({"type": "http", "method": "POST", "path": "/cases/workbench/evaluate"})

    async def run():
        try:
            await workbench_evaluate(
                request,
                uuid4(),
                CurrentUser(uuid4(), uuid4(), "Reviewer"),
                object(),
            )
        except HTTPException as error:
            return error
        raise AssertionError("expected an actionable HTTP error")

    error = asyncio.run(run())

    assert error.status_code == 422
    assert error.detail == "property.regime is required to evaluate regime-conditional rules."
