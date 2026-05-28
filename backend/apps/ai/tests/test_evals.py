"""Deterministic eval coverage for the AI app."""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.ai.evals import EvalRunner


@pytest.mark.django_db
def test_eval_runner_default_matrix_passes() -> None:
    """The current deterministic eval suite should pass end to end."""
    results = EvalRunner().run_all()

    assert results
    assert all(result.passed for result in results), results


@pytest.mark.django_db
def test_run_ai_evals_command_succeeds_and_prints_summary() -> None:
    """The management command should execute the eval suite and report a clean summary."""
    stdout = io.StringIO()

    call_command("run_ai_evals", stdout=stdout)

    output = stdout.getvalue()
    assert "[PASS]" in output
    assert "AI eval case(s) run, 0 failed." in output


@pytest.mark.django_db
def test_run_ai_evals_command_rejects_unknown_case_names() -> None:
    """Filtering to a missing case should fail loudly for CI visibility."""
    with pytest.raises(CommandError):
        call_command("run_ai_evals", case=["missing-case"])
