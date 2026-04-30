import { type FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import type { BackofficeCategory } from "../../types/backoffice";

interface CategoryFormState {
  name: string;
  slug: string;
  description: string;
  icon: string;
  order: string;
}

const emptyCategoryForm: CategoryFormState = {
  name: "",
  slug: "",
  description: "",
  icon: "",
  order: "0",
};

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<BackofficeCategory | null>(null);
  const [formState, setFormState] = useState<CategoryFormState>(emptyCategoryForm);
  const [feedback, setFeedback] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["backoffice-categories"],
    queryFn: backofficeApi.categories.list,
  });

  useEffect(() => {
    if (!selectedCategory) {
      setFormState(emptyCategoryForm);
      return;
    }
    setFormState({
      name: selectedCategory.name,
      slug: selectedCategory.slug,
      description: selectedCategory.description,
      icon: selectedCategory.icon,
      order: String(selectedCategory.order),
    });
  }, [selectedCategory]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: formState.name,
        slug: formState.slug,
        description: formState.description,
        icon: formState.icon,
        order: Number.parseInt(formState.order, 10) || 0,
      };

      if (selectedCategory) {
        return backofficeApi.categories.update(selectedCategory.id, payload);
      }
      return backofficeApi.categories.create(payload);
    },
    onSuccess: async (category) => {
      setFeedback("Categoría guardada correctamente.");
      setSelectedCategory(category);
      await queryClient.invalidateQueries({ queryKey: ["backoffice-categories"] });
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ detail?: string }>;
      setFeedback(
        axiosError.response?.data?.detail ?? "No pudimos guardar la categoría seleccionada.",
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCategory) {
        return;
      }
      await backofficeApi.categories.remove(selectedCategory.id);
    },
    onSuccess: async () => {
      setFeedback("Categoría eliminada.");
      setSelectedCategory(null);
      setFormState(emptyCategoryForm);
      await queryClient.invalidateQueries({ queryKey: ["backoffice-categories"] });
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    saveMutation.mutate();
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <section className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
              Categorías
            </p>
            <h3 className="mt-2 font-serif text-3xl text-burgundy-950">Orden y navegación del shop</h3>
          </div>
          <Button
            variant="ghost"
            onClick={() => {
              setSelectedCategory(null);
              setFormState(emptyCategoryForm);
            }}
          >
            Nueva categoría
          </Button>
        </div>

        <div className="mt-6 space-y-3">
          {isLoading ? <p className="text-burgundy-700">Cargando categorías...</p> : null}
          {(data ?? []).map((category) => (
            <button
              key={category.id}
              type="button"
              onClick={() => setSelectedCategory(category)}
              className={`w-full rounded-[22px] border px-4 py-4 text-left transition ${
                selectedCategory?.id === category.id
                  ? "border-burgundy-300 bg-burgundy-50"
                  : "border-burgundy-100 bg-cream-50 hover:border-burgundy-200"
              }`}
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-burgundy-950">{category.name}</p>
                  <p className="mt-1 text-sm text-burgundy-700">
                    {category.slug} · {category.wines_count} vino
                    {category.wines_count === 1 ? "" : "s"}
                  </p>
                </div>
                <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-burgundy-700">
                  Orden {category.order}
                </span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
          Editor
        </p>
        <h3 className="mt-2 font-serif text-3xl text-burgundy-950">
          {selectedCategory ? "Editar categoría" : "Crear categoría"}
        </h3>

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div className="grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Nombre</span>
              <input
                value={formState.name}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, name: event.target.value }))
                }
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                required
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Slug</span>
              <input
                value={formState.slug}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, slug: event.target.value }))
                }
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                placeholder="Se completa solo si lo dejás vacío"
              />
            </label>
          </div>

          <div className="grid gap-5 md:grid-cols-[1fr_180px]">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Icono</span>
              <input
                value={formState.icon}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, icon: event.target.value }))
                }
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                placeholder="wine, grape, sparkles..."
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Orden</span>
              <input
                type="number"
                value={formState.order}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, order: event.target.value }))
                }
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
              />
            </label>
          </div>

          <label className="grid gap-2">
            <span className="text-sm font-semibold text-burgundy-800">Descripción</span>
            <textarea
              value={formState.description}
              onChange={(event) =>
                setFormState((current) => ({ ...current, description: event.target.value }))
              }
              className="min-h-32 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
            />
          </label>

          {feedback ? (
            <div className="rounded-[20px] border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
              {feedback}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Guardando..." : "Guardar categoría"}
            </Button>
            {selectedCategory ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  if (window.confirm("¿Querés eliminar esta categoría?")) {
                    deleteMutation.mutate();
                  }
                }}
              >
                Eliminar
              </Button>
            ) : null}
          </div>
        </form>
      </section>
    </div>
  );
}
