import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Link } from "react-router-dom";
import { visitsApi } from "../../api/visits";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { visitFaqs, visitPlanningSteps } from "../../lib/siteContent";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { formatARS, formatDate } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";
import type { VisitBookingCreatePayload, VisitExperience, VisitTimeSlot } from "../../types/visits";

interface BookingFormState {
  customer_first_name: string;
  customer_last_name: string;
  customer_email: string;
  customer_phone: string;
  special_requests: string;
  dietary_restrictions_text: string;
}

const emptyBookingForm: BookingFormState = {
  customer_first_name: "",
  customer_last_name: "",
  customer_email: "",
  customer_phone: "",
  special_requests: "",
  dietary_restrictions_text: "",
};

function formatSlotTime(slot: VisitTimeSlot) {
  return `${slot.start_time.slice(0, 5)} - ${slot.end_time.slice(0, 5)}`;
}

function groupSlotsByDate(slots: VisitTimeSlot[]) {
  return slots.reduce<Record<string, VisitTimeSlot[]>>((accumulator, slot) => {
    accumulator[slot.date] = [...(accumulator[slot.date] ?? []), slot];
    return accumulator;
  }, {});
}

function textToList(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function ExperienceCard({
  experience,
  isSelected,
  onSelect,
}: {
  experience: VisitExperience;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`overflow-hidden rounded-[28px] border text-left transition ${
        isSelected
          ? "border-burgundy-900 bg-burgundy-950 text-cream-50 shadow-velvet"
          : "border-burgundy-100 bg-white text-burgundy-950 shadow-velvet"
      }`}
    >
      <img
        src={wineImageSrc(experience.cover_image)}
        alt={experience.name}
        onError={applyWineImageFallback}
        className="h-48 w-full object-cover"
      />
      <div className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-serif text-3xl">{experience.name}</h3>
          <span className="rounded-full bg-white/10 px-3 py-2 text-sm font-semibold">
            {formatARS(experience.price_per_person)} por persona
          </span>
        </div>
        <p className="mt-4 leading-7 text-current/75">{experience.description}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          <span className="rounded-full bg-burgundy-50 px-3 py-2 text-sm font-medium text-burgundy-800">
            {experience.duration_minutes} min
          </span>
          <span className="rounded-full bg-burgundy-50 px-3 py-2 text-sm font-medium text-burgundy-800">
            {experience.min_guests} a {experience.max_guests} personas
          </span>
          {experience.next_available_date ? (
            <span className="rounded-full bg-burgundy-50 px-3 py-2 text-sm font-medium text-burgundy-800">
              Próxima fecha: {formatDate(experience.next_available_date)}
            </span>
          ) : null}
        </div>
      </div>
    </button>
  );
}

export function VisitPage() {
  const user = useAuthStore((state) => state.user);
  const [selectedExperienceId, setSelectedExperienceId] = useState<string | null>(null);
  const [guestCount, setGuestCount] = useState("2");
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(null);
  const [bookingForm, setBookingForm] = useState<BookingFormState>(emptyBookingForm);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [redirectUrl, setRedirectUrl] = useState<string | null>(null);

  const experiencesQuery = useQuery({
    queryKey: ["visit-experiences"],
    queryFn: visitsApi.experiences,
  });

  const slotsQuery = useQuery({
    queryKey: ["visit-slots", selectedExperienceId, guestCount],
    queryFn: () =>
      visitsApi.slots({
        experience: selectedExperienceId ?? undefined,
        guest_count: Number.parseInt(guestCount, 10) || undefined,
      }),
    enabled: Boolean(selectedExperienceId),
  });

  const experiences = experiencesQuery.data ?? [];
  const slots = slotsQuery.data ?? [];
  const selectedExperience =
    experiences.find((experience) => experience.id === selectedExperienceId) ?? null;
  const selectedSlot = slots.find((slot) => slot.id === selectedSlotId) ?? null;
  const groupedSlots = useMemo(() => groupSlotsByDate(slots), [slots]);

  useEffect(() => {
    if (!selectedExperienceId && experiences.length > 0) {
      setSelectedExperienceId(experiences[0].id);
    }
  }, [experiences, selectedExperienceId]);

  useEffect(() => {
    if (!user) {
      return;
    }
    setBookingForm((current) => ({
      ...current,
      customer_first_name: current.customer_first_name || user.first_name,
      customer_last_name: current.customer_last_name || user.last_name,
      customer_email: current.customer_email || user.email,
      customer_phone: current.customer_phone || user.phone || "",
    }));
  }, [user]);

  useEffect(() => {
    if (slots.length === 0) {
      setSelectedSlotId(null);
      return;
    }
    if (!selectedSlotId || !slots.some((slot) => slot.id === selectedSlotId)) {
      setSelectedSlotId(slots[0].id);
    }
  }, [selectedSlotId, slots]);

  const bookingMutation = useMutation({
    mutationFn: async () => {
      if (!selectedSlotId) {
        throw new Error("Elegí una fecha y horario antes de continuar.");
      }
      const payload: VisitBookingCreatePayload = {
        time_slot: selectedSlotId,
        guest_count: Number.parseInt(guestCount, 10),
        customer_first_name: bookingForm.customer_first_name.trim(),
        customer_last_name: bookingForm.customer_last_name.trim(),
        customer_email: bookingForm.customer_email.trim(),
        customer_phone: bookingForm.customer_phone.trim(),
        special_requests: bookingForm.special_requests.trim(),
        dietary_restrictions: textToList(bookingForm.dietary_restrictions_text),
      };
      return visitsApi.createBooking(payload);
    },
    onSuccess: ({ preference }) => {
      const nextUrl = preference.init_point ?? preference.sandbox_init_point;
      setBookingError(null);
      setRedirectUrl(nextUrl);
      if (nextUrl) {
        window.location.assign(nextUrl);
      }
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ detail?: string; guest_count?: string[]; time_slot?: string[] }>;
      setBookingError(
        axiosError.response?.data?.detail ??
          axiosError.response?.data?.guest_count?.[0] ??
          axiosError.response?.data?.time_slot?.[0] ??
          (error instanceof Error ? error.message : "No pudimos preparar la reserva."),
      );
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBookingError(null);
    setRedirectUrl(null);
    bookingMutation.mutate();
  }

  return (
    <div>
      <PageHero
        eyebrow="Visitas y hospitalidad"
        title="Reservá la visita, elegí el horario y dejala pagada en un solo flujo."
        description="El recorrido ahora tiene agenda real: cupos por turno, precio por persona y pago inmediato para que la confirmación no dependa de mensajes manuales."
        aside={
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
              Operación clara
            </p>
            <div className="mt-5 space-y-4 text-burgundy-900">
              <p>
                <span className="font-semibold">Ubicación:</span> San Rafael, Mendoza
              </p>
              <p>
                <span className="font-semibold">Pago:</span> Checkout Pro de Mercado Pago
              </p>
              <p>
                <span className="font-semibold">Formato:</span> cupos por horario con confirmación automática
              </p>
            </div>
          </div>
        }
      >
        <Link to="#reservar">
          <Button>Reservar visita</Button>
        </Link>
        <Link to="/contacto?tipo=evento">
          <Button variant="ghost">Consultar evento privado</Button>
        </Link>
      </PageHero>

      <section id="reservar" className="mx-auto max-w-7xl px-6 py-8">
        <SectionHeading
          eyebrow="Reserva online"
          title="Elegí experiencia, fecha y horario sin salir de la página."
          description="La reserva bloquea el cupo mientras se procesa el pago y confirma la visita cuando Mercado Pago aprueba la operación."
        />

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            {experiencesQuery.isLoading ? <p className="text-burgundy-700">Cargando experiencias...</p> : null}
            {experiences.map((experience) => (
              <ExperienceCard
                key={experience.id}
                experience={experience}
                isSelected={experience.id === selectedExperienceId}
                onSelect={() => setSelectedExperienceId(experience.id)}
              />
            ))}
          </div>

          <div className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
            <SectionHeading
              eyebrow="Checkout de visita"
              title={selectedExperience ? selectedExperience.name : "Elegí una experiencia"}
              description="Seleccioná el grupo, un turno disponible y tus datos de contacto."
            />

            {selectedExperience ? (
              <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium text-burgundy-900">
                    Personas
                    <input
                      type="number"
                      min={selectedExperience.min_guests}
                      max={selectedExperience.max_guests}
                      value={guestCount}
                      onChange={(event) => setGuestCount(event.target.value)}
                      className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                    />
                  </label>
                  <div className="rounded-[20px] bg-burgundy-950 px-5 py-4 text-cream-50">
                    <p className="text-sm uppercase tracking-[0.18em] text-gold-300">Total estimado</p>
                    <p className="mt-2 font-serif text-4xl">
                      {formatARS(Number.parseInt(guestCount || "0", 10) * Number.parseFloat(selectedExperience.price_per_person))}
                    </p>
                    <p className="mt-2 text-sm text-cream-100/75">
                      {formatARS(selectedExperience.price_per_person)} por persona
                    </p>
                  </div>
                </div>

                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    Horarios disponibles
                  </p>
                  {slotsQuery.isLoading ? <p className="mt-4 text-burgundy-700">Buscando turnos...</p> : null}
                  {!slotsQuery.isLoading && slots.length === 0 ? (
                    <p className="mt-4 text-burgundy-700">
                      No encontramos horarios para esa cantidad de personas. Probá otro grupo o experiencia.
                    </p>
                  ) : null}
                  <div className="mt-4 space-y-4">
                    {Object.entries(groupedSlots).map(([date, dateSlots]) => (
                      <div key={date}>
                        <p className="text-sm font-semibold text-burgundy-950">{formatDate(date)}</p>
                        <div className="mt-3 flex flex-wrap gap-3">
                          {dateSlots.map((slot) => (
                            <button
                              key={slot.id}
                              type="button"
                              onClick={() => setSelectedSlotId(slot.id)}
                              className={`rounded-[18px] border px-4 py-3 text-sm transition ${
                                slot.id === selectedSlotId
                                  ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                                  : "border-burgundy-200 bg-white text-burgundy-900"
                              }`}
                            >
                              <span className="block font-semibold">{formatSlotTime(slot)}</span>
                              <span className="mt-1 block text-xs opacity-75">
                                {slot.spots_available} lugares disponibles
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium text-burgundy-900">
                    Nombre
                    <input
                      value={bookingForm.customer_first_name}
                      onChange={(event) =>
                        setBookingForm((current) => ({
                          ...current,
                          customer_first_name: event.target.value,
                        }))
                      }
                      className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                      required
                    />
                  </label>
                  <label className="text-sm font-medium text-burgundy-900">
                    Apellido
                    <input
                      value={bookingForm.customer_last_name}
                      onChange={(event) =>
                        setBookingForm((current) => ({
                          ...current,
                          customer_last_name: event.target.value,
                        }))
                      }
                      className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                      required
                    />
                  </label>
                  <label className="text-sm font-medium text-burgundy-900">
                    Email
                    <input
                      type="email"
                      value={bookingForm.customer_email}
                      onChange={(event) =>
                        setBookingForm((current) => ({
                          ...current,
                          customer_email: event.target.value,
                        }))
                      }
                      className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                      required
                    />
                  </label>
                  <label className="text-sm font-medium text-burgundy-900">
                    Teléfono
                    <input
                      value={bookingForm.customer_phone}
                      onChange={(event) =>
                        setBookingForm((current) => ({
                          ...current,
                          customer_phone: event.target.value,
                        }))
                      }
                      className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                      required
                    />
                  </label>
                </div>

                <label className="block text-sm font-medium text-burgundy-900">
                  Restricciones alimentarias
                  <input
                    value={bookingForm.dietary_restrictions_text}
                    onChange={(event) =>
                      setBookingForm((current) => ({
                        ...current,
                        dietary_restrictions_text: event.target.value,
                      }))
                    }
                    placeholder="Ej: sin gluten, vegetariano"
                    className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                  />
                </label>

                <label className="block text-sm font-medium text-burgundy-900">
                  Pedido especial
                  <textarea
                    value={bookingForm.special_requests}
                    onChange={(event) =>
                      setBookingForm((current) => ({
                        ...current,
                        special_requests: event.target.value,
                      }))
                    }
                    rows={4}
                    className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                    placeholder="Celebración, acceso especial, contexto del grupo"
                  />
                </label>

                {selectedSlot ? (
                  <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                    <p className="font-semibold text-burgundy-950">Resumen de la reserva</p>
                    <p className="mt-3">
                      {selectedExperience.name} · {formatDate(selectedSlot.date)} · {formatSlotTime(selectedSlot)}
                    </p>
                    <p className="mt-2">
                      {guestCount} personas · {formatARS(selectedExperience.price_per_person)} por persona
                    </p>
                  </div>
                ) : null}

                {bookingError ? (
                  <div className="rounded-[20px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {bookingError}
                  </div>
                ) : null}

                {redirectUrl ? (
                  <div className="rounded-[20px] border border-burgundy-100 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
                    Si no te redirigimos automáticamente,{" "}
                    <a href={redirectUrl} className="font-semibold underline">
                      continuá con Mercado Pago acá
                    </a>
                    .
                  </div>
                ) : null}

                <Button type="submit" disabled={bookingMutation.isPending || !selectedSlotId}>
                  {bookingMutation.isPending ? "Preparando pago..." : "Reservar y pagar"}
                </Button>
              </form>
            ) : (
              <p className="mt-6 text-burgundy-700">Cargá una experiencia activa desde el backoffice para empezar.</p>
            )}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[32px] border border-white/70 bg-burgundy-950 p-8 text-cream-50 shadow-velvet">
            <SectionHeading
              eyebrow="Cómo funciona"
              title="El flujo queda cerrado antes de llegar a la bodega."
              description="Negocio define cupos y horarios; la persona reserva el turno exacto y lo deja abonado."
              tone="light"
            />
            <div className="mt-8 space-y-4">
              {visitPlanningSteps.map((step, index) => (
                <div
                  key={step}
                  className="rounded-[24px] border border-white/10 bg-white/5 px-5 py-4"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
                    Paso {index + 1}
                  </p>
                  <p className="mt-2 leading-7 text-cream-100/80">{step}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
            <SectionHeading
              eyebrow="FAQ de visitas"
              title="Lo que normalmente preguntaría alguien antes de reservar."
            />
            <div className="mt-8 space-y-4">
              {visitFaqs.map((item) => (
                <details
                  key={item.question}
                  className="rounded-[24px] border border-burgundy-100 bg-cream-50 px-5 py-4"
                >
                  <summary className="cursor-pointer list-none text-lg font-semibold text-burgundy-950">
                    {item.question}
                  </summary>
                  <p className="mt-3 leading-7 text-burgundy-800">{item.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
