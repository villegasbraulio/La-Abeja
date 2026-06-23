"""Seed a rich commerce history for exercising AI and analytics tools."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.ai.models import (
    ApprovalRequest,
    Conversation,
    ConversationFeedback,
    ConversationTurn,
    InternalNote,
    Lead,
    MemoryFact,
    StockReservation,
    SupportTask,
    WorkflowRun,
)
from apps.authentication.models import CustomUser
from apps.catalog.models import Review, Wine
from apps.orders.models import Cart, CartItem, Order, OrderItem, ShippingAddress
from apps.payments.models import Payment, PaymentWebhookLog
from apps.reservations.models import Booking, Experience, TimeSlot

SEED_NAMESPACE = "https://bodegalaabeja.com.ar/demo/"
CUSTOMERS = (
    ("ana.torres@example.com", "Ana", "Torres", "+5492604001001", ["Malbec"]),
    ("bruno.diaz@example.com", "Bruno", "Díaz", "+5492604001002", ["Bonarda"]),
    ("carla.mendez@example.com", "Carla", "Méndez", "+5492604001003", ["Chardonnay"]),
    ("diego.romero@example.com", "Diego", "Romero", "+5492604001004", ["Cabernet Sauvignon"]),
    ("elena.sosa@example.com", "Elena", "Sosa", "+5492604001005", ["Chenin Blanc"]),
    ("facundo.paz@example.com", "Facundo", "Paz", "+5492604001006", ["Malbec"]),
    ("gabriela.luna@example.com", "Gabriela", "Luna", "+5492604001007", ["Bonarda"]),
    ("hernan.ruiz@example.com", "Hernán", "Ruiz", "+5492604001008", ["Chardonnay"]),
    ("ines.ferreyra@example.com", "Inés", "Ferreyra", "+5492604001009", ["Cabernet Sauvignon"]),
    ("julian.castro@example.com", "Julián", "Castro", "+5492604001010", ["Chenin Blanc"]),
    ("karina.ortiz@example.com", "Karina", "Ortiz", "+5492604001011", ["Malbec", "Bonarda"]),
    ("lucas.molina@example.com", "Lucas", "Molina", "+5492604001012", ["Chardonnay"]),
)

ORDER_STATUSES = (
    Order.Status.DELIVERED,
    Order.Status.PAYMENT_FAILED,
    Order.Status.SHIPPED,
    Order.Status.CANCELLED,
    Order.Status.PREPARING,
    Order.Status.REFUNDED,
    Order.Status.DELIVERED,
    Order.Status.PENDING_PAYMENT,
    Order.Status.PAID,
    Order.Status.READY_TO_SHIP,
    Order.Status.DELIVERED,
    Order.Status.DELIVERED,
)

CHANNELS = ("web", "whatsapp", "email", "backoffice")


def _seed_uuid(key: str):
    return uuid5(NAMESPACE_URL, f"{SEED_NAMESPACE}{key}")


def _aware(day: date, hour: int = 12) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour=hour)))


class Command(BaseCommand):
    """Create deterministic scenarios for every data-driven AI tool."""

    help = "Seed historical sales and operational scenarios for AI tools."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        """Populate the full demo graph and print a concise inventory."""
        del args, options
        call_command("seed_demo_data", verbosity=0)
        call_command("seed_ai_knowledge", verbosity=0)

        admin = CustomUser.objects.filter(is_superuser=True).order_by("date_joined").first()
        if admin is None:
            raise RuntimeError("The demo administrator could not be created.")

        customers = self._seed_customers()
        wines = list(Wine.objects.order_by("sku"))
        orders = self._seed_orders(customers, wines)
        self._seed_carts_and_addresses(customers, wines)
        self._seed_reviews(customers, wines, orders)
        self._seed_visits(customers)
        conversations = self._seed_conversations(customers)
        self._seed_operations(admin, customers, wines, orders, conversations)

        self.stdout.write(
            self.style.SUCCESS(
                "AI demo ready: "
                f"{len(customers)} customers, {len(orders)} historical orders, "
                f"{Payment.objects.filter(mp_preference_id__startswith='seed-pref-').count()} "
                f"payments, {Conversation.objects.filter(session_key__startswith='seed-').count()} "
                f"conversations, {SupportTask.objects.filter(metadata__seeded=True).count()} "
                "operational tasks."
            )
        )

    def _seed_customers(self) -> list[CustomUser]:
        customers = []
        today = timezone.localdate()
        for index, (email, first_name, last_name, phone, varietals) in enumerate(CUSTOMERS):
            customer, created = CustomUser.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "birth_date": date(1982 + index, (index % 12) + 1, (index % 25) + 1),
                    "preferred_varietals": varietals,
                    "newsletter_subscribed": index % 4 != 0,
                    "is_active": True,
                },
            )
            if created:
                customer.set_unusable_password()
                customer.save(update_fields=["password"])
            CustomUser.objects.filter(pk=customer.pk).update(
                date_joined=_aware(today - timedelta(days=700 - index * 31), 9)
            )
            customer.refresh_from_db()
            customers.append(customer)
        return customers

    def _seed_orders(
        self,
        customers: list[CustomUser],
        wines: list[Wine],
    ) -> list[Order]:
        today = timezone.localdate()
        orders = []
        for index in range(96):
            customer = customers[index % len(customers)]
            status = ORDER_STATUSES[index % len(ORDER_STATUSES)]
            created_day = today - timedelta(days=index * 5)
            order_number = f"DEMO-{created_day.year}-{index + 1:05d}"
            selected_wines = [
                wines[(index + offset) % len(wines)] for offset in range(1 + index % 3)
            ]
            quantities = [1 + ((index + offset) % 4) for offset in range(len(selected_wines))]
            subtotal = sum(
                (
                    wine.price * quantity
                    for wine, quantity in zip(selected_wines, quantities, strict=True)
                ),
                Decimal("0.00"),
            )
            discount = (
                (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
                if index % 5 == 0
                else Decimal("0.00")
            )
            shipping_method = (
                Order.ShippingMethod.PICKUP if index % 6 == 0 else Order.ShippingMethod.STANDARD
            )
            shipping_cost = (
                Decimal("0.00")
                if shipping_method == Order.ShippingMethod.PICKUP
                else Decimal("3500.00")
            )
            total = subtotal - discount + shipping_cost
            channel = CHANNELS[index % len(CHANNELS)]
            tracking = f"AR-DEMO-{index + 1:06d}" if status in {
                Order.Status.READY_TO_SHIP,
                Order.Status.SHIPPED,
                Order.Status.DELIVERED,
            } else ""
            order, _ = Order.objects.update_or_create(
                order_number=order_number,
                defaults={
                    "user": customer,
                    "status": status,
                    "subtotal": subtotal,
                    "discount_amount": discount,
                    "shipping_cost": shipping_cost,
                    "total": total,
                    "shipping_method": shipping_method,
                    "shipping_address": {
                        "recipient_name": customer.full_name,
                        "street": "Avenida Mitre",
                        "number": str(1000 + index),
                        "city": "San Rafael" if index % 3 else "Mendoza",
                        "province": "Mendoza",
                        "postal_code": "5600",
                        "phone": customer.phone,
                        "source_channel": channel,
                    },
                    "promo_code_used": "ABEJA10" if discount else "",
                    "tracking_number": tracking,
                    "shipped_at": _aware(created_day + timedelta(days=2)) if tracking else None,
                    "delivered_at": _aware(created_day + timedelta(days=5))
                    if status == Order.Status.DELIVERED
                    else None,
                    "estimated_delivery": created_day + timedelta(days=6),
                    "notes": "Pedido histórico generado para pruebas de métricas e IA.",
                },
            )
            Order.objects.filter(pk=order.pk).update(
                created_at=_aware(created_day, 10 + index % 8),
                updated_at=_aware(created_day + timedelta(days=1), 10),
            )
            OrderItem.objects.filter(order=order).delete()
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        wine=wine,
                        wine_name=wine.name,
                        wine_sku=wine.sku,
                        quantity=quantity,
                        unit_price=wine.price,
                        subtotal=wine.price * quantity,
                    )
                    for wine, quantity in zip(selected_wines, quantities, strict=True)
                ]
            )
            payment_status = self._payment_status_for_order(status)
            payment, _ = Payment.objects.update_or_create(
                order=order,
                defaults={
                    "idempotency_key": f"mercadopago:preference:{order.id}",
                    "mp_preference_id": f"seed-pref-{index + 1:05d}",
                    "mp_payment_id": f"seed-pay-{index + 1:05d}",
                    "mp_merchant_order_id": f"seed-merchant-{index + 1:05d}",
                    "status": payment_status,
                    "status_detail": self._payment_detail(payment_status),
                    "payment_method": ("visa" if index % 2 == 0 else "master"),
                    "payment_type": "credit_card",
                    "installments": (1, 3, 6)[index % 3],
                    "amount": total,
                    "currency": "ARS",
                },
            )
            Payment.objects.filter(pk=payment.pk).update(
                created_at=_aware(created_day, 10),
                updated_at=_aware(created_day, 11),
            )
            webhook, _ = PaymentWebhookLog.objects.update_or_create(
                deduplication_key=f"seed-webhook-{index + 1:05d}",
                mp_notification_id=f"seed-notification-{index + 1:05d}",
                topic="payment",
                defaults={
                    "payload": {"payment_id": payment.mp_payment_id, "status": payment_status},
                    "processed": index % 9 != 0,
                    "error": "Firma inválida simulada" if index % 9 == 0 else "",
                },
            )
            PaymentWebhookLog.objects.filter(pk=webhook.pk).update(
                received_at=_aware(created_day, 11)
            )
            order.refresh_from_db()
            orders.append(order)
        return orders

    def _seed_carts_and_addresses(
        self,
        customers: list[CustomUser],
        wines: list[Wine],
    ) -> None:
        now = timezone.now()
        for index, customer in enumerate(customers):
            ShippingAddress.objects.update_or_create(
                user=customer,
                label="Casa",
                defaults={
                    "recipient_name": customer.full_name,
                    "street": "Avenida Mitre",
                    "number": str(2100 + index),
                    "floor_apt": "",
                    "city": "San Rafael",
                    "province": "Mendoza",
                    "postal_code": "5600",
                    "phone": customer.phone,
                    "is_default": True,
                },
            )
            cart, _ = Cart.objects.update_or_create(
                user=customer,
                defaults={
                    "session_key": f"seed-cart-{index + 1:02d}",
                    "last_activity_at": now - timedelta(hours=index * 5),
                    "abandon_reminder_sent": index % 3 == 0,
                },
            )
            CartItem.objects.filter(cart=cart).delete()
            if index < 9:
                wine = wines[index % len(wines)]
                CartItem.objects.create(
                    cart=cart,
                    wine=wine,
                    quantity=1 + index % 3,
                    unit_price=wine.price,
                )

    def _seed_reviews(
        self,
        customers: list[CustomUser],
        wines: list[Wine],
        orders: list[Order],
    ) -> None:
        review_orders = [order for order in orders if order.status == Order.Status.DELIVERED][:24]
        for index, order in enumerate(review_orders):
            wine = wines[index % len(wines)]
            Review.objects.update_or_create(
                wine=wine,
                user=order.user,
                order=order,
                defaults={
                    "rating": 3 + index % 3,
                    "title": ("Excelente experiencia" if index % 2 == 0 else "Muy buen vino"),
                    "body": "Compra verificada de prueba con notas de servicio y producto.",
                    "is_verified_purchase": True,
                    "is_approved": index % 7 != 0,
                    "helpful_votes": index % 8,
                },
            )

    def _seed_visits(self, customers: list[CustomUser]) -> None:
        experiences = list(Experience.objects.order_by("slug"))
        today = timezone.localdate()
        booking_statuses = (
            Booking.Status.CONFIRMED,
            Booking.Status.COMPLETED,
            Booking.Status.CANCELLED,
            Booking.Status.NO_SHOW,
        )
        for index in range(20):
            experience = experiences[index % len(experiences)]
            status = booking_statuses[index % len(booking_statuses)]
            if status in {Booking.Status.COMPLETED, Booking.Status.NO_SHOW}:
                slot_day = today - timedelta(days=(index % 10) + 1)
            else:
                slot_day = today + timedelta(days=(index % 10) + 1)
            start_time = time(9 + index % 8, 0)
            end_at = datetime.combine(slot_day, start_time) + timedelta(
                minutes=experience.duration_minutes
            )
            slot, _ = TimeSlot.objects.update_or_create(
                experience=experience,
                date=slot_day,
                start_time=start_time,
                defaults={
                    "end_time": end_at.time(),
                    "capacity": experience.max_guests,
                    "spots_available": max(0, experience.max_guests - (index % 6)),
                    "guide_name": ("Lucía", "Martín", "Sofía")[index % 3],
                    "is_blocked": index == 19,
                    "block_reason": "Mantenimiento programado" if index == 19 else "",
                },
            )
            Booking.objects.update_or_create(
                confirmation_code=f"VIS{index + 1:07d}",
                defaults={
                    "user": customers[index % len(customers)],
                    "time_slot": slot,
                    "guest_count": 1 + index % 5,
                    "total_price": experience.price_per_person * (1 + index % 5),
                    "status": status,
                    "special_requests": "Mesa accesible" if index % 6 == 0 else "",
                    "dietary_restrictions": ["Sin TACC"] if index % 5 == 0 else [],
                    "checked_in_at": timezone.now() - timedelta(days=2)
                    if status == Booking.Status.COMPLETED
                    else None,
                },
            )

    def _seed_conversations(self, customers: list[CustomUser]) -> list[Conversation]:
        conversations = []
        intents = ("order_status", "payment_issue", "wine_recommendation", "booking", "shipping")
        channels = list(Conversation.Channel.values)
        statuses = list(Conversation.Status.values)
        for index, customer in enumerate(customers):
            conversation, _ = Conversation.objects.update_or_create(
                id=_seed_uuid(f"conversation-{index}"),
                defaults={
                    "channel": channels[index % len(channels)],
                    "mode": Conversation.Mode.SUPPORT if index % 3 else Conversation.Mode.OPS,
                    "customer": customer,
                    "session_key": f"seed-conversation-{index + 1:02d}",
                    "status": statuses[index % len(statuses)],
                    "last_intent": intents[index % len(intents)],
                    "summary": f"Consulta demo sobre {intents[index % len(intents)]}.",
                    "metadata": {"seeded": True, "source": "seed_ai_demo_data"},
                },
            )
            first_turn, _ = ConversationTurn.objects.update_or_create(
                id=_seed_uuid(f"conversation-{index}-user-turn"),
                defaults={
                    "conversation": conversation,
                    "role": ConversationTurn.Role.USER,
                    "content": "Necesito ayuda con mi pedido y quiero conocer el estado del envío.",
                    "metadata": {"seeded": True},
                },
            )
            assistant_turn, _ = ConversationTurn.objects.update_or_create(
                id=_seed_uuid(f"conversation-{index}-assistant-turn"),
                defaults={
                    "conversation": conversation,
                    "role": ConversationTurn.Role.ASSISTANT,
                    "content": "Revisé el pedido y preparé un resumen para seguimiento.",
                    "metadata": {"seeded": True},
                },
            )
            ConversationFeedback.objects.update_or_create(
                id=_seed_uuid(f"conversation-{index}-feedback"),
                defaults={
                    "conversation": conversation,
                    "turn": assistant_turn,
                    "value": ConversationFeedback.Value.NEGATIVE
                    if index % 5 == 0
                    else ConversationFeedback.Value.POSITIVE,
                    "note": "Feedback generado para pruebas.",
                },
            )
            MemoryFact.objects.update_or_create(
                conversation=conversation,
                fact_type="preference",
                key="preferred_varietal",
                defaults={
                    "value": {"items": customer.preferred_varietals},
                    "confidence": Decimal("0.920"),
                },
            )
            conversations.append(conversation)
            del first_turn
        return conversations

    def _seed_operations(
        self,
        admin: CustomUser,
        customers: list[CustomUser],
        wines: list[Wine],
        orders: list[Order],
        conversations: list[Conversation],
    ) -> None:
        task_types = list(SupportTask.TaskType.values)
        task_statuses = list(SupportTask.Status.values)
        priorities = list(SupportTask.Priority.values)
        note_types = list(InternalNote.NoteType.values)
        reservation_statuses = list(StockReservation.Status.values)
        today = timezone.localdate()

        for index in range(18):
            order = orders[index]
            customer = order.user
            SupportTask.objects.update_or_create(
                id=_seed_uuid(f"support-task-{index}"),
                defaults={
                    "task_type": task_types[index % len(task_types)],
                    "title": f"Caso demo {index + 1}: seguimiento de {order.order_number}",
                    "description": "Escenario operativo para probar tools, filtros e incidencias.",
                    "status": task_statuses[index % len(task_statuses)],
                    "priority": priorities[index % len(priorities)],
                    "order": order,
                    "conversation": conversations[index % len(conversations)],
                    "customer": customer,
                    "assigned_to": admin if index % 3 else None,
                    "created_by": admin,
                    "due_at": timezone.now() + timedelta(days=(index % 7) - 2),
                    "metadata": {"seeded": True, "seed_key": f"support-task-{index}"},
                },
            )
            InternalNote.objects.update_or_create(
                id=_seed_uuid(f"internal-note-{index}"),
                defaults={
                    "note_type": note_types[index % len(note_types)],
                    "content": (
                        f"Nota interna demo para {order.order_number}: cliente contactado, "
                        "validar pago, despacho y satisfacción."
                    ),
                    "order": order,
                    "conversation": conversations[index % len(conversations)],
                    "customer": customer,
                    "created_by": admin,
                    "metadata": {"seeded": True, "seed_key": f"internal-note-{index}"},
                },
            )

        Lead.objects.filter(metadata__seeded=True).delete()

        for index in range(8):
            StockReservation.objects.update_or_create(
                id=_seed_uuid(f"stock-reservation-{index}"),
                defaults={
                    "wine": wines[index % len(wines)],
                    "quantity": 2 + index,
                    "order": orders[index],
                    "conversation": conversations[index % len(conversations)],
                    "customer": customers[index % len(customers)],
                    "created_by": admin,
                    "status": reservation_statuses[index % len(reservation_statuses)],
                    "reason": "Reserva demo para pedido corporativo.",
                    "released_quantity": index if index % 3 else 0,
                    "released_at": timezone.now() - timedelta(days=1) if index % 3 else None,
                    "metadata": {"seeded": True, "seed_key": f"stock-reservation-{index}"},
                },
            )

        for index in range(6):
            workflow, _ = WorkflowRun.objects.update_or_create(
                idempotency_key=f"seed-workflow-{index}",
                defaults={
                    "workflow_type": ("order_status_change", "stock_reservation", "refund")[
                        index % 3
                    ],
                    "status": list(WorkflowRun.Status.values)[
                        index % len(WorkflowRun.Status.values)
                    ],
                    "actor_type": "agent",
                    "input_payload": {"order_number": orders[index].order_number},
                    "result_payload": {"seeded": True},
                },
            )
            ApprovalRequest.objects.update_or_create(
                id=_seed_uuid(f"approval-{index}"),
                defaults={
                    "workflow_run": workflow,
                    "action_name": ("update_order_status", "reserve_stock", "refund_order")[
                        index % 3
                    ],
                    "action_payload": {"order_number": orders[index].order_number},
                    "status": list(ApprovalRequest.Status.values)[
                        index % len(ApprovalRequest.Status.values)
                    ],
                    "approved_by": admin if index % 3 else None,
                    "decision_note": "Decisión demo para validar human-in-the-loop.",
                    "decided_at": timezone.now() if index % 3 else None,
                },
            )

        low_stock_levels = (4, 0, 9)
        for wine, stock in zip(wines[:3], low_stock_levels, strict=True):
            Wine.objects.filter(pk=wine.pk).update(stock=stock, low_stock_threshold=10)

        for index in range(18):
            SupportTask.objects.filter(pk=_seed_uuid(f"support-task-{index}")).update(
                created_at=_aware(today - timedelta(days=index * 3), 9)
            )

    @staticmethod
    def _payment_status_for_order(status: str) -> str:
        if status == Order.Status.PAYMENT_FAILED:
            return Payment.Status.REJECTED
        if status == Order.Status.CANCELLED:
            return Payment.Status.CANCELLED
        if status == Order.Status.REFUNDED:
            return Payment.Status.REFUNDED
        if status == Order.Status.PENDING_PAYMENT:
            return Payment.Status.PENDING
        return Payment.Status.APPROVED

    @staticmethod
    def _payment_detail(status: str) -> str:
        return {
            Payment.Status.APPROVED: "accredited",
            Payment.Status.REJECTED: "cc_rejected_insufficient_amount",
            Payment.Status.CANCELLED: "cancelled_by_user",
            Payment.Status.REFUNDED: "refunded",
            Payment.Status.PENDING: "pending_waiting_payment",
        }.get(status, "")
