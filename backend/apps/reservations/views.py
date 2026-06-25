"""Public API views for visit booking flows."""

from __future__ import annotations

import structlog
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.mercadopago import MercadoPagoAPIError, MercadoPagoClient
from apps.payments.models import PaymentWebhookLog
from apps.payments.webhook_utils import build_webhook_deduplication_key, has_valid_signature

from .access import resolve_guest_booking
from .models import Booking, BookingPayment, Experience, TimeSlot
from .serializers import (
    PublicBookingCreateSerializer,
    PublicBookingSerializer,
    PublicExperienceSerializer,
    PublicTimeSlotSerializer,
)
from .services import (
    ReservationIntegrityError,
    cancel_booking,
    expire_pending_booking_holds,
    sync_booking_payment,
)

logger = structlog.get_logger(__name__)


class ExperienceListView(generics.ListAPIView):
    """List active public experiences."""

    permission_classes = [permissions.AllowAny]
    serializer_class = PublicExperienceSerializer
    pagination_class = None

    def get_queryset(self):
        """Return only active public experiences ordered by prominence."""
        expire_pending_booking_holds()
        return (
            Experience.objects.filter(is_active=True)
            .exclude(experience_type=Experience.ExperienceType.PRIVATE_EVENT)
            .order_by("-is_featured", "name")
        )


class TimeSlotListView(generics.ListAPIView):
    """List future public slots for an experience."""

    permission_classes = [permissions.AllowAny]
    serializer_class = PublicTimeSlotSerializer
    pagination_class = None

    def get_queryset(self):
        """Filter future slots by experience and guest count."""
        expire_pending_booking_holds()
        queryset = TimeSlot.objects.select_related("experience").filter(
            experience__is_active=True,
            experience__experience_type__in=[
                Experience.ExperienceType.WINERY_TOUR,
                Experience.ExperienceType.PREMIUM_TASTING,
                Experience.ExperienceType.HARVEST,
                Experience.ExperienceType.WINE_PAIRING,
            ],
            is_blocked=False,
        )
        experience_id = self.request.query_params.get("experience")
        guest_count = self.request.query_params.get("guest_count")
        if experience_id:
            queryset = queryset.filter(experience_id=experience_id)
        if guest_count and guest_count.isdigit():
            guest_count_value = int(guest_count)
            queryset = queryset.filter(
                experience__min_guests__lte=guest_count_value,
                experience__max_guests__gte=guest_count_value,
                spots_available__gte=guest_count_value,
            )

        current = timezone.localtime()
        return queryset.filter(
            Q(date__gt=current.date())
            | Q(date=current.date(), start_time__gte=current.time())
        ).order_by("date", "start_time")


class BookingListCreateView(generics.GenericAPIView):
    """Create a visit booking and expose a Mercado Pago preference."""

    permission_classes = [permissions.AllowAny]
    serializer_class = PublicBookingCreateSerializer

    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Create the booking and return the checkout preference."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = serializer.create_with_preference()
        except MercadoPagoAPIError as exc:
            logger.error("visit_booking_preference_failed", error=str(exc))
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        response_data = {
            "booking": PublicBookingSerializer(payload["booking"]).data,
            "preference": payload["preference"],
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class BookingDetailView(generics.RetrieveAPIView):
    """Return a single booking to its owner or guest token bearer."""

    permission_classes = [permissions.AllowAny]
    serializer_class = PublicBookingSerializer

    def get_object(self):
        """Allow authenticated owners or guests with a signed access token."""
        if self.request.user.is_authenticated:
            booking = (
                Booking.objects.select_related("user", "time_slot", "time_slot__experience")
                .filter(user=self.request.user, pk=self.kwargs["pk"])
                .first()
            )
            if booking is None:
                raise Http404("Booking not found")
            return booking

        guest_booking = resolve_guest_booking(
            booking_id=str(self.kwargs["pk"]),
            guest_access_token=self.request.query_params.get("guest_access_token"),
        )
        if guest_booking is None:
            raise Http404("Booking not found")
        return guest_booking


class BookingCancelView(APIView):
    """Allow a customer to cancel a booking inside the configured window."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, pk: str) -> Response:
        """Cancel the booking and record a manual refund task when needed."""
        booking = self._get_booking(request, pk)
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("user", "time_slot", "time_slot__experience")
                .get(pk=booking.pk)
            )
            try:
                booking, _refund = cancel_booking(
                    booking,
                    actor=request.user,
                    note="Cancelación solicitada por cliente.",
                    enforce_deadline=True,
                )
            except ReservationIntegrityError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        booking.refresh_from_db()
        return Response(PublicBookingSerializer(booking).data)

    def _get_booking(self, request: Request, pk: str) -> Booking:
        """Return the authenticated booking or a guest booking with a valid token."""
        if request.user.is_authenticated:
            booking = (
                Booking.objects.select_related("user", "time_slot", "time_slot__experience")
                .filter(user=request.user, pk=pk)
                .first()
            )
            if booking is None:
                raise Http404("Booking not found")
            return booking

        guest_booking = resolve_guest_booking(
            booking_id=pk,
            guest_access_token=request.query_params.get("guest_access_token"),
        )
        if guest_booking is None:
            raise Http404("Booking not found")
        return guest_booking


class BookingPaymentWebhookView(APIView):
    """Receive Mercado Pago notifications for visit bookings."""

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Persist the raw webhook, validate it and sync booking payment state."""
        payload = request.data if isinstance(request.data, dict) else {}
        topic = str(
            request.query_params.get("type")
            or request.query_params.get("topic")
            or payload.get("type")
            or payload.get("topic")
            or ""
        )
        raw_payload_data = payload.get("data")
        payload_data = raw_payload_data if isinstance(raw_payload_data, dict) else {}
        notification_id = str(
            payload.get("id")
            or request.query_params.get("id")
            or request.query_params.get("data.id")
            or payload_data.get("id")
            or "unknown"
        )
        payment_resource_id = request.query_params.get("data.id") or str(
            payload_data.get("id", "")
        )
        if not payment_resource_id and topic == "payment":
            payment_resource_id = str(
                request.query_params.get("id") or payload.get("id") or ""
            )
        deduplication_key = build_webhook_deduplication_key(
            topic=topic or "unknown",
            notification_id=notification_id,
            payment_resource_id=payment_resource_id,
            payload=payload,
        )
        webhook_log, created = PaymentWebhookLog.objects.get_or_create(
            deduplication_key=deduplication_key,
            defaults={
                "mp_notification_id": notification_id,
                "topic": topic or "unknown",
                "payload": payload,
            },
        )
        if not created and webhook_log.processed:
            return Response(status=status.HTTP_200_OK)

        try:
            if not has_valid_signature(request, payload):
                webhook_log.error = "invalid_signature"
                webhook_log.save(update_fields=["error"])
                logger.warning(
                    "visit_booking_webhook_invalid_signature",
                    notification_id=notification_id,
                )
                return Response(status=status.HTTP_403_FORBIDDEN)

            if topic != "payment":
                webhook_log.processed = True
                webhook_log.save(update_fields=["processed"])
                return Response(status=status.HTTP_200_OK)

            if not payment_resource_id:
                webhook_log.error = "missing_payment_id"
                webhook_log.save(update_fields=["error"])
                return Response(status=status.HTTP_200_OK)

            payment_data = MercadoPagoClient().get_payment(str(payment_resource_id))
            booking_payment = self._find_booking_payment(payment_data)
            if booking_payment is None:
                webhook_log.error = "booking_payment_not_found"
                webhook_log.save(update_fields=["error"])
                logger.warning(
                    "visit_booking_payment_not_found",
                    notification_id=notification_id,
                    payment_id=payment_resource_id,
                )
                return Response(status=status.HTTP_200_OK)

            sync_booking_payment(booking_payment.pk, payment_data)
            webhook_log.processed = True
            webhook_log.error = ""
            webhook_log.save(update_fields=["processed", "error"])
        except ReservationIntegrityError as exc:
            BookingPayment.objects.filter(pk=booking_payment.pk).update(
                status_detail="integrity_validation_failed"
            )
            webhook_log.error = f"booking_payment_integrity_error: {exc}"
            webhook_log.processed = True
            webhook_log.save(update_fields=["error", "processed"])
            logger.error(
                "visit_booking_payment_integrity_failed",
                notification_id=notification_id,
                payment_id=payment_resource_id,
                error=str(exc),
            )
            return Response(status=status.HTTP_200_OK)
        except MercadoPagoAPIError as exc:
            webhook_log.error = str(exc)
            webhook_log.save(update_fields=["error"])
            logger.error("visit_booking_webhook_fetch_failed", error=str(exc))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:  # pragma: no cover - defensive logging
            webhook_log.error = str(exc)
            webhook_log.save(update_fields=["error"])
            logger.error("visit_booking_webhook_failed", error=str(exc))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)

    def _find_booking_payment(self, payment_data: dict[str, object]) -> BookingPayment | None:
        """Locate the local booking payment from Mercado Pago payment data."""
        external_reference = str(payment_data.get("external_reference") or "")
        metadata = payment_data.get("metadata") or {}
        booking_id = external_reference or str(metadata.get("booking_id") or "")
        if booking_id:
            return (
                BookingPayment.objects.select_related("booking")
                .filter(booking_id=booking_id)
                .first()
            )

        preference_id = str(metadata.get("preference_id") or "")
        if preference_id:
            return (
                BookingPayment.objects.select_related("booking")
                .filter(mp_preference_id=preference_id)
                .first()
            )
        return None
