import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { visitsApi } from "../../api/visits";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { visitFaqs } from "../../lib/siteContent";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { cn, formatARS, formatDate } from "../../lib/utils";
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

function parseDateValue(value: string) {
  return new Date(`${value}T12:00:00`);
}

function formatMonthLabel(value: string) {
  return new Intl.DateTimeFormat("es-AR", { month: "long", year: "numeric" }).format(
    parseDateValue(`${value}-01`),
  );
}

function formatWeekdayLabel(value: string) {
  return new Intl.DateTimeFormat("es-AR", { weekday: "long" }).format(parseDateValue(value));
}

function getMonthKey(value: string) {
  return value.slice(0, 7);
}

function shiftMonth(monthKey: string, offset: number) {
  const [year, month] = monthKey.split("-").map(Number);
  const next = new Date(year, month - 1 + offset, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

function getCalendarDays(monthKey: string) {
  const [year, month] = monthKey.split("-").map(Number);
  const firstDay = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const startOffset = (firstDay.getDay() + 6) % 7;
  const cells: Array<{ date: string; dayNumber: number; inCurrentMonth: boolean }> = [];

  for (let index = 0; index < startOffset; index += 1) {
    cells.push({
      date: `pad-start-${index}`,
      dayNumber: 0,
      inCurrentMonth: false,
    });
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push({
      date: `${monthKey}-${String(day).padStart(2, "0")}`,
      dayNumber: day,
      inCurrentMonth: true,
    });
  }

  while (cells.length % 7 !== 0) {
    cells.push({
      date: `pad-end-${cells.length}`,
      dayNumber: 0,
      inCurrentMonth: false,
    });
  }

  return cells;
}

function textToList(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildVisitPath(pathname: string, updates: Record<string, string | null | undefined>) {
  const searchParams = new URLSearchParams();

  Object.entries(updates).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      searchParams.set(key, value);
    }
  });

  return `${pathname}${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
}

function ExperienceCard({
  experience,
  onSelect,
}: {
  experience: VisitExperience;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-[280px] flex-none overflow-hidden rounded-[24px] border border-burgundy-100 bg-white text-left shadow-velvet transition hover:-translate-y-0.5 hover:border-burgundy-300 md:w-[320px]"
    >
      <img
        src={wineImageSrc(experience.cover_image)}
        alt={experience.name}
        onError={applyWineImageFallback}
        className="h-36 w-full object-cover"
      />
      <div className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-serif text-xl text-burgundy-950">{experience.name}</h3>
          <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-xs font-semibold text-burgundy-800">
            {formatARS(experience.price_per_person)}
          </span>
        </div>
        <p className="mt-2 line-clamp-2 min-h-[56px] text-sm leading-6 text-burgundy-800">
          {experience.description}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-[11px] font-medium text-burgundy-800">
            {experience.duration_minutes} min
          </span>
          <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-[11px] font-medium text-burgundy-800">
            {experience.min_guests} a {experience.max_guests}
          </span>
          {experience.next_available_date ? (
            <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-[11px] font-medium text-burgundy-800">
              {formatDate(experience.next_available_date)}
            </span>
          ) : null}
        </div>
        <div className="mt-3 flex justify-end">
          <span className="rounded-full bg-burgundy-950 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-cream-50">
            Ver horarios
          </span>
        </div>
      </div>
    </button>
  );
}

function ExperienceHighlights({ experience }: { experience: VisitExperience }) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-burgundy-100 bg-white shadow-velvet">
      <div className="grid sm:grid-cols-[200px_1fr]">
        <img
          src={wineImageSrc(experience.cover_image)}
          alt={experience.name}
          onError={applyWineImageFallback}
          className="h-48 w-full object-cover sm:h-full"
        />
        <div className="p-5">
          <h3 className="font-serif text-3xl text-burgundy-950">{experience.name}</h3>
          <p className="mt-3 text-sm leading-6 text-burgundy-800">{experience.description}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-xs font-semibold text-burgundy-800">
              {formatARS(experience.price_per_person)} por persona
            </span>
            <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-xs font-semibold text-burgundy-800">
              {experience.duration_minutes} min
            </span>
            <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-xs font-semibold text-burgundy-800">
              {experience.min_guests} a {experience.max_guests}
            </span>
            {experience.next_available_date ? (
              <span className="rounded-full bg-burgundy-50 px-3 py-1.5 text-xs font-semibold text-burgundy-800">
                Próxima fecha: {formatDate(experience.next_available_date)}
              </span>
            ) : null}
          </div>

          {experience.highlights.length > 0 || experience.includes.length > 0 ? (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {experience.highlights.length > 0 ? (
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    Ideal para
                  </p>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-burgundy-800">
                    {experience.highlights.map((highlight) => (
                      <li key={highlight} className="flex gap-2">
                        <span className="pt-1 text-burgundy-500">•</span>
                        <span>{highlight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {experience.includes.length > 0 ? (
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    Incluye
                  </p>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-burgundy-800">
                    {experience.includes.map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="pt-1 text-burgundy-500">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function VisitBookingFormSection({
  selectedExperience,
  selectedSlot,
  bookingForm,
  setBookingForm,
  bookingError,
  redirectUrl,
  bookingMutation,
  handleSubmit,
}: {
  selectedExperience: VisitExperience;
  selectedSlot: VisitTimeSlot;
  bookingForm: BookingFormState;
  setBookingForm: Dispatch<SetStateAction<BookingFormState>>;
  bookingError: string | null;
  redirectUrl: string | null;
  bookingMutation: { isPending: boolean };
  handleSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet">
      <SectionHeading eyebrow="Pago" title="Completá la reserva" />

      <div className="mt-5 rounded-[20px] border border-burgundy-100 bg-cream-50 p-4 text-sm text-burgundy-800">
        <p className="font-semibold text-burgundy-950">{selectedExperience.name}</p>
        <p className="mt-2">
          {formatDate(selectedSlot.date)} · {formatSlotTime(selectedSlot)}
        </p>
      </div>

      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <div className="grid gap-3 md:grid-cols-2">
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

        <Button type="submit" disabled={bookingMutation.isPending}>
          {bookingMutation.isPending ? "Preparando pago..." : "Reservar y pagar"}
        </Button>
      </form>
    </div>
  );
}

export function VisitPage() {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [bookingForm, setBookingForm] = useState<BookingFormState>(emptyBookingForm);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [redirectUrl, setRedirectUrl] = useState<string | null>(null);

  const isScheduleScreen = location.pathname === "/visitas/horarios";
  const isPaymentScreen = location.pathname === "/visitas/pago";

  const experienceId = searchParams.get("experience");
  const guestCount = searchParams.get("guests") ?? "2";
  const selectedDate = searchParams.get("date");
  const slotIdParam = searchParams.get("slot");
  const selectedSlotId = slotIdParam ? Number.parseInt(slotIdParam, 10) : null;

  const experiencesQuery = useQuery({
    queryKey: ["visit-experiences"],
    queryFn: visitsApi.experiences,
  });

  const slotsQuery = useQuery({
    queryKey: ["visit-slots", experienceId, guestCount],
    queryFn: () =>
      visitsApi.slots({
        experience: experienceId ?? undefined,
        guest_count: Number.parseInt(guestCount, 10) || undefined,
      }),
    enabled: Boolean(experienceId),
  });

  const experiences = experiencesQuery.data ?? [];
  const slots = slotsQuery.data ?? [];
  const selectedExperience = experiences.find((experience) => experience.id === experienceId) ?? null;
  const selectedSlot = slots.find((slot) => slot.id === selectedSlotId) ?? null;
  const groupedSlots = useMemo(() => groupSlotsByDate(slots), [slots]);
  const visibleDateSlots = selectedDate ? groupedSlots[selectedDate] ?? [] : [];
  const availableMonthKeys = useMemo(
    () => Array.from(new Set(slots.map((slot) => getMonthKey(slot.date)))).sort(),
    [slots],
  );
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const visibleMonthIndex = visibleMonth ? availableMonthKeys.indexOf(visibleMonth) : -1;
  const calendarDays = visibleMonth ? getCalendarDays(visibleMonth) : [];

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
    if ((isScheduleScreen || isPaymentScreen) && !experienceId) {
      navigate("/visitas", { replace: true });
    }
  }, [experienceId, isPaymentScreen, isScheduleScreen, navigate]);

  useEffect(() => {
    if (isPaymentScreen && (!experienceId || !selectedSlotId)) {
      navigate("/visitas", { replace: true });
    }
  }, [experienceId, isPaymentScreen, navigate, selectedSlotId]);

  useEffect(() => {
    if (slots.length === 0) {
      setVisibleMonth(null);
      return;
    }

    const firstDate = slots[0].date;
    if (!visibleMonth || !availableMonthKeys.includes(visibleMonth)) {
      setVisibleMonth(getMonthKey(firstDate));
    }

    if (isScheduleScreen && !selectedDate) {
      navigate(
        buildVisitPath("/visitas/horarios", {
          experience: experienceId,
          guests: guestCount,
          date: firstDate,
        }),
        { replace: true },
      );
    }
  }, [
    availableMonthKeys,
    experienceId,
    guestCount,
    isScheduleScreen,
    navigate,
    selectedDate,
    slots,
    visibleMonth,
  ]);

  const bookingMutation = useMutation({
    mutationFn: async () => {
      if (!selectedSlotId) {
        throw new Error("Elegí un día y un horario antes de continuar.");
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

  function handleSelectExperience(nextExperienceId: string) {
    navigate(
      buildVisitPath("/visitas/horarios", {
        experience: nextExperienceId,
        guests: guestCount,
      }),
    );
  }

  function handleGuestCountChange(value: string) {
    if (!experienceId) {
      return;
    }

    navigate(
      buildVisitPath("/visitas/horarios", {
        experience: experienceId,
        guests: value,
      }),
    );
  }

  function handleSelectDate(date: string) {
    if (!experienceId) {
      return;
    }

    navigate(
      buildVisitPath("/visitas/horarios", {
        experience: experienceId,
        guests: guestCount,
        date,
      }),
    );
  }

  function handleSelectSlot(slotId: number) {
    if (!experienceId || !selectedDate) {
      return;
    }

    navigate(
      buildVisitPath("/visitas/pago", {
        experience: experienceId,
        guests: guestCount,
        date: selectedDate,
        slot: String(slotId),
      }),
    );
  }

  return (
    <div>
      <PageHero
        eyebrow="Visitas y hospitalidad"
        title="Visitas y degustaciones en bodega."
        description="Recorridos, catas y propuestas privadas para grupos pequeños o encuentros especiales en bodega."
        className="py-10 md:py-12"
        contentClassName="max-w-6xl"
        titleClassName="max-w-6xl text-3xl leading-tight md:text-4xl lg:text-[3.35rem]"
        descriptionClassName="max-w-4xl text-base leading-7 md:text-lg"
      >
        <Link to="/contacto?tipo=evento">
          <Button variant="ghost">Consultar evento privado</Button>
        </Link>
      </PageHero>

      {!isScheduleScreen && !isPaymentScreen ? (
        <section className="mx-auto max-w-7xl px-6 py-8">
          <SectionHeading
            eyebrow="Visitas"
            title="Elegí la experiencia"
          />
          <div className="mt-6 rounded-[28px] border border-burgundy-100 bg-white p-4 shadow-velvet">
            {experiencesQuery.isLoading ? <p className="text-burgundy-700">Cargando experiencias...</p> : null}
            <div className="flex gap-3 overflow-x-auto pb-2">
              {experiences.map((experience) => (
                <ExperienceCard
                  key={experience.id}
                  experience={experience}
                  onSelect={() => handleSelectExperience(experience.id)}
                />
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {isScheduleScreen && selectedExperience ? (
        <section className="mx-auto max-w-7xl px-6 py-8">
          <div className="grid gap-5 xl:grid-cols-[0.78fr_1.22fr] xl:items-start">
            <div className="xl:sticky xl:top-6">
              <ExperienceHighlights experience={selectedExperience} />
            </div>

            <div className="rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                  Disponibilidad
                </p>
                <Link to="/visitas">
                  <Button variant="ghost">Cambiar visita</Button>
                </Link>
              </div>

              <div className="mt-5 grid items-end gap-3 lg:grid-cols-[180px_minmax(0,320px)]">
                <label className="text-sm font-medium text-burgundy-900">
                  Personas
                  <input
                    type="number"
                    min={selectedExperience.min_guests}
                    max={selectedExperience.max_guests}
                    value={guestCount}
                    onChange={(event) => handleGuestCountChange(event.target.value)}
                    className="mt-2 w-full rounded-[18px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                  />
                </label>
                <div className="rounded-[18px] bg-burgundy-950 px-4 py-3 text-cream-50">
                  <p className="text-xs uppercase tracking-[0.18em] text-gold-300">Total estimado</p>
                  <p className="mt-2 font-serif text-2xl md:text-[2rem]">
                    {formatARS(
                      Number.parseInt(guestCount || "0", 10) *
                        Number.parseFloat(selectedExperience.price_per_person),
                    )}
                  </p>
                  <p className="mt-1 text-sm text-cream-100/75">
                    {formatARS(selectedExperience.price_per_person)} por persona
                  </p>
                </div>
              </div>

              {slotsQuery.isLoading ? <p className="mt-4 text-burgundy-700">Buscando turnos...</p> : null}
              {!slotsQuery.isLoading && slots.length === 0 ? (
                <p className="mt-4 text-burgundy-700">
                  No encontramos horarios para esa cantidad de personas. Probá otro grupo o experiencia.
                </p>
              ) : null}

              {!slotsQuery.isLoading && visibleMonth ? (
                <div className="mt-4 rounded-[20px] border border-burgundy-100 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setVisibleMonth((current) => (current ? shiftMonth(current, -1) : current))}
                      disabled={visibleMonthIndex <= 0}
                    >
                      Mes anterior
                    </Button>
                    <div className="text-center">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                        Mes visible
                      </p>
                      <p className="mt-1 font-serif text-3xl text-burgundy-950">
                        {formatMonthLabel(visibleMonth)}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setVisibleMonth((current) => (current ? shiftMonth(current, 1) : current))}
                      disabled={visibleMonthIndex === -1 || visibleMonthIndex >= availableMonthKeys.length - 1}
                    >
                      Mes siguiente
                    </Button>
                  </div>

                  <div className="mt-3 grid grid-cols-7 gap-1.5 text-center text-[10px] font-semibold uppercase tracking-[0.16em] text-burgundy-500">
                    {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map((label) => (
                      <span key={label}>{label}</span>
                    ))}
                  </div>

                  <div className="mt-2 grid grid-cols-7 gap-1.5">
                    {calendarDays.map((day) => {
                      if (!day.inCurrentMonth) {
                        return <div key={day.date} className="aspect-square rounded-[18px] bg-transparent" />;
                      }

                      const daySlots = groupedSlots[day.date] ?? [];
                      const isSelected = selectedDate === day.date;
                      const isAvailable = daySlots.length > 0;
                      const totalSpots = daySlots.reduce((total, slot) => total + slot.spots_available, 0);

                      return (
                        <button
                          key={day.date}
                          type="button"
                          onClick={() => handleSelectDate(day.date)}
                          disabled={!isAvailable}
                          className={cn(
                            "aspect-square rounded-[14px] border p-1.5 text-left transition",
                            isSelected
                              ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                              : isAvailable
                                ? "border-burgundy-200 bg-cream-50 text-burgundy-950 hover:border-burgundy-400 hover:bg-white"
                                : "border-transparent bg-burgundy-50/50 text-burgundy-300 opacity-60",
                          )}
                        >
                          <span className="block text-sm font-semibold md:text-base">{day.dayNumber}</span>
                          <span className="mt-1 block text-[9px] leading-3 opacity-80 md:text-[10px]">
                            {isAvailable ? `${daySlots.length} horarios` : "Sin cupos"}
                          </span>
                          {isAvailable ? (
                            <span className="mt-0.5 block text-[9px] leading-3 opacity-70 md:text-[10px]">
                              {totalSpots} lugares
                            </span>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {selectedDate ? (
                <div className="mt-4 rounded-[20px] border border-burgundy-100 bg-white p-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    Horarios del {formatWeekdayLabel(selectedDate)} {formatDate(selectedDate)}
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                    {visibleDateSlots.map((slot) => (
                      <button
                        key={slot.id}
                        type="button"
                        onClick={() => handleSelectSlot(slot.id)}
                        className="rounded-[16px] border border-burgundy-200 bg-cream-50 px-3 py-3 text-left text-sm text-burgundy-900 transition hover:border-burgundy-400 hover:bg-white"
                      >
                        <span className="block font-semibold">{formatSlotTime(slot)}</span>
                        <span className="mt-1 block text-xs opacity-75">
                          {slot.spots_available} lugares disponibles
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}

      {isPaymentScreen && selectedExperience && selectedSlot ? (
        <section className="mx-auto max-w-3xl px-6 py-8">
          <SectionHeading eyebrow="Pago" title="Confirmá tu reserva" />
          <div className="mt-6 space-y-4">
            <div className="flex justify-start">
              <Link
                to={buildVisitPath("/visitas/horarios", {
                  experience: experienceId,
                  guests: guestCount,
                  date: selectedDate,
                })}
              >
                <Button variant="ghost">Volver a horarios</Button>
              </Link>
            </div>
            <VisitBookingFormSection
              selectedExperience={selectedExperience}
              selectedSlot={selectedSlot}
              bookingForm={bookingForm}
              setBookingForm={setBookingForm}
              bookingError={bookingError}
              redirectUrl={redirectUrl}
              bookingMutation={bookingMutation}
              handleSubmit={handleSubmit}
            />
          </div>
        </section>
      ) : null}

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
          <SectionHeading
            eyebrow="FAQ de visitas"
            title="Preguntas frecuentes"
          />
          <div className="mt-8 grid gap-4 lg:grid-cols-2">
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
      </section>
    </div>
  );
}
