import { type ChangeEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { cn, formatDate, slugify } from "../../lib/utils";
import type {
  BackofficeBooking,
  BackofficeBookingPayload,
  BackofficeExperience,
  BackofficeExperiencePayload,
} from "../../types/backoffice";
import {
  BackofficeBadge,
  BackofficeEmptyState,
  BackofficeField,
  BackofficeHero,
  BackofficeInput,
  BackofficeMessage,
  BackofficePanel,
  BackofficePanelHeader,
  BackofficeSectionCard,
  BackofficeSectionHeading,
  BackofficeSelect,
  BackofficeTextarea,
} from "./BackofficeUI";

const experienceTypeOptions = [
  { value: "winery_tour", label: "Tour por la bodega" },
  { value: "premium_tasting", label: "Cata premium" },
  { value: "harvest", label: "Experiencia de vendimia" },
  { value: "private_event", label: "Evento privado" },
  { value: "wine_pairing", label: "Maridaje con chef" },
];

const bookingStatusOptions = [
  { value: "confirmed", label: "Confirmada" },
  { value: "cancelled", label: "Cancelada" },
  { value: "completed", label: "Completada" },
  { value: "no_show", label: "No se presentó" },
];

interface ExperienceFormState {
  name: string;
  slug: string;
  experience_type: string;
  description: string;
  duration_minutes: string;
  price_per_person: string;
  min_guests: string;
  max_guests: string;
  includes_text: string;
  highlights_text: string;
  cover_image: string;
  gallery_images_text: string;
  cancellation_hours: string;
  is_active: boolean;
  is_featured: boolean;
}

interface BookingFormState {
  status: string;
  guest_count: string;
  special_requests: string;
  checked_in_at: string;
}

const emptyExperienceForm: ExperienceFormState = {
  name: "",
  slug: "",
  experience_type: "winery_tour",
  description: "",
  duration_minutes: "90",
  price_per_person: "0.00",
  min_guests: "1",
  max_guests: "12",
  includes_text: "",
  highlights_text: "",
  cover_image: "",
  gallery_images_text: "",
  cancellation_hours: "48",
  is_active: true,
  is_featured: false,
};

const emptyBookingForm: BookingFormState = {
  status: "confirmed",
  guest_count: "2",
  special_requests: "",
  checked_in_at: "",
};

function listToText(values: string[]) {
  return values.join("\n");
}

function textToList(rawValue: string) {
  return rawValue
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function toExperienceFormState(experience: BackofficeExperience): ExperienceFormState {
  return {
    name: experience.name,
    slug: experience.slug,
    experience_type: experience.experience_type,
    description: experience.description,
    duration_minutes: String(experience.duration_minutes),
    price_per_person: experience.price_per_person,
    min_guests: String(experience.min_guests),
    max_guests: String(experience.max_guests),
    includes_text: listToText(experience.includes),
    highlights_text: listToText(experience.highlights),
    cover_image: experience.cover_image,
    gallery_images_text: listToText(experience.gallery_images),
    cancellation_hours: String(experience.cancellation_hours),
    is_active: experience.is_active,
    is_featured: experience.is_featured,
  };
}

function toExperiencePayload(formState: ExperienceFormState): BackofficeExperiencePayload {
  return {
    name: formState.name,
    slug: formState.slug || undefined,
    experience_type: formState.experience_type,
    description: formState.description,
    duration_minutes: Number.parseInt(formState.duration_minutes, 10),
    price_per_person: formState.price_per_person,
    min_guests: Number.parseInt(formState.min_guests, 10),
    max_guests: Number.parseInt(formState.max_guests, 10),
    includes: textToList(formState.includes_text),
    highlights: textToList(formState.highlights_text),
    cover_image: formState.cover_image,
    gallery_images: textToList(formState.gallery_images_text),
    cancellation_hours: Number.parseInt(formState.cancellation_hours, 10),
    is_active: formState.is_active,
    is_featured: formState.is_featured,
  };
}

function toBookingFormState(booking: BackofficeBooking): BookingFormState {
  return {
    status: booking.status,
    guest_count: String(booking.guest_count),
    special_requests: booking.special_requests,
    checked_in_at: booking.checked_in_at ? booking.checked_in_at.slice(0, 16) : "",
  };
}

function toBookingPayload(formState: BookingFormState): BackofficeBookingPayload {
  return {
    status: formState.status,
    guest_count: Number.parseInt(formState.guest_count, 10),
    special_requests: formState.special_requests,
    checked_in_at: formState.checked_in_at ? new Date(formState.checked_in_at).toISOString() : null,
  };
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Sin fecha";
  }
  try {
    return new Intl.DateTimeFormat("es-AR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function VisitImage({ src, alt }: { src?: string | null; alt: string }) {
  const resolved = wineImageSrc(src);
  return (
    <img
      src={resolved}
      alt={alt}
      onError={applyWineImageFallback}
      className="h-24 w-24 rounded-[22px] object-cover"
    />
  );
}

export function BackofficeVisitsPage() {
  const queryClient = useQueryClient();
  const [selectedExperienceId, setSelectedExperienceId] = useState<string | null>(null);
  const [selectedBookingId, setSelectedBookingId] = useState<string | null>(null);
  const [isCreatingExperience, setIsCreatingExperience] = useState(false);
  const [experienceForm, setExperienceForm] = useState<ExperienceFormState>(emptyExperienceForm);
  const [bookingForm, setBookingForm] = useState<BookingFormState>(emptyBookingForm);
  const [bookingSearch, setBookingSearch] = useState("");
  const [bookingStatusFilter, setBookingStatusFilter] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<"success" | "danger">("success");

  const experiencesQuery = useQuery({
    queryKey: ["backoffice-visits-experiences"],
    queryFn: backofficeApi.visits.experiences.list,
  });

  const selectedExperienceQuery = useQuery({
    queryKey: ["backoffice-visits-experience-detail", selectedExperienceId],
    queryFn: () => backofficeApi.visits.experiences.detail(selectedExperienceId ?? ""),
    enabled: Boolean(selectedExperienceId),
  });

  const bookingsQuery = useQuery({
    queryKey: ["backoffice-visits-bookings", selectedExperienceId, bookingStatusFilter, bookingSearch],
    queryFn: () =>
      backofficeApi.visits.bookings.list({
        experience: selectedExperienceId ?? undefined,
        status: bookingStatusFilter || undefined,
        search: bookingSearch.trim() || undefined,
      }),
  });

  const slotsQuery = useQuery({
    queryKey: ["backoffice-visits-slots", selectedExperienceId],
    queryFn: () => backofficeApi.visits.slots.list({ experience: selectedExperienceId ?? undefined }),
    enabled: Boolean(selectedExperienceId),
  });

  const selectedBookingQuery = useQuery({
    queryKey: ["backoffice-visits-booking-detail", selectedBookingId],
    queryFn: () => backofficeApi.visits.bookings.detail(selectedBookingId ?? ""),
    enabled: Boolean(selectedBookingId),
  });

  const experiences = useMemo(
    () => experiencesQuery.data ?? [],
    [experiencesQuery.data],
  );
  const bookings = useMemo(() => bookingsQuery.data ?? [], [bookingsQuery.data]);
  const selectedExperience = useMemo(
    () => experiences.find((experience) => experience.id === selectedExperienceId) ?? null,
    [experiences, selectedExperienceId],
  );
  const selectedBooking = useMemo(
    () => bookings.find((booking) => booking.id === selectedBookingId) ?? null,
    [bookings, selectedBookingId],
  );
  const bookingSlots = useMemo(() => slotsQuery.data ?? [], [slotsQuery.data]);

  useEffect(() => {
    if (experiences.length === 0) {
      setSelectedExperienceId(null);
      setExperienceForm(emptyExperienceForm);
      return;
    }

    if (
      !isCreatingExperience &&
      (!selectedExperienceId || !experiences.some((experience) => experience.id === selectedExperienceId))
    ) {
      setSelectedExperienceId(experiences[0].id);
    }
  }, [experiences, isCreatingExperience, selectedExperienceId]);

  useEffect(() => {
    if (selectedExperienceQuery.data) {
      setExperienceForm(toExperienceFormState(selectedExperienceQuery.data));
    }
  }, [selectedExperienceQuery.data]);

  useEffect(() => {
    if (bookings.length === 0) {
      setSelectedBookingId(null);
      setBookingForm(emptyBookingForm);
      return;
    }

    if (!selectedBookingId || !bookings.some((booking) => booking.id === selectedBookingId)) {
      setSelectedBookingId(bookings[0].id);
    }
  }, [bookings, selectedBookingId]);

  useEffect(() => {
    if (selectedBookingQuery.data) {
      setBookingForm(toBookingFormState(selectedBookingQuery.data));
    }
  }, [selectedBookingQuery.data]);

  const saveExperienceMutation = useMutation({
    mutationFn: async () => {
      const payload = toExperiencePayload(experienceForm);
      if (selectedExperienceId) {
        return backofficeApi.visits.experiences.update(selectedExperienceId, payload);
      }
      return backofficeApi.visits.experiences.create(payload);
    },
    onSuccess: async (experience) => {
      setFeedback("Visita guardada correctamente.");
      setFeedbackTone("success");
      setIsCreatingExperience(false);
      setSelectedExperienceId(experience.id);
      setExperienceForm(toExperienceFormState(experience));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-experiences"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-bookings"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-slots"] }),
      ]);
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ detail?: string }>;
      setFeedbackTone("danger");
      setFeedback(
        axiosError.response?.data?.detail ?? "No pudimos guardar la visita seleccionada.",
      );
    },
  });

  const deleteExperienceMutation = useMutation({
    mutationFn: async () => {
      if (!selectedExperienceId) {
        return;
      }
      await backofficeApi.visits.experiences.remove(selectedExperienceId);
    },
    onSuccess: async () => {
      setFeedback("Visita eliminada.");
      setFeedbackTone("success");
      setIsCreatingExperience(false);
      setSelectedExperienceId(null);
      setExperienceForm(emptyExperienceForm);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-experiences"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-bookings"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-slots"] }),
      ]);
    },
    onError: () => {
      setFeedbackTone("danger");
      setFeedback("No pudimos eliminar la visita seleccionada.");
    },
  });

  const saveBookingMutation = useMutation({
    mutationFn: async () => {
      if (!selectedBookingId) {
        return;
      }
      return backofficeApi.visits.bookings.update(selectedBookingId, toBookingPayload(bookingForm));
    },
    onSuccess: async (booking) => {
      if (!booking) {
        return;
      }
      setFeedback("Reserva de visita actualizada.");
      setFeedbackTone("success");
      setBookingForm(toBookingFormState(booking));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-bookings"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-experiences"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-visits-slots"] }),
      ]);
    },
    onError: () => {
      setFeedbackTone("danger");
      setFeedback("No pudimos actualizar la reserva de visita.");
    },
  });

  function selectExperience(experience: BackofficeExperience | null) {
    setIsCreatingExperience(false);
    setSelectedExperienceId(experience?.id ?? null);
      setFeedback(null);
      if (!experience) {
        setExperienceForm(emptyExperienceForm);
        return;
    }
    setExperienceForm(toExperienceFormState(experience));
  }

  function selectBooking(booking: BackofficeBooking | null) {
    setSelectedBookingId(booking?.id ?? null);
    setFeedback(null);
    if (!booking) {
      setBookingForm(emptyBookingForm);
      return;
    }
    setBookingForm(toBookingFormState(booking));
  }

  function handleExperienceField(field: keyof ExperienceFormState) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const value = event.target instanceof HTMLInputElement && event.target.type === "checkbox"
        ? event.target.checked
        : event.target.value;
      setExperienceForm((current) => {
        const next = { ...current, [field]: value } as ExperienceFormState;
        if (field === "name" && (!current.slug || current.slug === slugify(current.name))) {
          next.slug = slugify(String(value));
        }
        return next;
      });
    };
  }

  function handleBookingField(field: keyof BookingFormState) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const value = event.target.value;
      setBookingForm((current) => ({ ...current, [field]: value }));
    };
  }

  function clearFilters() {
    setBookingSearch("");
    setBookingStatusFilter("");
  }

  function createNewExperience() {
    setIsCreatingExperience(true);
    setSelectedExperienceId(null);
    setExperienceForm(emptyExperienceForm);
    setFeedback(null);
  }

  return (
    <div className="space-y-8">
      <BackofficeHero
        eyebrow="Visitas y eventos"
        title="Gestioná experiencias, fechas y reservas desde el backoffice propio."
        description="Este módulo deja visible qué visitas existen, cuál es su contenido base y cómo van cambiando las reservas reales sin tener que entrar a Django admin."
        actions={
          <>
            <Button onClick={createNewExperience}>Nueva visita</Button>
          </>
        }
        stats={[
          { label: "Visitas activas", value: experiences.filter((experience) => experience.is_active).length },
          { label: "Destacadas", value: experiences.filter((experience) => experience.is_featured).length },
          { label: "Reservas visibles", value: bookings.length },
          { label: "Primer evento", value: bookings[0]?.confirmation_code ?? "Sin reservas" },
        ]}
      />

      {feedback ? <BackofficeMessage tone={feedbackTone}>{feedback}</BackofficeMessage> : null}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="space-y-4">
          {experiencesQuery.isLoading ? <p className="text-burgundy-700">Cargando visitas...</p> : null}
          {experiencesQuery.isError ? (
            <BackofficeMessage tone="danger">No pudimos cargar las experiencias de visita.</BackofficeMessage>
          ) : null}
          {experiences.length > 0 ? (
            experiences.map((experience) => (
              <button
                key={experience.id}
                type="button"
                onClick={() => selectExperience(experience)}
                className={cn(
                  "w-full rounded-[28px] border p-5 text-left shadow-velvet transition",
                  selectedExperienceId === experience.id
                    ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                    : "border-burgundy-100 bg-white text-burgundy-950",
                )}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="flex items-start gap-4">
                    <VisitImage src={experience.cover_image} alt={experience.name} />
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                        {experience.slug}
                      </p>
                      <h4 className="mt-2 font-serif text-2xl">{experience.name}</h4>
                      <p className="mt-2 text-sm text-current/70">{experience.description}</p>
                    </div>
                  </div>
                  <div className="text-left text-sm text-current/70 md:text-right">
                    <p>{experienceTypeOptions.find((option) => option.value === experience.experience_type)?.label ?? experience.experience_type}</p>
                    <p className="mt-2">
                      {experience.duration_minutes} min · {experience.min_guests}-{experience.max_guests} personas
                    </p>
                    <p className="mt-2">{experience.bookings_count} reservas</p>
                  </div>
                </div>
              </button>
            ))
          ) : (
            <BackofficeEmptyState
              title="Todavía no hay visitas cargadas"
              description="Podés crear la primera experiencia desde el panel de la derecha."
            />
          )}
        </section>

        <BackofficePanel>
          <BackofficePanelHeader
            eyebrow="Editor de visita"
            title={selectedExperience ? selectedExperience.name : "Nueva experiencia"}
            description="Acá se ajusta la propuesta comercial visible para el equipo y para los clientes."
            actions={
              <>
                {selectedExperienceId ? (
                  <Button
                    variant="ghost"
                    onClick={() => deleteExperienceMutation.mutate()}
                    disabled={deleteExperienceMutation.isPending}
                  >
                    Eliminar
                  </Button>
                ) : null}
                <Button
                  onClick={() => saveExperienceMutation.mutate()}
                  disabled={saveExperienceMutation.isPending}
                >
                  Guardar visita
                </Button>
              </>
            }
          />

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <BackofficeField label="Nombre">
              <BackofficeInput value={experienceForm.name} onChange={handleExperienceField("name")} />
            </BackofficeField>
            <BackofficeField label="Slug">
              <BackofficeInput value={experienceForm.slug} onChange={handleExperienceField("slug")} />
            </BackofficeField>
            <BackofficeField label="Tipo">
              <BackofficeSelect
                value={experienceForm.experience_type}
                onChange={handleExperienceField("experience_type")}
              >
                {experienceTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </BackofficeSelect>
            </BackofficeField>
            <BackofficeField label="Duración (min)">
              <BackofficeInput
                type="number"
                value={experienceForm.duration_minutes}
                onChange={handleExperienceField("duration_minutes")}
              />
            </BackofficeField>
            <BackofficeField label="Precio por persona">
              <BackofficeInput
                type="number"
                step="0.01"
                value={experienceForm.price_per_person}
                onChange={handleExperienceField("price_per_person")}
              />
            </BackofficeField>
            <BackofficeField label="Mínimo de invitados">
              <BackofficeInput
                type="number"
                value={experienceForm.min_guests}
                onChange={handleExperienceField("min_guests")}
              />
            </BackofficeField>
            <BackofficeField label="Máximo de invitados">
              <BackofficeInput
                type="number"
                value={experienceForm.max_guests}
                onChange={handleExperienceField("max_guests")}
              />
            </BackofficeField>
            <BackofficeField label="Horas de cancelación">
              <BackofficeInput
                type="number"
                value={experienceForm.cancellation_hours}
                onChange={handleExperienceField("cancellation_hours")}
              />
            </BackofficeField>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <BackofficeField label="Portada">
              <BackofficeInput
                value={experienceForm.cover_image}
                onChange={handleExperienceField("cover_image")}
                placeholder="https://..."
              />
            </BackofficeField>
            <BackofficeField label="Galería">
              <BackofficeTextarea
                value={experienceForm.gallery_images_text}
                onChange={handleExperienceField("gallery_images_text")}
                placeholder="Una URL por línea"
              />
            </BackofficeField>
            <BackofficeField label="Incluye">
              <BackofficeTextarea
                value={experienceForm.includes_text}
                onChange={handleExperienceField("includes_text")}
                placeholder="Una línea por beneficio o elemento incluido"
              />
            </BackofficeField>
            <BackofficeField label="Highlights">
              <BackofficeTextarea
                value={experienceForm.highlights_text}
                onChange={handleExperienceField("highlights_text")}
                placeholder="Una línea por highlight"
              />
            </BackofficeField>
          </div>

          <BackofficeField label="Descripción" className="mt-6">
            <BackofficeTextarea
              value={experienceForm.description}
              onChange={handleExperienceField("description")}
              placeholder="Explicación comercial y operativa de la experiencia"
            />
          </BackofficeField>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <BackofficeSectionCard className="space-y-4">
              <BackofficeSectionHeading
                eyebrow="Publicación"
                title="Visibilidad"
                description="Usá estos switches para controlar qué visita ve el equipo y qué queda destacada."
              />
              <div className="grid gap-3 md:grid-cols-2">
                <BackofficeBadge tone={experienceForm.is_active ? "success" : "soft"}>
                  {experienceForm.is_active ? "Activa" : "Inactiva"}
                </BackofficeBadge>
                <BackofficeBadge tone={experienceForm.is_featured ? "gold" : "soft"}>
                  {experienceForm.is_featured ? "Destacada" : "Normal"}
                </BackofficeBadge>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <label
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-[24px] border px-4 py-4 transition",
                    experienceForm.is_active
                      ? "border-burgundy-300 bg-white text-burgundy-950"
                      : "border-burgundy-100 bg-cream-50 text-burgundy-900",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={experienceForm.is_active}
                    onChange={handleExperienceField("is_active")}
                    className="mt-1 h-4 w-4 accent-burgundy-900"
                  />
                  <span>
                    <span className="block text-sm font-semibold">Activa</span>
                    <span className="mt-1 block text-sm leading-6 text-current/70">
                      La visita aparece disponible para gestión interna.
                    </span>
                  </span>
                </label>
                <label
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-[24px] border px-4 py-4 transition",
                    experienceForm.is_featured
                      ? "border-burgundy-300 bg-white text-burgundy-950"
                      : "border-burgundy-100 bg-cream-50 text-burgundy-900",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={experienceForm.is_featured}
                    onChange={handleExperienceField("is_featured")}
                    className="mt-1 h-4 w-4 accent-burgundy-900"
                  />
                  <span>
                    <span className="block text-sm font-semibold">Destacada</span>
                    <span className="mt-1 block text-sm leading-6 text-current/70">
                      Sube la experiencia a módulos de foco o recomendaciones.
                    </span>
                  </span>
                </label>
              </div>
            </BackofficeSectionCard>

            <BackofficeSectionCard className="space-y-4">
              <BackofficeSectionHeading
                eyebrow="Estado actual"
                title="Señales operativas"
                description="Lo que el equipo necesita para entender el lugar de esta visita dentro del calendario."
              />
              <div className="grid gap-3 text-sm text-burgundy-800">
                <p>Reservas asociadas: {selectedExperience?.bookings_count ?? 0}</p>
                <p>Turnos cargados: {selectedExperience?.slots_count ?? 0}</p>
                <p>Portada: {experienceForm.cover_image ? "Cargada" : "Sin imagen"}</p>
              </div>
            </BackofficeSectionCard>
          </div>
        </BackofficePanel>
      </div>

      <BackofficePanel>
        <BackofficePanelHeader
          eyebrow="Reservas"
          title="Eventos y reservas de visita"
          description="Cada reserva es el evento real que conviene revisar, reasignar o cerrar desde el panel."
          actions={
            <>
              <Button variant="ghost" onClick={clearFilters}>
                Limpiar filtros
              </Button>
            </>
          }
        />

        <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_240px]">
          <BackofficeField label="Buscar reservas" hint="Cliente, código, experiencia o texto libre">
            <BackofficeInput
              value={bookingSearch}
              onChange={(event) => setBookingSearch(event.target.value)}
              placeholder="codigo, email o nombre"
            />
          </BackofficeField>
          <BackofficeField label="Estado">
            <BackofficeSelect
              value={bookingStatusFilter}
              onChange={(event) => setBookingStatusFilter(event.target.value)}
            >
              <option value="">Todas</option>
              {bookingStatusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </BackofficeSelect>
          </BackofficeField>
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <section className="space-y-4">
            {bookingsQuery.isLoading ? <p className="text-burgundy-700">Cargando reservas...</p> : null}
            {bookingsQuery.isError ? (
              <BackofficeMessage tone="danger">No pudimos cargar las reservas de visita.</BackofficeMessage>
            ) : null}
            {bookings.length > 0 ? (
              bookings.map((booking) => (
                <button
                  key={booking.id}
                  type="button"
                  onClick={() => selectBooking(booking)}
                  className={cn(
                    "w-full rounded-[28px] border p-5 text-left shadow-velvet transition",
                    selectedBookingId === booking.id
                      ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                      : "border-burgundy-100 bg-white text-burgundy-950",
                  )}
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                        {booking.confirmation_code}
                      </p>
                      <h4 className="mt-2 font-serif text-2xl">{booking.customer_name}</h4>
                      <p className="mt-2 text-sm text-current/70">
                        {booking.experience_name} · {booking.guest_count} invitados
                      </p>
                    </div>
                    <div className="text-left text-sm text-current/70 md:text-right">
                      <p>{booking.status}</p>
                      <p className="mt-2">{formatDate(booking.created_at)}</p>
                    </div>
                  </div>
                </button>
              ))
            ) : (
              <BackofficeEmptyState
                title="No hay reservas con esos filtros"
                description="Probá cambiando el texto de búsqueda o volviendo a un estado más general."
              />
            )}
          </section>

          <BackofficePanel className="bg-white">
            <BackofficePanelHeader
              eyebrow="Detalle de reserva"
              title={selectedBooking?.confirmation_code ?? "Sin selección"}
              description="Editá el estado operativo de una reserva real sin tocar la estructura de la visita."
              actions={
                <Button onClick={() => saveBookingMutation.mutate()} disabled={saveBookingMutation.isPending}>
                  Guardar reserva
                </Button>
              }
            />

            {selectedBooking ? (
              <div className="mt-6 space-y-6">
                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {selectedBooking.experience_name}
                  </p>
                  <h4 className="mt-2 font-serif text-3xl text-burgundy-950">
                    {selectedBooking.customer_name}
                  </h4>
                  <p className="mt-3 text-sm text-burgundy-700">
                    {selectedBooking.customer_email} · {selectedBooking.slot_date} ·{" "}
                    {selectedBooking.slot_start_time} - {selectedBooking.slot_end_time}
                  </p>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <BackofficeField label="Estado">
                    <BackofficeSelect value={bookingForm.status} onChange={handleBookingField("status")}>
                      {bookingStatusOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </BackofficeSelect>
                  </BackofficeField>
                  <BackofficeField label="Cantidad de invitados">
                    <BackofficeInput
                      type="number"
                      value={bookingForm.guest_count}
                      onChange={handleBookingField("guest_count")}
                    />
                  </BackofficeField>
                  <BackofficeField label="Check-in">
                    <BackofficeInput
                      type="datetime-local"
                      value={bookingForm.checked_in_at}
                      onChange={handleBookingField("checked_in_at")}
                    />
                  </BackofficeField>
                  <BackofficeField label="Fecha de creación">
                    <BackofficeInput value={formatDateTime(selectedBooking.created_at)} readOnly />
                  </BackofficeField>
                </div>

                <BackofficeField label="Pedidos especiales">
                  <BackofficeTextarea
                    value={bookingForm.special_requests}
                    onChange={handleBookingField("special_requests")}
                  />
                </BackofficeField>

                <div className="grid gap-4 md:grid-cols-2">
                  <BackofficeSectionCard>
                    <BackofficeSectionHeading
                      eyebrow="Tiempo"
                      title="Datos de agenda"
                      description="La reserva apunta a un turno concreto con fecha y franja horaria."
                    />
                    <div className="mt-4 space-y-2 text-sm text-burgundy-800">
                      <p>Fecha: {selectedBooking.slot_date}</p>
                      <p>Horario: {selectedBooking.slot_start_time} - {selectedBooking.slot_end_time}</p>
                      <p>Tipo: {selectedBooking.experience_type}</p>
                    </div>
                  </BackofficeSectionCard>

                  <BackofficeSectionCard>
                    <BackofficeSectionHeading
                      eyebrow="Marcadores"
                      title="Estado automático"
                      description="Indicadores útiles para saber si la reserva ya recibió recordatorios."
                    />
                    <div className="mt-4 space-y-2 text-sm text-burgundy-800">
                      <p>Recordatorio 24h: {selectedBooking.reminder_24h_sent ? "Enviado" : "Pendiente"}</p>
                      <p>Recordatorio 1h: {selectedBooking.reminder_1h_sent ? "Enviado" : "Pendiente"}</p>
                      <p>Check-in: {selectedBooking.checked_in_at ? formatDateTime(selectedBooking.checked_in_at) : "No registrado"}</p>
                    </div>
                  </BackofficeSectionCard>
                </div>
              </div>
            ) : (
              <div className="mt-6">
                <BackofficeEmptyState
                  title="Seleccioná una reserva"
                  description="Podés revisar cualquier evento de visita desde la lista de la izquierda."
                />
              </div>
            )}
          </BackofficePanel>
        </div>
      </BackofficePanel>

      <BackofficePanel>
        <BackofficePanelHeader
          eyebrow="Turnos"
          title="Slots de la experiencia"
          description="Los turnos siguen viviendo como estructura operativa de base. Si luego querés, los hacemos editables con la misma UI."
        />
        <div className="mt-6">
          {slotsQuery.isLoading ? <p className="text-burgundy-700">Cargando turnos...</p> : null}
          {slotsQuery.isError ? (
            <BackofficeMessage tone="danger">No pudimos cargar los turnos de esta experiencia.</BackofficeMessage>
          ) : null}
          {bookingSlots.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {bookingSlots.map((slot) => (
                <article
                  key={slot.id}
                  className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800"
                >
                  <p className="font-semibold text-burgundy-950">
                    {slot.date} · {slot.start_time}
                  </p>
                  <p className="mt-2">{slot.experience_name}</p>
                </article>
              ))}
            </div>
          ) : selectedExperienceId ? (
            <BackofficeEmptyState
              title="No hay turnos cargados"
              description="Esta experiencia todavía no tiene slots asociados."
            />
          ) : (
            <BackofficeEmptyState
              title="Seleccioná una visita"
              description="Los turnos se muestran cuando elegís una experiencia."
            />
          )}
        </div>
      </BackofficePanel>
    </div>
  );
}
