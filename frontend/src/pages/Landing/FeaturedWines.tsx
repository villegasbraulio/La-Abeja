import { Link } from "react-router-dom";
import { useFeaturedWines } from "../../hooks/useCatalog";
import { Button } from "../../components/ui/Button";
import { WineCard } from "../../components/wine/WineCard";
import { SectionHeading } from "../../components/common/SectionHeading";

export function FeaturedWines() {
  const { data, isLoading } = useFeaturedWines();
  const featuredWines = data ?? [];

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:py-20">
      <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <SectionHeading
          eyebrow="Compra directa"
          title="Botellas elegidas para llevar la bodega a tu mesa."
          description="Etiquetas disponibles para compra online, retiro en bodega o envío coordinado con el equipo."
        />
        <Link to="/vinos" className="shrink-0">
          <Button variant="ghost">Ver colección completa</Button>
        </Link>
      </div>
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-[520px] animate-pulse rounded-lg bg-white/80 shadow-velvet" />
          ))}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {featuredWines.map((wine, index) => (
            <WineCard key={wine.id} wine={wine} variant={index === 0 ? "featured" : "grid"} />
          ))}
        </div>
      )}
    </section>
  );
}
