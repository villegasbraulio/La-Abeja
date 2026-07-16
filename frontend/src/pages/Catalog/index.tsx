import { startTransition, useMemo } from "react";
import { motion } from "framer-motion";
import { Link, useSearchParams } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { Button } from "../../components/ui/Button";
import { WineCard } from "../../components/wine/WineCard";
import { useCatalog, useCatalogCategories, useCatalogVarietals } from "../../hooks/useCatalog";
import type { WineListItem } from "../../types/catalog";

function parseNumericParam(value: string | null): number | undefined {
  if (!value) {
    return undefined;
  }

  const parsedValue = Number.parseInt(value, 10);
  return Number.isNaN(parsedValue) ? undefined : parsedValue;
}

function filterByCollection(wines: WineListItem[], collection: string) {
  switch (collection) {
    case "gift":
      return wines.filter(
        (wine) =>
          wine.is_in_stock &&
          (wine.is_featured || wine.compare_at_price !== null || (wine.average_rating ?? 0) >= 4),
      );
    case "limited":
      return wines.filter((wine) => wine.is_limited_edition);
    case "featured":
      return wines.filter((wine) => wine.is_featured);
    case "ready":
      return wines.filter((wine) => wine.is_in_stock);
    default:
      return wines;
  }
}

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  visible: { opacity: 1, y: 0 },
};

export function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get("search") ?? "";
  const category = searchParams.get("category") ?? "";
  const varietal = searchParams.get("varietal") ?? "";
  const collection = searchParams.get("collection") ?? "";
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
    const results = [...filterByCollection(data?.results ?? [], collection)];

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
  }, [collection, data?.results, sort]);

  const hasActiveFilters =
    collection.length > 0 ||
    search.length > 0 ||
    category.length > 0 ||
    varietal.length > 0 ||
    inStockOnly ||
    minPrice !== undefined ||
    maxPrice !== undefined;

  const activeFilterLabels = useMemo(() => {
    const labels: string[] = [];
    const categoryName = categories?.find((item) => item.slug === category)?.name;
    const varietalName = varietals?.find((item) => item.slug === varietal)?.name;

    if (collection === "gift") labels.push("Coleccion: Para regalar");
    if (collection === "limited") labels.push("Coleccion: Ediciones limitadas");
    if (collection === "featured") labels.push("Coleccion: Recomendadas");
    if (collection === "ready") labels.push("Coleccion: Entrega simple");
    if (category) labels.push(`Categoria: ${categoryName ?? category}`);
    if (varietal) labels.push(`Varietal: ${varietalName ?? varietal}`);
    if (minPrice !== undefined) labels.push(`Desde ${minPrice}`);
    if (maxPrice !== undefined) labels.push(`Hasta ${maxPrice}`);
    if (inStockOnly) labels.push("Solo en stock");
    if (search) labels.push(`Busqueda: ${search}`);

    return labels;
  }, [categories, category, collection, inStockOnly, maxPrice, minPrice, search, varietal, varietals]);

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
      <PageHero
        eyebrow="Vinos de la bodega"
        title="Etiquetas para descubrir, regalar o comprar con entrega inmediata."
        description="Explorá varietales, categorías y rangos de precio con una navegación clara para encontrar la botella indicada."
        className="pb-10 md:pb-12"
        titleClassName="max-w-5xl text-4xl md:text-5xl"
        descriptionClassName="max-w-3xl text-base leading-7 md:text-lg"
      />

      <motion.section
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.5, ease: "easeOut", delay: 0.08 }}
        className="mx-auto grid max-w-7xl gap-8 px-6 pb-20 lg:grid-cols-[320px_1fr]"
      >
        <motion.aside
          variants={fadeUp}
          className="h-fit rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet"
        >
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

            <div className="grid gap-4">
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Desde</span>
                <input
                  type="number"
                  min={0}
                  value={minPrice ?? ""}
                  onChange={(event) => updateParam("min_price", event.target.value || null)}
                  className="w-full min-w-0 rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none [appearance:textfield] focus:border-burgundy-400"
                />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Hasta</span>
                <input
                  type="number"
                  min={0}
                  value={maxPrice ?? ""}
                  onChange={(event) => updateParam("max_price", event.target.value || null)}
                  className="w-full min-w-0 rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none [appearance:textfield] focus:border-burgundy-400"
                />
              </label>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm font-medium text-burgundy-900">
              <input
                type="checkbox"
                checked={inStockOnly}
                onChange={(event) => updateParam("in_stock", event.target.checked ? "true" : null)}
              />
              Mostrar solo etiquetas disponibles hoy
            </label>

            <div className="rounded-lg border border-burgundy-100 bg-burgundy-950 px-4 py-5 text-cream-50">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-300">
                Compra asistida
              </p>
              <p className="mt-3 text-sm leading-6 text-cream-100/80">
                ¿Buscas un regalo, retiro en bodega o una recomendacion para tu visita?
              </p>
              <div className="mt-4 flex flex-col gap-3">
                <Link to="/regalos">
                  <Button variant="secondary" className="w-full">
                    Ver regalos
                  </Button>
                </Link>
                <Link to="/visitas">
                  <Button
                    variant="ghost"
                    className="w-full border-white/20 text-cream-50 hover:bg-white/10"
                  >
                    Explorar visitas
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </motion.aside>

        <motion.div variants={fadeUp}>
          <motion.div
            variants={fadeUp}
            className="mb-8 flex flex-col gap-4 rounded-lg border border-burgundy-100 bg-white p-5 shadow-velvet md:flex-row md:items-center md:justify-between"
          >
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                Resultado de la coleccion
              </p>
              <p className="mt-2 text-burgundy-800">
                {wines.length} etiqueta{wines.length === 1 ? "" : "s"} para explorar
              </p>
              {activeFilterLabels.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {activeFilterLabels.map((label) => (
                    <span
                      key={label}
                      className="rounded-full bg-burgundy-50 px-3 py-2 text-xs font-semibold text-burgundy-800"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              ) : null}
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
                <Button variant="ghost">Ver ideas para regalar</Button>
              </Link>
            </div>
          </motion.div>

          {isLoading ? <p className="text-burgundy-700">Cargando vinos...</p> : null}
          {isError ? (
            <p className="rounded-3xl border border-burgundy-200 bg-white px-6 py-5 text-burgundy-900">
              No pudimos cargar la coleccion por el momento. Intenta nuevamente en unos minutos o
              escribinos para recibir asistencia personalizada.
            </p>
          ) : null}

          {!isLoading && !isError && wines.length === 0 ? (
            <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet">
              <h2 className="font-serif text-3xl text-burgundy-950">
                No encontramos etiquetas con esos filtros.
              </h2>
              <p className="mt-4 max-w-2xl leading-7 text-burgundy-800">
                Prueba ampliar el rango de precio, limpiar la busqueda o pedir una recomendacion
                personalizada para regalos, visitas o compras corporativas.
              </p>
              <div className="mt-6 flex flex-wrap gap-4">
                <Button onClick={clearFilters}>Limpiar filtros</Button>
                <Link to="/contacto?tipo=regalos">
                  <Button variant="ghost">Pedir ayuda al concierge</Button>
                </Link>
              </div>
            </div>
          ) : (
            <motion.div
              initial="hidden"
              animate="visible"
              transition={{ staggerChildren: 0.06, delayChildren: 0.06 }}
              className="grid gap-6 md:grid-cols-2 xl:grid-cols-3"
            >
              {wines.map((wine) => (
                <motion.div key={wine.id} variants={fadeUp}>
                  <WineCard wine={wine} />
                </motion.div>
              ))}
            </motion.div>
          )}
        </motion.div>
      </motion.section>
    </div>
  );
}
