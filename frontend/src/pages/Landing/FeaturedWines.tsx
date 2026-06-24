import { Link } from "react-router-dom";
import { useFeaturedWines } from "../../hooks/useCatalog";
import { Button } from "../../components/ui/Button";
import { WineCard } from "../../components/wine/WineCard";
import { SectionHeading } from "../../components/common/SectionHeading";

export function FeaturedWines() {
  const { data, isLoading } = useFeaturedWines();
  const featuredWines = data ?? [];

  return (
    <section className="mx-auto max-w-7xl px-6 py-20">
      <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <SectionHeading
          eyebrow="Seleccion destacada"
          title="Etiquetas emblema para empezar a explorar la coleccion."
          description="Vinos recomendados por estilo, ocasion y expresion de la casa para elegir con mas confianza."
        />
        <Link to="/vinos" className="shrink-0">
          <Button variant="ghost">Ver la coleccion completa</Button>
        </Link>
      </div>
      {isLoading ? (
        <p className="text-burgundy-700">Cargando selección...</p>
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
