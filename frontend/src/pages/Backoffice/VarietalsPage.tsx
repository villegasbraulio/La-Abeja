import { type FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import type { BackofficeVarietal } from "../../types/backoffice";

interface VarietalFormState {
  name: string;
  slug: string;
  description: string;
  origin_region: string;
}

const emptyVarietalForm: VarietalFormState = {
  name: "",
  slug: "",
  description: "",
  origin_region: "",
};

export function VarietalsPage() {
  const queryClient = useQueryClient();
  const [selectedVarietal, setSelectedVarietal] = useState<BackofficeVarietal | null>(null);
  const [formState, setFormState] = useState<VarietalFormState>(emptyVarietalForm);
  const [feedback, setFeedback] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["backoffice-varietals"],
    queryFn: backofficeApi.varietals.list,
  });

  useEffect(() => {
    if (!selectedVarietal) {
      setFormState(emptyVarietalForm);
      return;
    }
    setFormState({
      name: selectedVarietal.name,
      slug: selectedVarietal.slug,
      description: selectedVarietal.description,
      origin_region: selectedVarietal.origin_region,
    });
  }, [selectedVarietal]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: formState.name,
        slug: formState.slug,
        description: formState.description,
        origin_region: formState.origin_region,
      };
      if (selectedVarietal) {
        return backofficeApi.varietals.update(selectedVarietal.id, payload);
      }
      return backofficeApi.varietals.create(payload);
    },
    onSuccess: async (varietal) => {
      setFeedback("Varietal guardado correctamente.");
      setSelectedVarietal(varietal);
      await queryClient.invalidateQueries({ queryKey: ["backoffice-varietals"] });
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ detail?: string }>;
      setFeedback(
        axiosError.response?.data?.detail ?? "No pudimos guardar el varietal seleccionado.",
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVarietal) {
        return;
      }
      await backofficeApi.varietals.remove(selectedVarietal.id);
    },
    onSuccess: async () => {
      setFeedback("Varietal eliminado.");
      setSelectedVarietal(null);
      setFormState(emptyVarietalForm);
      await queryClient.invalidateQueries({ queryKey: ["backoffice-varietals"] });
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
              Varietales
            </p>
            <h3 className="mt-2 font-serif text-3xl text-burgundy-950">Base enológica del catálogo</h3>
          </div>
          <Button
            variant="ghost"
            onClick={() => {
              setSelectedVarietal(null);
              setFormState(emptyVarietalForm);
            }}
          >
            Nuevo varietal
          </Button>
        </div>

        <div className="mt-6 space-y-3">
          {isLoading ? <p className="text-burgundy-700">Cargando varietales...</p> : null}
          {(data ?? []).map((varietal) => (
            <button
              key={varietal.id}
              type="button"
              onClick={() => setSelectedVarietal(varietal)}
              className={`w-full rounded-[22px] border px-4 py-4 text-left transition ${
                selectedVarietal?.id === varietal.id
                  ? "border-burgundy-300 bg-burgundy-50"
                  : "border-burgundy-100 bg-cream-50 hover:border-burgundy-200"
              }`}
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-burgundy-950">{varietal.name}</p>
                  <p className="mt-1 text-sm text-burgundy-700">
                    {varietal.origin_region || "Sin origen cargado"} · {varietal.wines_count} vino
                    {varietal.wines_count === 1 ? "" : "s"}
                  </p>
                </div>
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
          {selectedVarietal ? "Editar varietal" : "Crear varietal"}
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

          <label className="grid gap-2">
            <span className="text-sm font-semibold text-burgundy-800">Región de origen</span>
            <input
              value={formState.origin_region}
              onChange={(event) =>
                setFormState((current) => ({ ...current, origin_region: event.target.value }))
              }
              className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
            />
          </label>

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
              {saveMutation.isPending ? "Guardando..." : "Guardar varietal"}
            </Button>
            {selectedVarietal ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  if (window.confirm("¿Querés eliminar este varietal?")) {
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
