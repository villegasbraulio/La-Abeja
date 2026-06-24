import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { catalogApi } from "../../api/catalog";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { WineCard } from "../../components/wine/WineCard";
import { StarRating } from "../../components/wine/StarRating";
import { useCart } from "../../hooks/useCart";
import {
  FALLBACK_WINE_IMAGE,
  applyWineImageFallback,
  resolveAssetUrl,
  wineImageSrc,
} from "../../lib/assets";
import { formatARS } from "../../lib/utils";

export function ProductDetailPage() {
  const { slug = "" } = useParams();
  const { addItem } = useCart();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["wine-detail", slug],
    queryFn: () => catalogApi.detail(slug),
    enabled: slug.length > 0,
  });

  const { data: relatedCatalog } = useQuery({
    queryKey: ["related-wines", data?.varietal_name],
    queryFn: () => catalogApi.list({ search: data?.varietal_name }),
    enabled: Boolean(data?.varietal_name),
  });

  useEffect(() => {
    if (!data) {
      return;
    }

    const primaryImage =
      data.images.find((image) => image.is_primary)?.url ??
      data.primary_image ??
      data.images[0]?.url ??
      null;

    setSelectedImage(resolveAssetUrl(primaryImage));
  }, [data]);

  if (isLoading) {
    return <section className="mx-auto max-w-7xl px-6 py-16">Cargando ficha del vino...</section>;
  }

  if (isError || !data) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-burgundy-600">
            Ficha no disponible
          </p>
          <h1 className="mt-3 font-serif text-4xl text-burgundy-950">
            No encontramos este vino.
          </h1>
          <Link to="/vinos" className="mt-6 inline-flex text-sm font-semibold text-burgundy-800">
            Volver al catálogo
          </Link>
        </div>
      </section>
    );
  }

  const gallery =
    data.images.length > 0
      ? data.images
      : [
          {
            id: 0,
            url: data.primary_image ?? FALLBACK_WINE_IMAGE,
            alt_text: data.name,
            is_primary: true,
            order: 0,
          },
        ];

  const tastingEntries = [
    { label: "Taninos", value: data.tasting_profile.tannins },
    { label: "Acidez", value: data.tasting_profile.acidity },
    { label: "Cuerpo", value: data.tasting_profile.body },
    { label: "Dulzor", value: data.tasting_profile.sweetness },
    { label: "Fruta", value: data.tasting_profile.fruit_intensity },
  ];

  const relatedWines = (relatedCatalog?.results ?? [])
    .filter((wine) => wine.id !== data.id)
    .slice(0, 3);

  return (
    <div>
      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-10 lg:grid-cols-[1.02fr_0.98fr]">
          <div className="space-y-5">
            <div className="overflow-hidden rounded-lg border border-white/70 bg-white p-4 shadow-velvet">
              <img
                src={selectedImage ?? wineImageSrc(gallery[0].url)}
                alt={data.name}
                onError={applyWineImageFallback}
                className="h-full min-h-[560px] w-full rounded-lg object-cover"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-4">
              {gallery.slice(0, 4).map((image) => (
                <button
                  key={image.id}
                  type="button"
                  className="overflow-hidden rounded-lg border border-burgundy-100 bg-white p-2 shadow-velvet"
                  onClick={() => setSelectedImage(wineImageSrc(image.url))}
                >
                  <img
                    src={wineImageSrc(image.url)}
                    alt={image.alt_text}
                    onError={applyWineImageFallback}
                    className="h-24 w-full rounded-lg object-cover"
                  />
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-burgundy-600">
                {data.varietal_name} · {data.vintage_year}
              </p>
              <div className="flex flex-wrap gap-2">
                {data.is_limited_edition ? <Badge>Edición limitada</Badge> : null}
                {data.discount_percentage ? (
                  <Badge variant="discount">-{data.discount_percentage}%</Badge>
                ) : null}
              </div>
              <h1 className="font-serif text-5xl text-burgundy-950">{data.name}</h1>
              <StarRating rating={data.average_rating} count={data.review_count} />
            </div>

            <div className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet">
              <p className="text-sm uppercase tracking-[0.22em] text-burgundy-500">Precio</p>
              <div className="mt-2 flex items-end gap-3">
                <p className="text-4xl font-bold text-burgundy-950">{formatARS(data.price)}</p>
                {data.compare_at_price ? (
                  <p className="pb-1 text-lg text-burgundy-400 line-through">
                    {formatARS(data.compare_at_price)}
                  </p>
                ) : null}
              </div>
              <p className="mt-4 text-burgundy-800">{data.description}</p>
              <div className="mt-6 grid gap-3 text-sm text-burgundy-700 md:grid-cols-3">
                <div className="rounded-lg bg-cream-50 px-4 py-3">Retiro en bodega disponible</div>
                <div className="rounded-lg bg-cream-50 px-4 py-3">Asistencia para regalos y cajas</div>
                <div className="rounded-lg bg-cream-50 px-4 py-3">Concierge comercial de lunes a sabado</div>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button
                  onClick={() =>
                    addItem({
                      wineId: data.id,
                      slug: data.slug,
                      name: data.name,
                      price: data.price,
                      primaryImage: data.primary_image,
                      varietalName: data.varietal_name,
                      vintageYear: data.vintage_year,
                    })
                  }
                >
                  Agregar al carrito
                </Button>
                <Link to="/carrito">
                  <Button variant="ghost">Ver carrito</Button>
                </Link>
                <Link to="/contacto?tipo=regalos">
                  <Button variant="secondary">Comprar para regalar</Button>
                </Link>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-lg border border-burgundy-100 bg-white p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                  Notas de cata
                </p>
                <p className="mt-3 leading-7 text-burgundy-900">{data.tasting_notes}</p>
              </div>
              <div className="rounded-lg border border-burgundy-100 bg-white p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                  Maridajes
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.pairing_suggestions.map((pairing) => (
                    <span
                      key={pairing}
                      className="rounded-full bg-burgundy-50 px-3 py-2 text-sm font-medium text-burgundy-800"
                    >
                      {pairing}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-burgundy-100 bg-white p-6">
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                Perfil de cata
              </p>
              <div className="mt-5 space-y-4">
                {tastingEntries.map((entry) => (
                  <div key={entry.label}>
                    <div className="mb-2 flex items-center justify-between text-sm text-burgundy-800">
                      <span>{entry.label}</span>
                      <span>{entry.value}/100</span>
                    </div>
                    <div className="h-2 rounded-full bg-burgundy-100">
                      <div
                        className="h-2 rounded-full bg-burgundy-900"
                        style={{ width: `${entry.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-burgundy-100 bg-white p-6">
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                Datos de servicio
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-burgundy-500">Alcohol</p>
                  <p className="mt-1 text-lg font-semibold text-burgundy-950">
                    {data.alcohol_percentage}%
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-burgundy-500">
                    Temperatura
                  </p>
                  <p className="mt-1 text-lg font-semibold text-burgundy-950">
                    {data.serving_temperature_min}° a {data.serving_temperature_max}°
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-burgundy-500">Crianza</p>
                  <p className="mt-1 text-lg font-semibold text-burgundy-950">
                    {data.ageing_months} meses
                  </p>
                </div>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-lg border border-burgundy-100 bg-white p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                  Premios y menciones
                </p>
                <div className="mt-4 space-y-3 text-burgundy-800">
                  {data.awards.length > 0 ? (
                    data.awards.map((award, index) => (
                      <p key={`${String(award["award"])}-${index}`}>
                        {String(award["award"])} · {String(award["score"])} pts · {String(award["year"])}
                      </p>
                    ))
                  ) : (
                    <p>Estamos actualizando las menciones y puntajes recientes de esta etiqueta.</p>
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-burgundy-100 bg-white p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                  Notas del enologo
                </p>
                <p className="mt-4 leading-7 text-burgundy-800">
                  {data.winemaker_notes ||
                    "Vino pensado para expresar fruta, textura y una identidad clara de San Rafael."}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_0.95fr]">
          <div className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Reviews recientes
            </p>
            <div className="mt-5 grid gap-4">
              {data.recent_reviews.length > 0 ? (
                data.recent_reviews.map((review) => (
                  <article
                    key={review.id}
                    className="rounded-lg border border-burgundy-100 bg-cream-50 p-5"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-burgundy-950">{review.title}</p>
                      <p className="text-sm text-burgundy-600">{review.rating}/5</p>
                    </div>
                    <p className="mt-3 leading-7 text-burgundy-800">{review.body}</p>
                    <p className="mt-3 text-sm text-burgundy-600">{review.user_name}</p>
                  </article>
                ))
              ) : (
                <p className="text-burgundy-700">
                  Todavia no hay opiniones publicadas para esta etiqueta.
                </p>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
              Compra asistida
            </p>
            <h2 className="mt-3 font-serif text-4xl text-white">
              Tambien podes convertir esta ficha en regalo, retiro o visita.
            </h2>
            <p className="mt-4 leading-7 text-cream-100/80">
              Coordinamos cajas para regalar, retiro en bodega y experiencias para que esta compra
              se adapte al plan que tengas en mente.
            </p>
            <div className="mt-6 flex flex-wrap gap-4">
              <Link to="/contacto?tipo=regalos">
                <Button variant="secondary">Armar una caja</Button>
              </Link>
              <Link to="/visitas">
                <Button
                  variant="ghost"
                  className="border-white/30 text-cream-50 hover:bg-white/10"
                >
                  Ver visitas
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {relatedWines.length > 0 ? (
        <section className="mx-auto max-w-7xl px-6 py-20">
          <div className="mb-8">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Tambien te puede gustar
            </p>
            <h2 className="mt-3 font-serif text-4xl text-burgundy-950">
              Otras etiquetas para seguir explorando la coleccion.
            </h2>
          </div>
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {relatedWines.map((wine) => (
              <WineCard key={wine.id} wine={wine} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
