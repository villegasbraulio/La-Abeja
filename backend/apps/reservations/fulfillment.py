"""External reservation fulfillment operations executed by outbox workers."""

from __future__ import annotations

from apps.notifications.email import EmailService

from .models import Booking
from .services import booking_cancellation_deadline


def send_booking_email(booking: Booking, *, template: str) -> None:
    """Send a booking email and surface delivery failures to the outbox."""
    recipient = booking.customer_email or (booking.user.email if booking.user_id else "")
    if not recipient:
        return

    sent = EmailService.send_transactional(
        to=recipient,
        template=template,
        context={
            "confirmation_code": booking.confirmation_code,
            "customer_name": booking.customer_name,
            "status": booking.get_status_display(),
            "experience": booking.time_slot.experience.name,
            "date": booking.time_slot.date,
            "start_time": booking.time_slot.start_time,
            "end_time": booking.time_slot.end_time,
            "guest_count": booking.guest_count,
            "total": booking.total_price,
            "cancellation_deadline": booking_cancellation_deadline(booking),
        },
    )
    if not sent:
        raise RuntimeError("No se pudo enviar el email transaccional de la reserva.")
