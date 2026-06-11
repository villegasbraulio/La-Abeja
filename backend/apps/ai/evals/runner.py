"""Deterministic AI eval runner for prompt and orchestration regressions."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test.utils import override_settings

from apps.ai.agents.orchestrator import AIOrchestrator
from apps.ai.models import Conversation, KnowledgeDocument, KnowledgeSource
from apps.ai.rag.ingest import KnowledgeIngestionService
from apps.authentication.models import CustomUser
from apps.catalog.models import Category, Varietal, Wine
from apps.orders.models import Order, OrderItem

user_model = get_user_model()


@dataclass(slots=True)
class EvalEnvironment:
    """Mutable environment passed to per-case setup functions."""

    user: CustomUser
    conversation: Conversation


@dataclass(slots=True)
class EvalCase:
    """Single deterministic eval scenario."""

    name: str
    description: str
    mode: str
    is_staff: bool
    message: str
    setup: Callable[[EvalEnvironment], None]
    expected_intent: str
    expected_substrings: list[str] = field(default_factory=list)
    expected_tool_statuses: list[tuple[str, str]] = field(default_factory=list)
    min_citations: int = 0
    expect_needs_human: bool = False


@dataclass(slots=True)
class EvalOutcome:
    """Result of a single eval case."""

    name: str
    passed: bool
    failures: list[str]
    actual_intent: str
    assistant_text: str
    tool_statuses: list[tuple[str, str]]
    citation_count: int
    needs_human: bool


class EvalRunner:
    """Run deterministic eval cases against the local AI stack."""

    def run_all(self, case_names: list[str] | None = None) -> list[EvalOutcome]:
        """Run all evals or a filtered subset."""
        cases = self.default_cases()
        if case_names:
            allowed = set(case_names)
            cases = [case for case in cases if case.name in allowed]
        return [self.run_case(case) for case in cases]

    def run_case(self, case: EvalCase) -> EvalOutcome:
        """Run a single eval case inside a rolled-back transaction."""
        with transaction.atomic(), override_settings(AI_USE_LLM=False, AI_USE_TOOL_CALLING=False):
            user = self._create_user(is_staff=case.is_staff, label=case.name)
            conversation = Conversation.objects.create(
                channel=Conversation.Channel.BACKOFFICE
                if case.is_staff
                else Conversation.Channel.WEB,
                mode=case.mode,
                customer=user,
            )
            environment = EvalEnvironment(user=user, conversation=conversation)
            case.setup(environment)

            result = AIOrchestrator().handle_message(
                conversation=conversation,
                message=case.message,
                user_id=user.id,
                is_staff=case.is_staff,
            )
            tool_statuses = [
                (execution.tool_name, execution.status)
                for execution in result.run.tool_executions.order_by("created_at")
            ]
            failures = self._evaluate(case=case, result=result, tool_statuses=tool_statuses)
            outcome = EvalOutcome(
                name=case.name,
                passed=not failures,
                failures=failures,
                actual_intent=result.run.intent,
                assistant_text=result.assistant_turn.content,
                tool_statuses=tool_statuses,
                citation_count=len(result.assistant_turn.citations),
                needs_human=result.run.needs_human,
            )
            transaction.set_rollback(True)
            return outcome

    def default_cases(self) -> list[EvalCase]:
        """Return the current deterministic eval matrix."""
        return [
            EvalCase(
                name="support_pickup_policy_grounding",
                description="Support agent answers pickup policy from public knowledge with citations.",
                mode=Conversation.Mode.SUPPORT,
                is_staff=False,
                message="Puedo retirar la compra en la bodega?",
                setup=self._setup_public_pickup_policy,
                expected_intent="knowledge_search",
                expected_substrings=["retiro en bodega"],
                min_citations=1,
            ),
            EvalCase(
                name="support_order_status_lookup",
                description="Customer support retrieves a real order status without hallucinating.",
                mode=Conversation.Mode.SUPPORT,
                is_staff=False,
                message="Quiero saber el estado de mi pedido LAB-2026-000145",
                setup=self._setup_customer_order,
                expected_intent="order_status",
                expected_substrings=["LAB-2026-000145", "preparando"],
                expected_tool_statuses=[("get_order_by_number", "succeeded")],
            ),
            EvalCase(
                name="ops_low_stock_snapshot",
                description="Operations copilot can list low-stock products from live catalog data.",
                mode=Conversation.Mode.OPS,
                is_staff=True,
                message="Mostrame el stock bajo",
                setup=self._setup_low_stock_catalog,
                expected_intent="low_stock",
                expected_substrings=["stock bajo", "Malbec"],
                expected_tool_statuses=[("list_low_stock_items", "succeeded")],
            ),
            EvalCase(
                name="ops_sales_by_varietal",
                description="Operations copilot computes sales by varietal over seeded revenue data.",
                mode=Conversation.Mode.OPS,
                is_staff=True,
                message="Mostrame ventas por varietal este mes",
                setup=self._setup_sales_data,
                expected_intent="sales_by_varietal",
                expected_substrings=["Ventas por varietal", "Malbec"],
                expected_tool_statuses=[("get_sales_by_varietal", "succeeded")],
            ),
            EvalCase(
                name="ops_task_creation",
                description="Explicit operator requests create a real support task without approval.",
                mode=Conversation.Mode.OPS,
                is_staff=True,
                message="Crea una tarea urgente para seguir el pedido LAB-2026-000701 por pago rechazado",
                setup=self._setup_ops_follow_up_order,
                expected_intent="create_support_task",
                expected_substrings=["Cree la tarea"],
                expected_tool_statuses=[("create_support_task", "succeeded")],
            ),
            EvalCase(
                name="ops_status_change_requires_approval",
                description="Risky order state changes are prepared but blocked pending approval.",
                mode=Conversation.Mode.OPS,
                is_staff=True,
                message="Marca el pedido LAB-2026-000702 como enviado con tracking AND-12345",
                setup=self._setup_ops_shipping_order,
                expected_intent="update_order_status",
                expected_substrings=["requiere aprobacion humana"],
                expected_tool_statuses=[("update_order_status", "blocked")],
                expect_needs_human=True,
            ),
        ]

    def _evaluate(
        self,
        *,
        case: EvalCase,
        result,
        tool_statuses: list[tuple[str, str]],
    ) -> list[str]:
        """Compare actual outputs against case expectations."""
        failures: list[str] = []
        if result.run.intent != case.expected_intent:
            failures.append(f"intent esperado={case.expected_intent} actual={result.run.intent}")

        assistant_text_lower = result.assistant_turn.content.lower()
        for expected in case.expected_substrings:
            if expected.lower() not in assistant_text_lower:
                failures.append(f"falta substring esperado: {expected}")

        if len(result.assistant_turn.citations) < case.min_citations:
            failures.append(
                f"citas esperadas>={case.min_citations} actual={len(result.assistant_turn.citations)}"
            )

        for expected_tool_status in case.expected_tool_statuses:
            if expected_tool_status not in tool_statuses:
                failures.append(f"tool status faltante: {expected_tool_status}")

        if result.run.needs_human != case.expect_needs_human:
            failures.append(
                f"needs_human esperado={case.expect_needs_human} actual={result.run.needs_human}"
            )
        return failures

    def _create_user(self, *, is_staff: bool, label: str) -> CustomUser:
        """Create an isolated user for one eval case."""
        suffix = uuid4().hex[:8]
        email = f"eval-{label}-{suffix}@example.com".replace("_", "-")
        return user_model.objects.create_user(
            email=email,
            password="StrongPass123!",
            first_name="Eval",
            last_name="Runner",
            phone="+5492604000000",
            is_staff=is_staff,
        )

    def _setup_public_pickup_policy(self, environment: EvalEnvironment) -> None:
        """Seed one public knowledge document about pickup policy."""
        self._upsert_knowledge(
            title="Retiro en bodega",
            external_id="pickup-policy",
            content=(
                "El retiro en bodega se coordina luego de la confirmacion. "
                "El equipo confirma horario y disponibilidad por mensaje."
            ),
            channel=KnowledgeDocument.Channel.PUBLIC,
        )
        del environment

    def _setup_customer_order(self, environment: EvalEnvironment) -> None:
        """Seed one customer-owned order for deterministic support lookups."""
        Order.objects.create(
            order_number="LAB-2026-000145",
            user=environment.user,
            status=Order.Status.PREPARING,
            subtotal=Decimal("12400.00"),
            discount_amount=Decimal("0.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("12400.00"),
            shipping_method=Order.ShippingMethod.STANDARD,
            shipping_address=self._shipping_address(),
        )

    def _setup_low_stock_catalog(self, environment: EvalEnvironment) -> None:
        """Seed a low-stock wine."""
        category = Category.objects.create(name="Tintos Eval", slug=f"tintos-{uuid4().hex[:6]}")
        varietal = Varietal.objects.create(name="Malbec", slug=f"malbec-{uuid4().hex[:6]}")
        Wine.objects.create(
            name="Malbec Eval Reserva",
            slug=f"malbec-eval-{uuid4().hex[:6]}",
            category=category,
            varietal=varietal,
            vintage_year=2024,
            price=Decimal("12000.00"),
            cost_price=Decimal("7000.00"),
            stock=3,
            low_stock_threshold=5,
            sku=f"EVAL-MAL-{uuid4().hex[:6].upper()}",
            alcohol_percentage=Decimal("14.0"),
            serving_temperature_min=14,
            serving_temperature_max=16,
            ageing_months=8,
            ageing_type=Wine.AgeingType.OAK,
            description="Malbec de evaluacion.",
            tasting_notes="Fruta roja y especias.",
        )
        del environment

    def _setup_sales_data(self, environment: EvalEnvironment) -> None:
        """Seed enough paid orders to produce a varietal ranking."""
        category = Category.objects.create(name="Ventas Eval", slug=f"ventas-{uuid4().hex[:6]}")
        malbec = Varietal.objects.create(name="Malbec", slug=f"malbec-sales-{uuid4().hex[:6]}")
        cabernet = Varietal.objects.create(
            name="Cabernet", slug=f"cabernet-sales-{uuid4().hex[:6]}"
        )
        wine_malbec = self._create_wine(
            category=category,
            varietal=malbec,
            name="Malbec Ventas Eval",
            sku_prefix="EVAL-MAL-SALES",
        )
        wine_cabernet = self._create_wine(
            category=category,
            varietal=cabernet,
            name="Cabernet Ventas Eval",
            sku_prefix="EVAL-CAB-SALES",
        )
        buyer = self._create_user(is_staff=False, label="sales-buyer")
        order_one = Order.objects.create(
            order_number=f"LAB-EVAL-{uuid4().hex[:6].upper()}",
            user=buyer,
            status=Order.Status.PAID,
            subtotal=Decimal("13500.00"),
            discount_amount=Decimal("0.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("13500.00"),
            shipping_method=Order.ShippingMethod.STANDARD,
            shipping_address=self._shipping_address(),
        )
        OrderItem.objects.create(
            order=order_one,
            wine=wine_malbec,
            wine_name=wine_malbec.name,
            wine_sku=wine_malbec.sku,
            quantity=2,
            unit_price=Decimal("4500.00"),
            subtotal=Decimal("9000.00"),
        )
        OrderItem.objects.create(
            order=order_one,
            wine=wine_cabernet,
            wine_name=wine_cabernet.name,
            wine_sku=wine_cabernet.sku,
            quantity=1,
            unit_price=Decimal("4500.00"),
            subtotal=Decimal("4500.00"),
        )

        order_two = Order.objects.create(
            order_number=f"LAB-EVAL-{uuid4().hex[:6].upper()}",
            user=buyer,
            status=Order.Status.SHIPPED,
            subtotal=Decimal("4500.00"),
            discount_amount=Decimal("0.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("4500.00"),
            shipping_method=Order.ShippingMethod.STANDARD,
            shipping_address=self._shipping_address(),
        )
        OrderItem.objects.create(
            order=order_two,
            wine=wine_malbec,
            wine_name=wine_malbec.name,
            wine_sku=wine_malbec.sku,
            quantity=1,
            unit_price=Decimal("4500.00"),
            subtotal=Decimal("4500.00"),
        )
        del environment

    def _setup_ops_follow_up_order(self, environment: EvalEnvironment) -> None:
        """Seed an order the ops copilot can use for task creation."""
        buyer = self._create_user(is_staff=False, label="follow-up-buyer")
        Order.objects.create(
            order_number="LAB-2026-000701",
            user=buyer,
            status=Order.Status.PAYMENT_FAILED,
            subtotal=Decimal("9900.00"),
            discount_amount=Decimal("0.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("9900.00"),
            shipping_method=Order.ShippingMethod.STANDARD,
            shipping_address=self._shipping_address(),
        )
        del environment

    def _setup_ops_shipping_order(self, environment: EvalEnvironment) -> None:
        """Seed an order the ops copilot will try to move to shipped."""
        buyer = self._create_user(is_staff=False, label="shipping-buyer")
        Order.objects.create(
            order_number="LAB-2026-000702",
            user=buyer,
            status=Order.Status.READY_TO_SHIP,
            subtotal=Decimal("15200.00"),
            discount_amount=Decimal("0.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("15200.00"),
            shipping_method=Order.ShippingMethod.STANDARD,
            shipping_address=self._shipping_address(),
        )
        del environment

    def _upsert_knowledge(
        self,
        *,
        title: str,
        external_id: str,
        content: str,
        channel: str,
    ) -> None:
        """Persist a synthetic knowledge document for one eval."""
        source = KnowledgeSource.objects.create(
            name=f"AI Eval {title} {uuid4().hex[:6]}",
            source_type=KnowledgeSource.SourceType.MANUAL,
            uri=f"eval://{external_id}-{uuid4().hex[:6]}",
        )
        KnowledgeIngestionService().upsert_document(
            source=source,
            external_id=external_id,
            title=title,
            content=content,
            channel=channel,
        )

    def _create_wine(
        self,
        *,
        category: Category,
        varietal: Varietal,
        name: str,
        sku_prefix: str,
    ) -> Wine:
        """Create one active wine for eval seeding."""
        suffix = uuid4().hex[:6]
        return Wine.objects.create(
            name=name,
            slug=f"{sku_prefix.lower()}-{suffix}",
            category=category,
            varietal=varietal,
            vintage_year=2024,
            price=Decimal("4500.00"),
            cost_price=Decimal("2500.00"),
            stock=20,
            low_stock_threshold=5,
            sku=f"{sku_prefix}-{suffix.upper()}",
            alcohol_percentage=Decimal("13.8"),
            serving_temperature_min=14,
            serving_temperature_max=16,
            ageing_months=6,
            ageing_type=Wine.AgeingType.OAK,
            description=f"{name} creado para evals.",
            tasting_notes="Fruta negra y especias.",
        )

    def _shipping_address(self) -> dict[str, str]:
        """Return a reusable shipping address payload."""
        return {
            "recipient_name": "Maria Perez",
            "street": "Av. San Martin",
            "number": "1234",
            "floor_apt": "",
            "city": "San Rafael",
            "province": "Mendoza",
            "postal_code": "5600",
            "country": "Argentina",
            "phone": "+5492604000000",
        }
