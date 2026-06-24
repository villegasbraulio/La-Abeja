import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { visitsApi } from "../../api/visits";
import { Button } from "../../components/ui/Button";
import { formatARS, formatDate } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";

function resolveVisitStatus(searchParams: URLSearchParams) {
  const status = (searchParams.get("status") || "").toLowerCase();
  if (status === "approved") {
    return {
      title: "Reserva confirmada",
      description: "Mercado Pago aprobó el pago y la visita ya quedó confirmada.",
    };
  }
  if (status === "pending") {
    return {
      title: "Pago en proceso",
      description: "La reserva quedó tomada y estamos esperando la confirmación final del pago.",
    };
  }
  return {
    title: "Pago no confirmado",
    description: "La reserva existe, pero el pago no quedó aprobado. Podés revisar el estado o contactarnos.",
  };
}

export function VisitBookingResultPage() {
  const [searchParams] = useSearchParams();
  const accessToken = useAuthStore((state) => state.accessToken);
  const bookingId = searchParams.get("booking_id");
  const guestAccessToken = searchParams.get("guest_access_token");
  const statusMeta = resolveVisitStatus(searchParams);

  const bookingQuery = useQuery({
    queryKey: ["visit-booking-detail", bookingId, guestAccessToken],
    queryFn: () => visitsApi.bookingDetail(bookingId ?? "", guestAccessToken),
    enabled: Boolean(bookingId && (accessToken || guestAccessToken)),
  });

  const booking = bookingQuery.data;

  return (
    <section className="mx-auto max-w-4xl px-6 py-20">
      <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
          Resultado de la reserva
        </p>
        <h1 className="mt-3 font-serif text-3xl text-burgundy-950 sm:text-4xl">{statusMeta.title}</h1>
        <p className="mt-4 max-w-2xl leading-7 text-burgundy-800">{statusMeta.description}</p>

        {booking ? (
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5">
              <p className="text-sm uppercase tracking-[0.18em] text-burgundy-500">Reserva</p>
              <p className="mt-3 font-serif text-3xl text-burgundy-950">{booking.confirmation_code}</p>
              <p className="mt-2 text-sm text-burgundy-700">{booking.experience_name}</p>
              <p className="mt-2 text-sm text-burgundy-700">
                {formatDate(booking.slot_date)} · {booking.slot_start_time.slice(0, 5)} - {booking.slot_end_time.slice(0, 5)}
              </p>
              <p className="mt-2 text-sm text-burgundy-700">
                {booking.guest_count} personas · {formatARS(booking.total_price)}
              </p>
            </div>

            <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5">
              <p className="text-sm uppercase tracking-[0.18em] text-burgundy-500">Estado</p>
              <p className="mt-3 font-semibold text-burgundy-950">{booking.status_label}</p>
              <p className="mt-2 text-sm text-burgundy-700">
                Pago: {booking.payment?.status ?? "sin registro"}
              </p>
              <p className="mt-2 text-sm text-burgundy-700">
                Contacto: {booking.customer_email} · {booking.customer_phone}
              </p>
            </div>
          </div>
        ) : null}

        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/visitas">
            <Button>Volver a visitas</Button>
          </Link>
          <Link to="/contacto?tipo=visita">
            <Button variant="ghost">Necesito ayuda</Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
