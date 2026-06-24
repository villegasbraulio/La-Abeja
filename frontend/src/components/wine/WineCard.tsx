import { motion } from "framer-motion";
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
    <motion.article
      className={cn(
        "group relative overflow-hidden rounded-lg border border-white/70 bg-white/90 shadow-velvet",
        variant === "featured" && "md:col-span-2",
      )}
      whileHover={{ y: -6 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      data-testid="wine-card"
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-cream-100">
        <img
          src={wineImageSrc(wine.primary_image)}
          alt={wine.name}
          onError={applyWineImageFallback}
          className="h-full w-full object-cover transition duration-1000 group-hover:scale-105"
        />
        <div className="absolute left-4 top-4 flex flex-col gap-2">
          {wine.is_limited_edition ? <Badge>Edición limitada</Badge> : null}
          {wine.discount_percentage ? <Badge variant="discount">-{wine.discount_percentage}%</Badge> : null}
          {!wine.is_in_stock ? <Badge variant="outline">Sin stock</Badge> : null}
        </div>
      </div>
      <div className="space-y-3 p-5">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-burgundy-500">
          {wine.varietal_name} · {wine.vintage_year}
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-serif text-2xl text-charcoal-900">{wine.name}</h3>
            <p className="mt-1 text-sm text-burgundy-700">{wine.category_name}</p>
          </div>
          <div className="text-right">
            {wine.compare_at_price ? (
              <p className="text-sm text-burgundy-400 line-through">
                {formatARS(wine.compare_at_price)}
              </p>
            ) : null}
            <p className="text-xl font-bold text-burgundy-900">{formatARS(wine.price)}</p>
          </div>
        </div>
        <StarRating rating={wine.average_rating} count={wine.review_count} />
        <div className="flex items-center justify-between">
          <button
            type="button"
            aria-label="Agregar al carrito"
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
              "rounded-full px-4 py-2 text-sm font-semibold transition-all duration-300",
              wine.is_in_stock
                ? "bg-burgundy-900 text-gold-300 hover:bg-burgundy-800"
                : "cursor-not-allowed bg-burgundy-100 text-burgundy-400",
            )}
          >
            Agregar al carrito
          </button>
          <Link to={`/vinos/${wine.slug}`} className="text-sm font-semibold text-burgundy-800">
            Ver ficha
          </Link>
        </div>
      </div>
    </motion.article>
  );
}
