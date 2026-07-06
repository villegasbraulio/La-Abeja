import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import { applyWineImageFallback, resolveAssetUrl } from "../../lib/assets";
import { cn, formatARS, formatDate, slugify } from "../../lib/utils";
import type {
  BackofficeCategory,
  BackofficeVarietal,
  BackofficeWineDetail,
  BackofficeWineImage,
  BackofficeWinePayload,
} from "../../types/backoffice";
import {
  BackofficeBadge,
  BackofficeCheckboxCard,
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

interface WineFormState {
  name: string;
  slug: string;
  sku: string;
  category: string;
  varietal: string;
  vintage_year: string;
  price: string;
  compare_at_price: string;
  cost_price: string;
  stock: string;
  low_stock_threshold: string;
  alcohol_percentage: string;
  serving_temperature_min: string;
  serving_temperature_max: string;
  ageing_months: string;
  ageing_type: string;
  tannins: string;
  acidity: string;
  body: string;
  sweetness: string;
  fruit_intensity: string;
  description: string;
  tasting_notes: string;
  pairing_suggestions_text: string;
  winemaker_notes: string;
  awards_text: string;
  blend_varietals_text: string;
  meta_title: string;
  meta_description: string;
  is_featured: boolean;
  is_active: boolean;
  is_limited_edition: boolean;
  images: BackofficeWineImage[];
}

type WineTextField = keyof Omit<
  WineFormState,
  "images" | "is_featured" | "is_active" | "is_limited_edition"
>;

const pricingFieldConfig: Array<{
  field: WineTextField;
  label: string;
  hint: string;
  inputType?: "text" | "number";
  step?: string;
}> = [
  { field: "price", label: "Precio actual", hint: "Precio principal visible en tienda.", inputType: "number", step: "0.01" },
  {
    field: "compare_at_price",
    label: "Precio anterior",
    hint: "Útil para mostrar descuento o precio tachado.",
    inputType: "number",
    step: "0.01",
  },
  { field: "cost_price", label: "Costo", hint: "Base para margen bruto.", inputType: "number", step: "0.01" },
  { field: "stock", label: "Stock", hint: "Botellas disponibles para vender.", inputType: "number" },
  {
    field: "low_stock_threshold",
    label: "Umbral stock bajo",
    hint: "Avisa cuando el inventario cae por debajo de este punto.",
    inputType: "number",
  },
  { field: "alcohol_percentage", label: "Alcohol %", hint: "Graduación alcohólica.", inputType: "number", step: "0.1" },
];

const serviceFieldConfig: Array<{
  field: WineTextField;
  label: string;
  hint: string;
}> = [
  { field: "serving_temperature_min", label: "Temp. mínima", hint: "Temperatura sugerida de servicio." },
  { field: "serving_temperature_max", label: "Temp. máxima", hint: "Límite superior de servicio." },
  { field: "ageing_months", label: "Meses de crianza", hint: "Tiempo total de evolución o guarda." },
  { field: "tannins", label: "Taninos", hint: "Escala interna de 0 a 100." },
  { field: "acidity", label: "Acidez", hint: "Escala interna de 0 a 100." },
  { field: "body", label: "Cuerpo", hint: "Escala interna de 0 a 100." },
  { field: "sweetness", label: "Dulzor", hint: "Escala interna de 0 a 100." },
  { field: "fruit_intensity", label: "Fruta", hint: "Escala interna de 0 a 100." },
];

const wineFlags = [
  {
    field: "is_active" as const,
    label: "Publicado en tienda",
    description: "Determina si el vino aparece disponible para clientes en el storefront.",
  },
  {
    field: "is_featured" as const,
    label: "Destacado en home",
    description: "Se usa para priorizarlo en home, curadurías y recomendaciones comerciales.",
  },
  {
    field: "is_limited_edition" as const,
    label: "Edición limitada",
    description: "Marca el vino como partida corta o lanzamiento especial.",
  },
];

const ageingOptions = [
  { value: "oak", label: "Roble" },
  { value: "stainless", label: "Acero inoxidable" },
  { value: "cement", label: "Hormigón" },
  { value: "amphora", label: "Ánfora" },
];

const emptyWineForm: WineFormState = {
  name: "",
  slug: "",
  sku: "",
  category: "",
  varietal: "",
  vintage_year: "2024",
  price: "0.00",
  compare_at_price: "",
  cost_price: "0.00",
  stock: "0",
  low_stock_threshold: "6",
  alcohol_percentage: "14.0",
  serving_temperature_min: "15",
  serving_temperature_max: "18",
  ageing_months: "0",
  ageing_type: "oak",
  tannins: "50",
  acidity: "50",
  body: "50",
  sweetness: "20",
  fruit_intensity: "50",
  description: "",
  tasting_notes: "",
  pairing_suggestions_text: "",
  winemaker_notes: "",
  awards_text: "",
  blend_varietals_text: "",
  meta_title: "",
  meta_description: "",
  is_featured: false,
  is_active: true,
  is_limited_edition: false,
  images: [
    {
      url: "",
      alt_text: "",
      is_primary: true,
      order: 0,
    },
  ],
};

const stockStateMeta = {
  healthy: { label: "Stock saludable", tone: "success" as const },
  low: { label: "Stock bajo", tone: "warning" as const },
  out: { label: "Sin stock", tone: "dark" as const },
};

function serializeAwards(awards: Array<Record<string, unknown>>) {
  return awards
    .map((award) => `${String(award.award ?? "")} | ${String(award.score ?? "")} | ${String(award.year ?? "")}`)
    .filter((line) => !line.startsWith(" |"))
    .join("\n");
}

function serializeBlends(blends: Array<Record<string, unknown>>) {
  return blends
    .map((blend) => `${String(blend.varietal ?? "")}: ${String(blend.percentage ?? "")}`)
    .filter((line) => !line.startsWith(":"))
    .join("\n");
}

function parseLineList(rawValue: string) {
  return rawValue
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function parseAwards(rawValue: string) {
  return parseLineList(rawValue).map((line) => {
    const [award = "", score = "", year = ""] = line.split("|").map((segment) => segment.trim());
    return {
      award,
      score: Number.parseInt(score, 10) || 0,
      year: Number.parseInt(year, 10) || 0,
    };
  });
}

function parseBlends(rawValue: string) {
  return parseLineList(rawValue).map((line) => {
    const [varietal = "", percentage = "0"] = line.split(":").map((segment) => segment.trim());
    return {
      varietal,
      percentage: Number.parseInt(percentage, 10) || 0,
    };
  });
}

function toWineFormState(wine: BackofficeWineDetail): WineFormState {
  return {
    name: wine.name,
    slug: wine.slug,
    sku: wine.sku,
    category: String(wine.category),
    varietal: String(wine.varietal),
    vintage_year: String(wine.vintage_year),
    price: wine.price,
    compare_at_price: wine.compare_at_price ?? "",
    cost_price: wine.cost_price,
    stock: String(wine.stock),
    low_stock_threshold: String(wine.low_stock_threshold),
    alcohol_percentage: wine.alcohol_percentage,
    serving_temperature_min: String(wine.serving_temperature_min),
    serving_temperature_max: String(wine.serving_temperature_max),
    ageing_months: String(wine.ageing_months),
    ageing_type: wine.ageing_type,
    tannins: String(wine.tannins),
    acidity: String(wine.acidity),
    body: String(wine.body),
    sweetness: String(wine.sweetness),
    fruit_intensity: String(wine.fruit_intensity),
    description: wine.description,
    tasting_notes: wine.tasting_notes,
    pairing_suggestions_text: wine.pairing_suggestions.join("\n"),
    winemaker_notes: wine.winemaker_notes,
    awards_text: serializeAwards(wine.awards),
    blend_varietals_text: serializeBlends(wine.blend_varietals),
    meta_title: wine.meta_title,
    meta_description: wine.meta_description,
    is_featured: wine.is_featured,
    is_active: wine.is_active,
    is_limited_edition: wine.is_limited_edition,
    images:
      wine.images.length > 0
        ? wine.images
        : [{ url: "", alt_text: "", is_primary: true, order: 0 }],
  };
}

function toWinePayload(formState: WineFormState): BackofficeWinePayload {
  return {
    name: formState.name,
    slug: formState.slug || undefined,
    sku: formState.sku,
    category: Number.parseInt(formState.category, 10),
    varietal: Number.parseInt(formState.varietal, 10),
    vintage_year: Number.parseInt(formState.vintage_year, 10),
    price: formState.price,
    compare_at_price: formState.compare_at_price ? formState.compare_at_price : null,
    cost_price: formState.cost_price,
    stock: Number.parseInt(formState.stock, 10),
    low_stock_threshold: Number.parseInt(formState.low_stock_threshold, 10),
    alcohol_percentage: formState.alcohol_percentage,
    serving_temperature_min: Number.parseInt(formState.serving_temperature_min, 10),
    serving_temperature_max: Number.parseInt(formState.serving_temperature_max, 10),
    ageing_months: Number.parseInt(formState.ageing_months, 10),
    ageing_type: formState.ageing_type,
    tannins: Number.parseInt(formState.tannins, 10),
    acidity: Number.parseInt(formState.acidity, 10),
    body: Number.parseInt(formState.body, 10),
    sweetness: Number.parseInt(formState.sweetness, 10),
    fruit_intensity: Number.parseInt(formState.fruit_intensity, 10),
    description: formState.description,
    tasting_notes: formState.tasting_notes,
    pairing_suggestions: parseLineList(formState.pairing_suggestions_text),
    winemaker_notes: formState.winemaker_notes,
    awards: parseAwards(formState.awards_text),
    blend_varietals: parseBlends(formState.blend_varietals_text),
    meta_title: formState.meta_title,
    meta_description: formState.meta_description,
    is_featured: formState.is_featured,
    is_active: formState.is_active,
    is_limited_edition: formState.is_limited_edition,
    images: formState.images
      .filter((image) => image.url.trim().length > 0)
      .map((image, index) => ({
        ...image,
        order: index,
      })),
  };
}

function WineThumbnail({
  src,
  name,
  className,
}: {
  src?: string | null;
  name: string;
  className?: string;
}) {
  const resolvedSrc = resolveAssetUrl(src);
  if (resolvedSrc) {
    return (
      <img
        src={resolvedSrc}
        alt={name}
        onError={applyWineImageFallback}
        className={cn("object-cover", className)}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center bg-[radial-gradient(circle_at_top_left,rgba(200,169,110,0.28),transparent_35%),linear-gradient(160deg,#722F37_0%,#420d15_100%)] text-lg font-serif text-cream-50",
        className,
      )}
      aria-label={`Sin imagen para ${name}`}
    >
      {name.charAt(0).toUpperCase() || "V"}
    </div>
  );
}

function WineMetric({
  label,
  value,
  inverted = false,
}: {
  label: string;
  value: string;
  inverted?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-3",
        inverted
          ? "border-white/10 bg-white/10 text-cream-50"
          : "border-burgundy-100 bg-white text-burgundy-950",
      )}
    >
      <p className={cn("text-[11px] font-semibold uppercase tracking-[0.16em]", inverted ? "text-cream-100/70" : "text-burgundy-500")}>
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold">{value}</p>
    </div>
  );
}

export function WinesPage() {
  const queryClient = useQueryClient();
  const [selectedWineId, setSelectedWineId] = useState<string | null>(null);
  const [formState, setFormState] = useState<WineFormState>(emptyWineForm);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [varietalFilter, setVarietalFilter] = useState<string>("");

  const categoriesQuery = useQuery({
    queryKey: ["backoffice-categories"],
    queryFn: backofficeApi.categories.list,
  });
  const varietalsQuery = useQuery({
    queryKey: ["backoffice-varietals"],
    queryFn: backofficeApi.varietals.list,
  });
  const winesQuery = useQuery({
    queryKey: ["backoffice-wines", search, categoryFilter, varietalFilter],
    queryFn: () =>
      backofficeApi.wines.list({
        search: search || undefined,
        category: categoryFilter ? Number.parseInt(categoryFilter, 10) : null,
        varietal: varietalFilter ? Number.parseInt(varietalFilter, 10) : null,
      }),
  });
  const selectedWineQuery = useQuery({
    queryKey: ["backoffice-wine-detail", selectedWineId],
    queryFn: () => backofficeApi.wines.detail(selectedWineId ?? ""),
    enabled: selectedWineId !== null,
  });

  useEffect(() => {
    if (!selectedWineQuery.data) {
      return;
    }
    setFormState(toWineFormState(selectedWineQuery.data));
  }, [selectedWineQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toWinePayload(formState);
      if (selectedWineId) {
        return backofficeApi.wines.update(selectedWineId, payload);
      }
      return backofficeApi.wines.create(payload);
    },
    onSuccess: async (wine) => {
      setFeedback("Vino guardado correctamente.");
      setSelectedWineId(wine.id);
      setFormState(toWineFormState(wine));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["backoffice-wines"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-dashboard"] }),
      ]);
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ detail?: string }>;
      setFeedback(
        axiosError.response?.data?.detail ?? "No pudimos guardar este vino en el backoffice.",
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!selectedWineId) {
        return;
      }
      await backofficeApi.wines.remove(selectedWineId);
    },
    onSuccess: async () => {
      setFeedback("Vino eliminado.");
      setSelectedWineId(null);
      setFormState(emptyWineForm);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["backoffice-wines"] }),
        queryClient.invalidateQueries({ queryKey: ["backoffice-dashboard"] }),
      ]);
    },
    onError: () => {
      setFeedback("No pudimos eliminar el vino seleccionado.");
    },
  });

  const wines = useMemo(() => winesQuery.data?.results ?? [], [winesQuery.data?.results]);
  const selectedWinePreview = useMemo(
    () => wines.find((wine) => wine.id === selectedWineId) ?? null,
    [selectedWineId, wines],
  );
  const currentWineSummary = selectedWineQuery.data ?? selectedWinePreview;

  const visibleWinesCount = winesQuery.data?.count ?? wines.length;
  const activeWinesCount = wines.filter((wine) => wine.is_active).length;
  const featuredWinesCount = wines.filter((wine) => wine.is_featured).length;
  const sensitiveWinesCount = wines.filter((wine) => wine.stock_state !== "healthy").length;

  function resetEditor() {
    setSelectedWineId(null);
    setFormState(emptyWineForm);
    setFeedback(null);
  }

  function clearFilters() {
    setSearch("");
    setCategoryFilter("");
    setVarietalFilter("");
  }

  function selectWine(wineId: string) {
    setSelectedWineId(wineId);
    setFeedback(null);
  }

  function handleTextInput(field: WineTextField) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const value = event.target.value;
      setFormState((current) => {
        const nextState = { ...current, [field]: value };
        if (field === "name" && (!current.slug || current.slug === slugify(current.name))) {
          nextState.slug = slugify(value);
        }
        return nextState;
      });
    };
  }

  function handleBooleanChange(field: "is_featured" | "is_active" | "is_limited_edition") {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const value = event.target.checked;
      setFormState((current) => ({ ...current, [field]: value }));
    };
  }

  function updateImage(index: number, partial: Partial<BackofficeWineImage>) {
    setFormState((current) => ({
      ...current,
      images: current.images.map((image, imageIndex) =>
        imageIndex === index ? { ...image, ...partial } : image,
      ),
    }));
  }

  function markPrimaryImage(index: number) {
    setFormState((current) => ({
      ...current,
      images: current.images.map((image, imageIndex) => ({
        ...image,
        is_primary: imageIndex === index,
      })),
    }));
  }

  function removeImage(index: number) {
    setFormState((current) => {
      const removedImage = current.images[index];
      const nextImages = current.images.filter((_, imageIndex) => imageIndex !== index);

      if (nextImages.length === 0) {
        return {
          ...current,
          images: [{ url: "", alt_text: "", is_primary: true, order: 0 }],
        };
      }

      const shouldAssignFirstAsPrimary =
        removedImage?.is_primary || !nextImages.some((image) => image.is_primary);

      return {
        ...current,
        images: nextImages.map((image, imageIndex) => ({
          ...image,
          is_primary: shouldAssignFirstAsPrimary ? imageIndex === 0 : image.is_primary,
          order: imageIndex,
        })),
      };
    });
  }

  function addImage() {
    setFormState((current) => ({
      ...current,
      images: [
        ...current.images,
        {
          url: "",
          alt_text: "",
          is_primary: current.images.length === 0,
          order: current.images.length,
        },
      ],
    }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    saveMutation.mutate();
  }

  const hasActiveFilters = Boolean(search || categoryFilter || varietalFilter);

  return (
    <div className="space-y-8">
      <BackofficeHero
        eyebrow="Gestión comercial del catálogo"
        title="Vinos"
        description="Inventario, precios, contenido, imágenes y SEO."
        actions={
          <Button variant="ghost" onClick={resetEditor}>
            Nuevo vino
          </Button>
        }
        stats={[
          { label: "Vinos visibles", value: visibleWinesCount },
          { label: "Publicados", value: activeWinesCount },
          { label: "Stock sensible", value: sensitiveWinesCount },
          { label: "Destacados", value: featuredWinesCount },
        ]}
      />

      <BackofficePanel>
        <BackofficePanelHeader
          eyebrow="Búsqueda y filtros"
          title="Encontrá rápido el vino que querés editar"
          description="Nombre, SKU, categoría o varietal."
          actions={
            hasActiveFilters ? (
              <Button type="button" variant="ghost" onClick={clearFilters}>
                Limpiar filtros
              </Button>
            ) : null
          }
        />

        <div className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_0.9fr_0.9fr]">
          <BackofficeField label="Buscar por nombre o SKU">
            <BackofficeInput
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Ej. Reserva, Gran Corte, LAB-MALBEC..."
            />
          </BackofficeField>

          <BackofficeField label="Categoría">
            <BackofficeSelect
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">Todas las categorías</option>
              {(categoriesQuery.data ?? []).map((category: BackofficeCategory) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </BackofficeSelect>
          </BackofficeField>

          <BackofficeField label="Varietal">
            <BackofficeSelect
              value={varietalFilter}
              onChange={(event) => setVarietalFilter(event.target.value)}
            >
              <option value="">Todos los varietales</option>
              {(varietalsQuery.data ?? []).map((varietal: BackofficeVarietal) => (
                <option key={varietal.id} value={varietal.id}>
                  {varietal.name}
                </option>
              ))}
            </BackofficeSelect>
          </BackofficeField>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <BackofficeBadge tone="soft">{visibleWinesCount} resultados</BackofficeBadge>
          {categoryFilter ? (
            <BackofficeBadge tone="gold">
              {(categoriesQuery.data ?? []).find((item) => String(item.id) === categoryFilter)?.name ??
                "Categoría filtrada"}
            </BackofficeBadge>
          ) : null}
          {varietalFilter ? (
            <BackofficeBadge tone="gold">
              {(varietalsQuery.data ?? []).find((item) => String(item.id) === varietalFilter)?.name ??
                "Varietal filtrado"}
            </BackofficeBadge>
          ) : null}
          {search ? <BackofficeBadge tone="gold">Búsqueda: {search}</BackofficeBadge> : null}
        </div>
      </BackofficePanel>

      <div className="grid items-start gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <BackofficePanel>
          <BackofficePanelHeader
            eyebrow="Inventario visible"
            title="Listado de vinos"
            description="Precio, estado, margen, stock y visibilidad."
          />

          <div className="mt-6 space-y-4">
            {winesQuery.isLoading ? <p className="text-burgundy-700">Cargando vinos...</p> : null}

            {winesQuery.isError ? (
              <BackofficeMessage>
                No pudimos cargar los vinos con esos filtros por ahora.
              </BackofficeMessage>
            ) : null}

            {!winesQuery.isLoading && !winesQuery.isError && wines.length === 0 ? (
              <BackofficeEmptyState
                title="No encontramos vinos con esos filtros."
                description="Probá limpiar la búsqueda o crear una nueva etiqueta para arrancar desde cero."
              />
            ) : null}

            {wines.map((wine) => {
              const isSelected = selectedWineId === wine.id;
              const stockMeta = stockStateMeta[wine.stock_state];

              return (
                <button
                  key={wine.id}
                  type="button"
                  onClick={() => selectWine(wine.id)}
                  className={`w-full rounded-lg border p-5 text-left transition ${
                    isSelected
                      ? "border-burgundy-900 bg-burgundy-950 text-cream-50 shadow-velvet"
                      : "border-burgundy-100 bg-white text-burgundy-950 hover:border-burgundy-200 hover:bg-cream-50/60"
                  }`}
                >
                  <div className="flex flex-col gap-5 md:flex-row">
                    <WineThumbnail
                      src={wine.primary_image}
                      name={wine.name}
                      className="h-28 w-24 shrink-0 rounded-lg"
                    />

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap gap-2">
                            <BackofficeBadge tone={isSelected ? "gold" : stockMeta.tone}>
                              {stockMeta.label}
                            </BackofficeBadge>
                            {wine.is_featured ? (
                              <BackofficeBadge tone={isSelected ? "gold" : "soft"}>
                                Destacado
                              </BackofficeBadge>
                            ) : null}
                            {wine.is_limited_edition ? (
                              <BackofficeBadge tone={isSelected ? "gold" : "soft"}>
                                Edición limitada
                              </BackofficeBadge>
                            ) : null}
                          </div>

                          <h4 className="mt-4 font-serif text-3xl leading-tight">{wine.name}</h4>
                          <p className="mt-2 text-sm leading-7 text-current/75">
                            {wine.varietal_name} · {wine.category_name} · SKU {wine.sku}
                          </p>
                        </div>

                        <div className="text-left xl:text-right">
                          <p className="text-2xl font-semibold">{formatARS(wine.price)}</p>
                          <p className="mt-2 text-sm text-current/70">
                            Actualizado {formatDate(wine.updated_at)}
                          </p>
                        </div>
                      </div>

                      <div className="mt-5 grid gap-3 sm:grid-cols-3">
                        <WineMetric
                          label="Stock"
                          value={`${wine.stock} botellas`}
                          inverted={isSelected}
                        />
                        <WineMetric
                          label="Margen"
                          value={
                            wine.gross_margin_percentage === null
                              ? "Sin cálculo"
                              : `${wine.gross_margin_percentage}%`
                          }
                          inverted={isSelected}
                        />
                        <WineMetric
                          label="Publicación"
                          value={wine.is_active ? "Activo en tienda" : "Oculto"}
                          inverted={isSelected}
                        />
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </BackofficePanel>

        <BackofficePanel>
          <BackofficePanelHeader
            eyebrow="Editor de vino"
            title={selectedWineId ? currentWineSummary?.name ?? "Editar vino" : "Crear nuevo vino"}
            description="La ficha fue dividida en secciones para que cargar datos comerciales, editoriales y visuales sea mucho menos caótico."
            actions={
              selectedWineId ? (
                <Button
                  variant="ghost"
                  onClick={() => {
                    if (window.confirm("¿Querés eliminar este vino del catálogo?")) {
                      deleteMutation.mutate();
                    }
                  }}
                >
                  Eliminar
                </Button>
              ) : null
            }
          />

          {currentWineSummary ? (
            <BackofficeSectionCard className="mt-6 bg-white">
              <div className="flex flex-col gap-5 md:flex-row md:items-center">
                <WineThumbnail
                  src={currentWineSummary.primary_image}
                  name={currentWineSummary.name}
                  className="h-28 w-24 rounded-lg"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap gap-2">
                    <BackofficeBadge tone={currentWineSummary.is_active ? "success" : "warning"}>
                      {currentWineSummary.is_active ? "Publicado" : "Oculto"}
                    </BackofficeBadge>
                    {currentWineSummary.is_featured ? (
                      <BackofficeBadge tone="soft">Destacado</BackofficeBadge>
                    ) : null}
                    {currentWineSummary.is_limited_edition ? (
                      <BackofficeBadge tone="gold">Edición limitada</BackofficeBadge>
                    ) : null}
                  </div>
                  <h4 className="mt-4 font-serif text-3xl text-burgundy-950">
                    {currentWineSummary.name}
                  </h4>
                  <p className="mt-2 text-sm leading-7 text-burgundy-700">
                    {currentWineSummary.varietal_name} · {currentWineSummary.category_name} · SKU{" "}
                    {currentWineSummary.sku}
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3 md:w-[420px]">
                  <WineMetric label="Precio" value={formatARS(currentWineSummary.price)} />
                  <WineMetric label="Stock" value={`${currentWineSummary.stock}`} />
                  <WineMetric label="Última edición" value={formatDate(currentWineSummary.updated_at)} />
                </div>
              </div>
            </BackofficeSectionCard>
          ) : (
            <BackofficeSectionCard className="mt-6">
              <BackofficeSectionHeading
                eyebrow="Nueva etiqueta"
                title="Empezá por identidad y pricing"
                description="Nombre, SKU, categoría y precio base."
              />
            </BackofficeSectionCard>
          )}

          <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="Identidad"
                title="Base comercial y catalogación"
                description="Estos campos definen cómo se encuentra, se lista y se reconoce el vino en todo el ecosistema."
              />

              <div className="mt-6 grid gap-5 md:grid-cols-2">
                <BackofficeField label="Nombre comercial" hint="Nombre visible para clientes y equipo interno.">
                  <BackofficeInput
                    value={formState.name}
                    onChange={handleTextInput("name")}
                    placeholder="Malbec Reserva"
                    required
                  />
                </BackofficeField>

                <BackofficeField
                  label="Slug"
                  hint="Se genera acompañando el nombre si todavía no lo definiste manualmente."
                >
                  <BackofficeInput
                    value={formState.slug}
                    onChange={handleTextInput("slug")}
                    placeholder="malbec-reserva"
                  />
                </BackofficeField>
              </div>

              <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                <BackofficeField label="SKU">
                  <BackofficeInput
                    value={formState.sku}
                    onChange={handleTextInput("sku")}
                    placeholder="LAB-MALBEC-RSV"
                    required
                  />
                </BackofficeField>

                <BackofficeField label="Añada">
                  <BackofficeInput
                    type="number"
                    value={formState.vintage_year}
                    onChange={handleTextInput("vintage_year")}
                    required
                  />
                </BackofficeField>

                <BackofficeField label="Categoría">
                  <BackofficeSelect
                    value={formState.category}
                    onChange={handleTextInput("category")}
                    required
                  >
                    <option value="">Seleccionar</option>
                    {(categoriesQuery.data ?? []).map((category: BackofficeCategory) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </BackofficeSelect>
                </BackofficeField>

                <BackofficeField label="Varietal">
                  <BackofficeSelect
                    value={formState.varietal}
                    onChange={handleTextInput("varietal")}
                    required
                  >
                    <option value="">Seleccionar</option>
                    {(varietalsQuery.data ?? []).map((varietal: BackofficeVarietal) => (
                      <option key={varietal.id} value={varietal.id}>
                        {varietal.name}
                      </option>
                    ))}
                  </BackofficeSelect>
                </BackofficeField>
              </div>
            </BackofficeSectionCard>

            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="Comercial"
                title="Precio, stock y rentabilidad"
                description="Agrupé los datos económicos en una sola sección para que pricing y abastecimiento se lean rápido."
              />

              <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {pricingFieldConfig.map(({ field, label, hint, inputType = "text", step }) => (
                  <BackofficeField key={field} label={label} hint={hint}>
                    <BackofficeInput
                      type={inputType}
                      step={step}
                      value={formState[field]}
                      onChange={handleTextInput(field)}
                    />
                  </BackofficeField>
                ))}
              </div>
            </BackofficeSectionCard>

            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="Perfil sensorial"
                title="Servicio, crianza y estructura"
                description="Servicio, crianza, alcohol, acidez y estructura."
              />

              <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                {serviceFieldConfig.map(({ field, label, hint }) => (
                  <BackofficeField key={field} label={label} hint={hint}>
                    <BackofficeInput
                      type="number"
                      value={formState[field]}
                      onChange={handleTextInput(field)}
                    />
                  </BackofficeField>
                ))}

                <BackofficeField label="Tipo de crianza" hint="Método principal de evolución o conservación.">
                  <BackofficeSelect
                    value={formState.ageing_type}
                    onChange={handleTextInput("ageing_type")}
                  >
                    {ageingOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </BackofficeSelect>
                </BackofficeField>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-3">
                {wineFlags.map((flag) => (
                  <BackofficeCheckboxCard
                    key={flag.field}
                    checked={formState[flag.field]}
                    onChange={handleBooleanChange(flag.field)}
                    label={flag.label}
                    description={flag.description}
                  />
                ))}
              </div>
            </BackofficeSectionCard>

            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="Narrativa"
                title="Contenido editorial de la ficha"
                description="Descripción, cata, maridajes y nota de enólogo."
              />

              <div className="mt-6 grid gap-5 xl:grid-cols-2">
                <BackofficeField label="Descripción" hint="Presentación principal del vino.">
                  <BackofficeTextarea
                    value={formState.description}
                    onChange={handleTextInput("description")}
                    placeholder="Un vino de perfil profundo, elegante y gastronómico..."
                  />
                </BackofficeField>

                <BackofficeField label="Notas de cata" hint="Aromas, boca y final.">
                  <BackofficeTextarea
                    value={formState.tasting_notes}
                    onChange={handleTextInput("tasting_notes")}
                    placeholder="Fruta negra madura, especias dulces y textura envolvente."
                  />
                </BackofficeField>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-2">
                <BackofficeField label="Maridajes" hint="Un maridaje por línea para mantener claridad.">
                  <BackofficeTextarea
                    value={formState.pairing_suggestions_text}
                    onChange={handleTextInput("pairing_suggestions_text")}
                    placeholder={"Carnes asadas\nPastas con ragú\nQuesos semiduros"}
                  />
                </BackofficeField>

                <BackofficeField label="Notas del enólogo" hint="Contexto de elaboración, intención o estilo de cosecha.">
                  <BackofficeTextarea
                    value={formState.winemaker_notes}
                    onChange={handleTextInput("winemaker_notes")}
                    placeholder="Fermentación cuidada para priorizar fruta y tensión."
                  />
                </BackofficeField>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-2">
                <BackofficeField
                  label="Premios"
                  hint="Usá el formato Premio | puntaje | año para mantener consistencia."
                >
                  <BackofficeTextarea
                    value={formState.awards_text}
                    onChange={handleTextInput("awards_text")}
                    placeholder={"Decanter | 92 | 2025\nGuía Descorchados | 94 | 2026"}
                  />
                </BackofficeField>

                <BackofficeField
                  label="Blend varietal"
                  hint="Usá el formato Varietal: porcentaje."
                >
                  <BackofficeTextarea
                    value={formState.blend_varietals_text}
                    onChange={handleTextInput("blend_varietals_text")}
                    placeholder={"Malbec: 85\nCabernet Franc: 15"}
                  />
                </BackofficeField>
              </div>
            </BackofficeSectionCard>

            <BackofficeSectionCard>
              <div className="flex flex-col gap-4 border-b border-burgundy-100 pb-5 md:flex-row md:items-end md:justify-between">
                <BackofficeSectionHeading
                  eyebrow="Imágenes"
                  title="Galería del vino"
                  description="Preview, URL, alt text y control de principal."
                />
                <Button type="button" variant="ghost" onClick={addImage}>
                  Agregar imagen
                </Button>
              </div>

              <div className="mt-6 space-y-4">
                {formState.images.map((image, index) => (
                  <div
                    key={`image-${index}`}
                    className="rounded-lg border border-burgundy-100 bg-white p-4 md:p-5"
                  >
                    <div className="grid gap-5 lg:grid-cols-[124px_1fr]">
                      <WineThumbnail
                        src={image.url}
                        name={image.alt_text || formState.name || `Imagen ${index + 1}`}
                        className="h-36 w-full rounded-lg"
                      />

                      <div className="space-y-5">
                        <div className="flex flex-wrap items-center gap-2">
                          <BackofficeBadge tone={image.is_primary ? "gold" : "soft"}>
                            {image.is_primary ? "Imagen principal" : `Imagen ${index + 1}`}
                          </BackofficeBadge>
                        </div>

                        <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
                          <BackofficeField label="URL" hint="Pegá la ruta completa de la imagen publicada.">
                            <BackofficeInput
                              value={image.url}
                              onChange={(event) => updateImage(index, { url: event.target.value })}
                              placeholder="https://..."
                            />
                          </BackofficeField>

                          <BackofficeField
                            label="Alt text"
                            hint="Descripción corta útil para accesibilidad y SEO."
                          >
                            <BackofficeInput
                              value={image.alt_text}
                              onChange={(event) =>
                                updateImage(index, { alt_text: event.target.value })
                              }
                              placeholder="Botella de Malbec Reserva sobre fondo claro"
                            />
                          </BackofficeField>
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <Button
                            type="button"
                            variant="ghost"
                            onClick={() => markPrimaryImage(index)}
                          >
                            {image.is_primary ? "Ya es principal" : "Marcar como principal"}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            onClick={() => removeImage(index)}
                          >
                            Quitar imagen
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </BackofficeSectionCard>

            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="SEO"
                title="Metadata de descubrimiento"
                description="Meta title, descripción y estado de publicación."
              />

              <div className="mt-6 grid gap-5 xl:grid-cols-2">
                <BackofficeField label="Meta title" hint="Ideal para buscadores y snippets sociales.">
                  <BackofficeInput
                    value={formState.meta_title}
                    onChange={handleTextInput("meta_title")}
                    placeholder="Malbec Reserva | Bodega La Abeja"
                  />
                </BackofficeField>

                <BackofficeField
                  label="Meta description"
                  hint="Resumen corto, natural y atractivo para buscadores."
                >
                  <BackofficeInput
                    value={formState.meta_description}
                    onChange={handleTextInput("meta_description")}
                    placeholder="Vino de perfil elegante, estructura amable y gran versatilidad gastronómica."
                  />
                </BackofficeField>
              </div>
            </BackofficeSectionCard>

            {selectedWineQuery.isLoading ? (
              <BackofficeMessage>Cargando datos completos del vino seleccionado...</BackofficeMessage>
            ) : null}

            {selectedWineQuery.isError ? (
              <BackofficeMessage>
                No pudimos cargar el detalle completo del vino seleccionado.
              </BackofficeMessage>
            ) : null}

            {feedback ? <BackofficeMessage>{feedback}</BackofficeMessage> : null}

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={saveMutation.isPending || selectedWineQuery.isLoading}>
                {saveMutation.isPending ? "Guardando..." : "Guardar vino"}
              </Button>
              <Button type="button" variant="ghost" onClick={resetEditor}>
                Limpiar formulario
              </Button>
            </div>
          </form>
        </BackofficePanel>
      </div>
    </div>
  );
}
