import { type FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import type { BackofficeVarietal } from "../../types/backoffice";
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
  BackofficeTextarea,
} from "./BackofficeUI";

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

  const varietals = data ?? [];
  const totalLinkedWines = varietals.reduce((total, varietal) => total + varietal.wines_count, 0);

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
    onError: () => {
      setFeedback("No pudimos eliminar el varietal seleccionado.");
    },
  });

  function resetEditor() {
    setSelectedVarietal(null);
    setFormState(emptyVarietalForm);
    setFeedback(null);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    saveMutation.mutate();
  }

  return (
    <div className="space-y-8">
      <BackofficeHero
        eyebrow="Base enológica"
        title="Varietales"
        description="Origen, descripción y relación con etiquetas."
        actions={
          <Button variant="ghost" onClick={resetEditor}>
            Nuevo varietal
          </Button>
        }
        stats={[
          { label: "Varietales activos", value: varietals.length },
          { label: "Vinos asociados", value: totalLinkedWines },
          { label: "En edición", value: selectedVarietal ? selectedVarietal.name : "Nuevo" },
        ]}
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <BackofficePanel>
          <BackofficePanelHeader
            eyebrow="Mapa de uvas"
            title="Listado de varietales"
            description="Seleccioná un varietal para editarlo y mantené ordenado el relato enológico del catálogo."
          />

          <div className="mt-6 space-y-3">
            {isLoading ? <p className="text-burgundy-700">Cargando varietales...</p> : null}

            {!isLoading && varietals.length === 0 ? (
              <BackofficeEmptyState
                title="Todavía no hay varietales cargados."
                description="Creá el primero para estructurar el catálogo."
              />
            ) : null}

            {varietals.map((varietal) => {
              const isSelected = selectedVarietal?.id === varietal.id;

              return (
                <button
                  key={varietal.id}
                  type="button"
                  onClick={() => setSelectedVarietal(varietal)}
                  className={`w-full rounded-lg border p-5 text-left transition ${
                    isSelected
                      ? "border-burgundy-900 bg-burgundy-950 text-cream-50 shadow-velvet"
                      : "border-burgundy-100 bg-cream-50/70 text-burgundy-950 hover:border-burgundy-200 hover:bg-white"
                  }`}
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-serif text-2xl">{varietal.name}</p>
                        {varietal.origin_region ? (
                          <BackofficeBadge tone={isSelected ? "gold" : "soft"}>
                            {varietal.origin_region}
                          </BackofficeBadge>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm leading-7 text-current/75">{varietal.slug}</p>
                      <p className="mt-3 text-sm leading-7 text-current/75">
                        {varietal.description || "Sin descripción cargada todavía."}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2 md:justify-end">
                      <BackofficeBadge tone={isSelected ? "gold" : "default"}>
                        {varietal.wines_count} vino{varietal.wines_count === 1 ? "" : "s"}
                      </BackofficeBadge>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </BackofficePanel>

        <BackofficePanel>
          <BackofficePanelHeader
            eyebrow="Editor"
            title={selectedVarietal ? "Refinar varietal" : "Crear nuevo varietal"}
            description="Nombre, slug, región, descripción y estado visible."
          />

          <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="Ficha varietal"
                title={selectedVarietal?.name ?? "Nuevo varietal"}
                description="Usá esta ficha para ordenar la información principal que luego se refleja en el catálogo."
              />

              <div className="mt-6 grid gap-5 md:grid-cols-2">
                <BackofficeField label="Nombre" hint="Se usa en filtros, fichas y descripciones del catálogo.">
                  <BackofficeInput
                    value={formState.name}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, name: event.target.value }))
                    }
                    placeholder="Malbec"
                    required
                  />
                </BackofficeField>

                <BackofficeField
                  label="Slug"
                  hint="Podés completarlo manualmente o dejarlo vacío para generarlo automáticamente."
                >
                  <BackofficeInput
                    value={formState.slug}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, slug: event.target.value }))
                    }
                    placeholder="malbec"
                  />
                </BackofficeField>
              </div>

              <div className="mt-5">
                <BackofficeField
                  label="Región de origen"
                  hint="Sirve para contextualizar el varietal dentro de la narrativa enológica."
                >
                  <BackofficeInput
                    value={formState.origin_region}
                    onChange={(event) =>
                      setFormState((current) => ({
                        ...current,
                        origin_region: event.target.value,
                      }))
                    }
                    placeholder="Valle de Uco, Mendoza"
                  />
                </BackofficeField>
              </div>

              <div className="mt-5">
                <BackofficeField
                  label="Descripción"
                  hint="Contá el perfil general del varietal: estilo, carácter y rasgos distintivos."
                >
                  <BackofficeTextarea
                    value={formState.description}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, description: event.target.value }))
                    }
                    placeholder="Varietal de fruta profunda, tanino amable y gran versatilidad gastronómica."
                  />
                </BackofficeField>
              </div>
            </BackofficeSectionCard>

            {feedback ? <BackofficeMessage>{feedback}</BackofficeMessage> : null}

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "Guardando..." : "Guardar varietal"}
              </Button>
              <Button type="button" variant="ghost" onClick={resetEditor}>
                Limpiar formulario
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
        </BackofficePanel>
      </div>
    </div>
  );
}
