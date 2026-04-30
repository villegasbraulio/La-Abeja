import { startTransition, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { WineCard } from "../../components/wine/WineCard";
import { useCatalog, useCatalogCategories, useCatalogVarietals } from "../../hooks/useCatalog";

function parseNumericParam(value: string | null): number | undefined {
  if (!value) {
    return undefined;
  }

  const parsedValue = Number.parseInt(value, 10);
  return Number.isNaN(parsedValue) ? undefined : parsedValue;
}

export function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get("search") ?? "";
  const category = searchParams.get("category") ?? "";
  const varietal = searchParams.get("varietal") ?? "";
  const sort = searchParams.get("sort") ?? "featured";
  const inStockOnly = searchParams.get("in_stock") === "true";
  const minPrice = parseNumericParam(searchParams.get("min_price"));
  const maxPrice = parseNumericParam(searchParams.get("max_price"));

  const filters = {
    search: search || undefined,
    category: category || undefined,
    varietal: varietal || undefined,
    min_price: minPrice,
    max_price: maxPrice,
    in_stock: inStockOnly || undefined,
  };

  const { data, isLoading, isError } = useCatalog(filters);
  const { data: categories } = useCatalogCategories();
  const { data: varietals } = useCatalogVarietals();

  const wines = useMemo(() => {
    const results = [...(data?.results ?? [])];

    switch (sort) {
      case "price-asc":
        return results.sort((left, right) => Number(left.price) - Number(right.price));
      case "price-desc":
        return results.sort((left, right) => Number(right.price) - Number(left.price));
      case "name":
        return results.sort((left, right) => left.name.localeCompare(right.name, "es"));
      case "vintage-desc":
        return results.sort((left, right) => right.vintage_year - left.vintage_year);
      default:
        return results.sort(
          (left, right) => Number(right.is_featured) - Number(left.is_featured),
        );
    }
  }, [data?.results, sort]);

  const hasActiveFilters =
    search.length > 0 ||
    category.length > 0 ||
    varietal.length > 0 ||
    inStockOnly ||
    minPrice !== undefined ||
    maxPrice !== undefined;

  function updateParam(key: string, value: string | null) {
    const nextParams = new URLSearchParams(searchParams);

    if (!value) {
      nextParams.delete(key);
    } else {
      nextParams.set(key, value);
    }

    startTransition(() => {
      setSearchParams(nextParams, { replace: true });
    });
  }

  function clearFilters() {
    setSearchParams(new URLSearchParams(), { replace: true });
  }

  return (
    <div>
      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.95fr] lg:items-end">
          <SectionHeading
            eyebrow="Wine Shop"
            title="Una tienda mas completa, con filtros visibles, tono comercial y colecciones explorables."
            description="Aca es donde mas acercamos el proyecto a una bodega premium real: mejor navegacion, discovery y mas argumentos para comprar."
          />
          <div className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Comprar mejor
            </p>
            <div className="mt-4 grid gap-3 text-sm text-burgundy-800">
              <p>Filtra por categoria, varietal, rango de precio y disponibilidad.</p>
              <p>Descubri etiquetas para regalar, retirar en bodega o sumar a una visita.</p>
              <p>La interfaz ya no depende solo del listado: tambien orienta la decision.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-6 pb-20 lg:grid-cols-[320px_1fr]">
        <aside className="h-fit rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Filtros
            </p>
            {hasActiveFilters ? (
              <button
                type="button"
                className="text-sm font-semibold text-burgundy-800"
                onClick={clearFilters}
              >
                Limpiar
              </button>
            ) : null}
          </div>

          <div className="mt-6 space-y-5">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Buscar</span>
              <input
                value={search}
                onChange={(event) => updateParam("search", event.target.value || null)}
                placeholder="Malbec, reserva, espumante..."
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Categoria</span>
              <select
                value={category}
                onChange={(event) => updateParam("category", event.target.value || null)}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
              >
                <option value="">Todas</option>
                {(categories ?? []).map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Varietal</span>
              <select
                value={varietal}
                onChange={(event) => updateParam("varietal", event.target.value || null)}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
              >
                <option value="">Todos</option>
                {(varietals ?? []).map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Desde</span>
                <input
                  type="number"
                  min={0}
                  value={minPrice ?? ""}
                  onChange={(event) => updateParam("min_price", event.target.value || null)}
                  className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Hasta</span>
                <input
                  type="number"
                  min={0}
                  value={maxPrice ?? ""}
                  onChange={(event) => updateParam("max_price", event.target.value || null)}
                  className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                />
              </label>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm font-medium text-burgundy-900">
              <input
                type="checkbox"
                checked={inStockOnly}
                onChange={(event) => updateParam("in_stock", event.target.checked ? "true" : null)}
              />
              Mostrar solo etiquetas en stock
            </label>
          </div>
        </aside>

        <div>
          <div className="mb-8 flex flex-col gap-4 rounded-[30px] border border-burgundy-100 bg-white p-5 shadow-velvet md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                Resultado de la coleccion
              </p>
              <p className="mt-2 text-burgundy-800">
                {data?.count ?? 0} etiqueta{(data?.count ?? 0) === 1 ? "" : "s"} disponibles
              </p>
            </div>

            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <select
                value={sort}
                onChange={(event) => updateParam("sort", event.target.value || null)}
                className="rounded-full border border-burgundy-200 bg-cream-50 px-4 py-3 text-sm font-medium text-burgundy-900 outline-none focus:border-burgundy-400"
              >
                <option value="featured">Destacados primero</option>
                <option value="price-asc">Precio menor a mayor</option>
                <option value="price-desc">Precio mayor a menor</option>
                <option value="name">Nombre A-Z</option>
                <option value="vintage-desc">Añada mas nueva</option>
              </select>
              <Link to="/regalos">
                <Button variant="ghost">Comprar para regalar</Button>
              </Link>
            </div>
          </div>

          {isLoading ? <p className="text-burgundy-700">Cargando vinos...</p> : null}
          {isError ? (
            <p className="rounded-3xl border border-burgundy-200 bg-white px-6 py-5 text-burgundy-900">
              No pudimos cargar el catálogo. Si el backend todavía no está levantado, esta vista igual
              queda lista para conectarse a `/api/v1/catalog/wines/`.
            </p>
          ) : null}

          {!isLoading && !isError && wines.length === 0 ? (
            <div className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
              <h2 className="font-serif text-3xl text-burgundy-950">
                No encontramos etiquetas con esos filtros.
              </h2>
              <p className="mt-4 max-w-2xl leading-7 text-burgundy-800">
                Proba ampliar el rango de precio, limpiar la busqueda o consultar una seleccion
                asistida para regalos, visitas o compras corporativas.
              </p>
              <div className="mt-6 flex flex-wrap gap-4">
                <Button onClick={clearFilters}>Limpiar filtros</Button>
                <Link to="/contacto?tipo=regalos">
                  <Button variant="ghost">Pedir ayuda al concierge</Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {wines.map((wine) => (
                <WineCard key={wine.id} wine={wine} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
