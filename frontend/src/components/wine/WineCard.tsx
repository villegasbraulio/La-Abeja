import { ArrowRight, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { useCart } from "../../hooks/useCart";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { cn, formatARS } from "../../lib/utils";
import type { WineListItem } from "../../types/catalog";
import { Badge } from "../ui/Badge";
import { StarRating } from "./StarRating";

interface WineCardProps {
  wine: WineListItem;
  variant?: "grid" | "featured";
}

export function WineCard({ wine, variant = "grid" }: WineCardProps) {
  const { addItem } = useCart();

  return (
    <article
      className={cn(
        "group relative overflow-hidden rounded-lg border border-burgundy-100 bg-white shadow-velvet transition-transform duration-300 hover:-translate-y-1.5",
        variant === "featured" && "md:col-span-2",
      )}
      data-testid="wine-card"
    >
      <div className={cn("relative overflow-hidden bg-cream-100", variant === "featured" ? "aspect-[16/11]" : "aspect-[4/5]")}>
        <img
          src={wineImageSrc(wine.primary_image)}
          alt={wine.name}
          onError={applyWineImageFallback}
          className="h-full w-full object-cover transition duration-1000 group-hover:scale-105"
        />
        <div className="absolute left-3 top-3 flex flex-col gap-2">
          {wine.is_limited_edition ? <Badge>Edición limitada</Badge> : null}
          {wine.discount_percentage ? <Badge variant="discount">-{wine.discount_percentage}%</Badge> : null}
          {!wine.is_in_stock ? <Badge variant="outline">Sin stock</Badge> : null}
        </div>
      </div>
      <div className="space-y-4 p-4 sm:p-5">
        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-burgundy-500">
          {wine.varietal_name} · {wine.vintage_year}
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-serif text-2xl leading-tight text-charcoal-900">{wine.name}</h3>
            <p className="mt-1 text-sm text-burgundy-700">{wine.category_name}</p>
          </div>
          <div className="shrink-0 text-right">
            {wine.compare_at_price ? (
              <p className="text-sm text-burgundy-400 line-through">
                {formatARS(wine.compare_at_price)}
              </p>
            ) : null}
            <p className="text-xl font-bold text-burgundy-900">{formatARS(wine.price)}</p>
          </div>
        </div>
        <StarRating rating={wine.average_rating} count={wine.review_count} />
        <div className="grid grid-cols-[1fr_auto] items-center gap-3">
          <button
            type="button"
            aria-label={`Agregar al carrito: ${wine.name}`}
            onClick={() =>
              addItem({
                wineId: wine.id,
                slug: wine.slug,
                name: wine.name,
                price: wine.price,
                primaryImage: wine.primary_image,
                varietalName: wine.varietal_name,
                vintageYear: wine.vintage_year,
              })
            }
            disabled={!wine.is_in_stock}
            className={cn(
              "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-300",
              wine.is_in_stock
                ? "bg-burgundy-900 text-gold-300 hover:bg-burgundy-800"
                : "cursor-not-allowed bg-burgundy-100 text-burgundy-400",
            )}
          >
            <Plus className="h-4 w-4" strokeWidth={1.9} />
            Comprar
          </button>
          <Link
            to={`/vinos/${wine.slug}`}
            aria-label={`Ver ficha de ${wine.name}`}
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-burgundy-100 text-burgundy-900 transition hover:bg-burgundy-50"
          >
            <ArrowRight className="h-4 w-4" strokeWidth={1.9} />
          </Link>
        </div>
      </div>
    </article>
  );
}
