"""Run deterministic AI eval cases against the local stack."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.ai.evals import EvalRunner


class Command(BaseCommand):
    """Execute deterministic AI eval scenarios and print a concise summary."""

    help = "Run deterministic AI evals for prompts, orchestration, and approval flows."

    def add_arguments(self, parser) -> None:  # type: ignore[override]
        """Allow filtering eval execution to a subset of case names."""
        parser.add_argument(
            "--case",
            action="append",
            dest="cases",
            default=[],
            help="Run only the named eval case. Can be provided multiple times.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Run eval cases and fail the command if any case regresses."""
        del args
        case_names = list(options.get("cases") or [])
        results = EvalRunner().run_all(case_names=case_names or None)
        if case_names and not results:
            raise CommandError("No AI eval cases matched the provided --case filters.")

        failed = [result for result in results if not result.passed]
        for result in results:
            status_label = "PASS" if result.passed else "FAIL"
            self.stdout.write(f"[{status_label}] {result.name}")
            if not result.passed:
                for failure in result.failures:
                    self.stdout.write(f"  - {failure}")

        summary = f"{len(results)} AI eval case(s) run, {len(failed)} failed."
        if failed:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
