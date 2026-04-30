import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import { formatARS, formatDate, slugify } from "../../lib/utils";
import type {
  BackofficeCategory,
  BackofficeVarietal,
  BackofficeWineDetail,
  BackofficeWineImage,
  BackofficeWinePayload,
} from "../../types/backoffice";

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

const pricingFieldConfig: Array<{ field: WineTextField; label: string; inputType?: "text" | "number" }> = [
  { field: "price", label: "Precio" },
  { field: "compare_at_price", label: "Precio anterior" },
  { field: "cost_price", label: "Costo" },
  { field: "stock", label: "Stock" },
  { field: "low_stock_threshold", label: "Umbral stock bajo" },
  { field: "alcohol_percentage", label: "Alcohol %"},
];

const serviceFieldConfig: Array<{ field: WineTextField; label: string }> = [
  { field: "serving_temperature_min", label: "Temp. mínima" },
  { field: "serving_temperature_max", label: "Temp. máxima" },
  { field: "ageing_months", label: "Meses de crianza" },
  { field: "tannins", label: "Taninos" },
  { field: "acidity", label: "Acidez" },
  { field: "body", label: "Cuerpo" },
  { field: "sweetness", label: "Dulzor" },
  { field: "fruit_intensity", label: "Fruta" },
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

function serializeAwards(awards: Array<Record<string, unknown>>) {
  return awards
    .map((award) => `${String(award.award ?? "")} | ${String(award.score ?? "")} | ${String(award.year ?? "")}`)
    .filter((line) => !line.startsWith(" |"))
    .join("\n");
}

function serializeBlends(blends: Array<Record<string, unknown>>) {
  return blends
    .map(
      (blend) =>
        `${String(blend.varietal ?? "")}: ${String(blend.percentage ?? "")}`,
    )
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
  });

  const wines = useMemo(() => winesQuery.data?.results ?? [], [winesQuery.data?.results]);
  const selectedWinePreview = useMemo(
    () => wines.find((wine) => wine.id === selectedWineId) ?? null,
    [selectedWineId, wines],
  );

  function resetEditor() {
    setSelectedWineId(null);
    setFormState(emptyWineForm);
    setFeedback(null);
  }

  function handleTextInput(
    field: WineTextField,
  ) {
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
      const nextImages = current.images.filter((_, imageIndex) => imageIndex !== index);
      if (nextImages.length === 0) {
        return {
          ...current,
          images: [{ url: "", alt_text: "", is_primary: true, order: 0 }],
        };
      }
      return {
        ...current,
        images: nextImages.map((image, imageIndex) => ({
          ...image,
          is_primary: imageIndex === 0 ? true : image.is_primary && imageIndex === 0,
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

  return (
    <div className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
      <section className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
              Catálogo
            </p>
            <h3 className="mt-2 font-serif text-3xl text-burgundy-950">Gestor de vinos</h3>
          </div>
          <Button variant="ghost" onClick={resetEditor}>
            Nuevo vino
          </Button>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por nombre o SKU"
            className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
          />
          <div className="grid gap-4 md:grid-cols-2">
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
              className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
            >
              <option value="">Todas las categorías</option>
              {(categoriesQuery.data ?? []).map((category: BackofficeCategory) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <select
              value={varietalFilter}
              onChange={(event) => setVarietalFilter(event.target.value)}
              className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
            >
              <option value="">Todos los varietales</option>
              {(varietalsQuery.data ?? []).map((varietal: BackofficeVarietal) => (
                <option key={varietal.id} value={varietal.id}>
                  {varietal.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {winesQuery.isLoading ? <p className="text-burgundy-700">Cargando vinos...</p> : null}
          {wines.map((wine) => (
            <button
              key={wine.id}
              type="button"
              onClick={() => setSelectedWineId(wine.id)}
              className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                selectedWineId === wine.id
                  ? "border-burgundy-300 bg-burgundy-50"
                  : "border-burgundy-100 bg-cream-50 hover:border-burgundy-200"
              }`}
            >
              <div className="flex items-start gap-4">
                <img
                  src={
                    wine.primary_image ??
                    "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?auto=format&fit=crop&w=600&q=80"
                  }
                  alt={wine.name}
                  className="h-20 w-16 rounded-[16px] object-cover"
                />
                <div className="flex-1">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="font-semibold text-burgundy-950">{wine.name}</p>
                      <p className="mt-1 text-sm text-burgundy-700">
                        {wine.varietal_name} · {wine.category_name} · SKU {wine.sku}
                      </p>
                    </div>
                    <p className="text-right text-sm font-semibold text-burgundy-900">
                      {formatARS(wine.price)}
                    </p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-burgundy-800">
                      Stock {wine.stock}
                    </span>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-burgundy-800">
                      Margen {wine.gross_margin_percentage ?? 0}%
                    </span>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-burgundy-800">
                      Actualizado {formatDate(wine.updated_at)}
                    </span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
              Editor de vino
            </p>
            <h3 className="mt-2 font-serif text-3xl text-burgundy-950">
              {selectedWineId ? selectedWinePreview?.name ?? "Editar vino" : "Crear nuevo vino"}
            </h3>
          </div>
          {selectedWineId ? (
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
          ) : null}
        </div>

        <form className="mt-6 space-y-8" onSubmit={handleSubmit}>
          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Nombre comercial</span>
              <input
                value={formState.name}
                onChange={handleTextInput("name")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                required
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Slug</span>
              <input
                value={formState.slug}
                onChange={handleTextInput("slug")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                placeholder="Se completa solo"
              />
            </label>
          </div>

          <div className="grid gap-5 md:grid-cols-4">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">SKU</span>
              <input
                value={formState.sku}
                onChange={handleTextInput("sku")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                required
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Añada</span>
              <input
                type="number"
                value={formState.vintage_year}
                onChange={handleTextInput("vintage_year")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                required
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Categoría</span>
              <select
                value={formState.category}
                onChange={handleTextInput("category")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                required
              >
                <option value="">Seleccionar</option>
                {(categoriesQuery.data ?? []).map((category: BackofficeCategory) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Varietal</span>
              <select
                value={formState.varietal}
                onChange={handleTextInput("varietal")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                required
              >
                <option value="">Seleccionar</option>
                {(varietalsQuery.data ?? []).map((varietal: BackofficeVarietal) => (
                  <option key={varietal.id} value={varietal.id}>
                    {varietal.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
              Precio y stock
            </p>
            <div className="mt-5 grid gap-5 md:grid-cols-3">
              {pricingFieldConfig.map(({ field, label, inputType = "text" }) => (
                <label key={field} className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">{label}</span>
                  <input
                    type={inputType}
                    value={formState[field]}
                    onChange={handleTextInput(field)}
                    className="rounded-2xl border border-burgundy-200 bg-white px-4 py-3"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
              Servicio y perfil
            </p>
            <div className="mt-5 grid gap-5 md:grid-cols-4">
              {serviceFieldConfig.map(({ field, label }) => (
                <label key={field} className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">{label}</span>
                  <input
                    type="number"
                    value={formState[field]}
                    onChange={handleTextInput(field)}
                    className="rounded-2xl border border-burgundy-200 bg-white px-4 py-3"
                  />
                </label>
              ))}

              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Tipo de crianza</span>
                <select
                  value={formState.ageing_type}
                  onChange={handleTextInput("ageing_type")}
                  className="rounded-2xl border border-burgundy-200 bg-white px-4 py-3"
                >
                  {ageingOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            <label className="flex items-center gap-3 rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-4 text-sm font-semibold text-burgundy-900">
              <input
                type="checkbox"
                checked={formState.is_active}
                onChange={handleBooleanChange("is_active")}
              />
              Publicado en tienda
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-4 text-sm font-semibold text-burgundy-900">
              <input
                type="checkbox"
                checked={formState.is_featured}
                onChange={handleBooleanChange("is_featured")}
              />
              Destacado en home
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-4 text-sm font-semibold text-burgundy-900">
              <input
                type="checkbox"
                checked={formState.is_limited_edition}
                onChange={handleBooleanChange("is_limited_edition")}
              />
              Edición limitada
            </label>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Descripción</span>
              <textarea
                value={formState.description}
                onChange={handleTextInput("description")}
                className="min-h-36 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Notas de cata</span>
              <textarea
                value={formState.tasting_notes}
                onChange={handleTextInput("tasting_notes")}
                className="min-h-36 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
              />
            </label>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Maridajes</span>
              <textarea
                value={formState.pairing_suggestions_text}
                onChange={handleTextInput("pairing_suggestions_text")}
                className="min-h-32 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                placeholder="Un maridaje por línea"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Notas del enólogo</span>
              <textarea
                value={formState.winemaker_notes}
                onChange={handleTextInput("winemaker_notes")}
                className="min-h-32 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
              />
            </label>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Premios</span>
              <textarea
                value={formState.awards_text}
                onChange={handleTextInput("awards_text")}
                className="min-h-32 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                placeholder="Premio | puntaje | año"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Blend varietal</span>
              <textarea
                value={formState.blend_varietals_text}
                onChange={handleTextInput("blend_varietals_text")}
                className="min-h-32 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                placeholder="Malbec: 80"
              />
            </label>
          </div>

          <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                Imágenes del vino
              </p>
              <Button type="button" variant="ghost" onClick={addImage}>
                Agregar imagen
              </Button>
            </div>
            <div className="mt-5 space-y-4">
              {formState.images.map((image, index) => (
                <div
                  key={`image-${index}`}
                  className="rounded-[22px] border border-burgundy-100 bg-white p-4"
                >
                  <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
                    <label className="grid gap-2">
                      <span className="text-sm font-semibold text-burgundy-800">URL</span>
                      <input
                        value={image.url}
                        onChange={(event) => updateImage(index, { url: event.target.value })}
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                      />
                    </label>
                    <label className="grid gap-2">
                      <span className="text-sm font-semibold text-burgundy-800">Alt</span>
                      <input
                        value={image.alt_text}
                        onChange={(event) => updateImage(index, { alt_text: event.target.value })}
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                      />
                    </label>
                    <div className="flex items-end gap-2">
                      <Button type="button" variant="ghost" onClick={() => markPrimaryImage(index)}>
                        {image.is_primary ? "Principal" : "Marcar principal"}
                      </Button>
                      <Button type="button" variant="ghost" onClick={() => removeImage(index)}>
                        Quitar
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Meta title</span>
              <input
                value={formState.meta_title}
                onChange={handleTextInput("meta_title")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Meta description</span>
              <input
                value={formState.meta_description}
                onChange={handleTextInput("meta_description")}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
              />
            </label>
          </div>

          {feedback ? (
            <div className="rounded-[20px] border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
              {feedback}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={saveMutation.isPending || selectedWineQuery.isLoading}>
              {saveMutation.isPending ? "Guardando..." : "Guardar vino"}
            </Button>
            <Button type="button" variant="ghost" onClick={resetEditor}>
              Limpiar formulario
            </Button>
          </div>
        </form>
      </section>
    </div>
  );
}
