import { type FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import type { BackofficeCategory } from "../../types/backoffice";
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

  const categories = data ?? [];
  const totalLinkedWines = categories.reduce((total, category) => total + category.wines_count, 0);

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
    onError: () => {
      setFeedback("No pudimos eliminar la categoría seleccionada.");
    },
  });

  function resetEditor() {
    setSelectedCategory(null);
    setFormState(emptyCategoryForm);
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
        eyebrow="Arquitectura del catálogo"
        title="Ordená las categorías con una vista más clara y consistente."
        description="Esta pantalla ahora prioriza orden visual, contexto y edición rápida para mantener la navegación del shop prolija sin perder detalle operativo."
        actions={
          <Button variant="ghost" onClick={resetEditor}>
            Nueva categoría
          </Button>
        }
        stats={[
          { label: "Categorías activas", value: categories.length },
          { label: "Vinos vinculados", value: totalLinkedWines },
          { label: "En edición", value: selectedCategory ? selectedCategory.name : "Nueva" },
        ]}
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <BackofficePanel>
          <BackofficePanelHeader
            eyebrow="Mapa del shop"
            title="Listado de categorías"
            description="Elegí una categoría para editarla o creá una nueva manteniendo orden, slug y naming consistentes."
          />

          <div className="mt-6 space-y-3">
            {isLoading ? <p className="text-burgundy-700">Cargando categorías...</p> : null}

            {!isLoading && categories.length === 0 ? (
              <BackofficeEmptyState
                title="Todavía no hay categorías cargadas."
                description="Creá la primera categoría para organizar el catálogo y su navegación."
              />
            ) : null}

            {categories.map((category) => {
              const isSelected = selectedCategory?.id === category.id;

              return (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => setSelectedCategory(category)}
                  className={`w-full rounded-[26px] border p-5 text-left transition ${
                    isSelected
                      ? "border-burgundy-900 bg-burgundy-950 text-cream-50 shadow-velvet"
                      : "border-burgundy-100 bg-cream-50/70 text-burgundy-950 hover:border-burgundy-200 hover:bg-white"
                  }`}
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-serif text-2xl">{category.name}</p>
                        {category.icon ? (
                          <BackofficeBadge tone={isSelected ? "gold" : "soft"}>
                            {category.icon}
                          </BackofficeBadge>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm leading-7 text-current/75">{category.slug}</p>
                      <p className="mt-3 text-sm leading-7 text-current/75">
                        {category.description || "Sin descripción cargada todavía."}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2 md:justify-end">
                      <BackofficeBadge tone={isSelected ? "gold" : "default"}>
                        {category.wines_count} vino{category.wines_count === 1 ? "" : "s"}
                      </BackofficeBadge>
                      <BackofficeBadge tone={isSelected ? "gold" : "soft"}>
                        Orden {category.order}
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
            title={selectedCategory ? "Refinar categoría" : "Crear nueva categoría"}
            description="Ajustá naming, slug, ícono y descripción dentro de un formulario más alineado y fácil de escanear."
          />

          <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
            <BackofficeSectionCard>
              <BackofficeSectionHeading
                eyebrow="Identidad"
                title={selectedCategory?.name ?? "Nueva categoría"}
                description="Definí cómo se presenta esta categoría dentro del catálogo y en la navegación."
              />

              <div className="mt-6 grid gap-5 md:grid-cols-2">
                <BackofficeField label="Nombre" hint="Visible para clientes y para el equipo interno.">
                  <BackofficeInput
                    value={formState.name}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, name: event.target.value }))
                    }
                    placeholder="Tintos de guarda"
                    required
                  />
                </BackofficeField>

                <BackofficeField
                  label="Slug"
                  hint="Podés dejarlo vacío si preferís que se resuelva automáticamente en backend."
                >
                  <BackofficeInput
                    value={formState.slug}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, slug: event.target.value }))
                    }
                    placeholder="tintos-de-guarda"
                  />
                </BackofficeField>
              </div>

              <div className="mt-5 grid gap-5 md:grid-cols-[1fr_180px]">
                <BackofficeField
                  label="Ícono o keyword visual"
                  hint="Referencia corta para mantener consistencia con futuros iconos o labels."
                >
                  <BackofficeInput
                    value={formState.icon}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, icon: event.target.value }))
                    }
                    placeholder="wine, cellar, reserve"
                  />
                </BackofficeField>

                <BackofficeField
                  label="Orden"
                  hint="Controla la posición de la categoría dentro del catálogo."
                >
                  <BackofficeInput
                    type="number"
                    value={formState.order}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, order: event.target.value }))
                    }
                  />
                </BackofficeField>
              </div>

              <div className="mt-5">
                <BackofficeField
                  label="Descripción"
                  hint="Usá una frase clara para orientar al cliente sobre qué encuentra en esta categoría."
                >
                  <BackofficeTextarea
                    value={formState.description}
                    onChange={(event) =>
                      setFormState((current) => ({ ...current, description: event.target.value }))
                    }
                    placeholder="Selección de vinos con estructura, crianza y perfil gastronómico."
                  />
                </BackofficeField>
              </div>
            </BackofficeSectionCard>

            {feedback ? <BackofficeMessage>{feedback}</BackofficeMessage> : null}

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "Guardando..." : "Guardar categoría"}
              </Button>
              <Button type="button" variant="ghost" onClick={resetEditor}>
                Limpiar formulario
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
        </BackofficePanel>
      </div>
    </div>
  );
}
