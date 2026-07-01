import { Link } from "react-router-dom";
import { ArrowRight, CalendarDays, ShoppingBag } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { estateFacts } from "../../lib/siteContent";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-burgundy-950 text-cream-50">
        <img
          src="https://images.unsplash.com/photo-1569919659476-f0852f6834b7?auto=format&fit=crop&w=1400&q=80"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-cover opacity-[0.58]"
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(66,13,21,0.94)_0%,rgba(66,13,21,0.68)_47%,rgba(66,13,21,0.2)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-burgundy-950/80 to-transparent" />

        <div className="relative mx-auto grid min-h-[calc(100vh-74px)] max-w-7xl content-end gap-10 px-4 pb-8 pt-20 sm:px-6 lg:min-h-[720px] lg:grid-cols-[1fr_360px] lg:items-end lg:pb-12">
          <div className="max-w-4xl">
            <p className="mb-5 text-xs font-semibold uppercase tracking-[0.3em] text-gold-300">
              San Rafael · Mendoza · desde 1883
            </p>
            <h1 className="font-serif text-5xl leading-[0.98] text-white sm:text-6xl lg:text-7xl">
              La bodega histórica para comprar vino y vivir San Rafael.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-cream-100/88 sm:text-lg sm:leading-8">
              Elegí etiquetas de la casa, reservá una visita guiada y coordiná retiro o envío con
              atención humana desde el primer contacto.
            </p>

            <div className="mt-8 grid gap-3 sm:flex sm:flex-wrap">
              <Link to="/vinos">
                <Button className="w-full justify-between bg-gold-500 text-burgundy-950 hover:bg-gold-400 sm:w-auto">
                  <ShoppingBag className="h-4 w-4" strokeWidth={1.9} />
                  Comprar botellas
                  <ArrowRight className="h-4 w-4" strokeWidth={1.9} />
                </Button>
              </Link>
              <Link to="/visitas">
                <Button
                  variant="ghost"
                  className="w-full justify-between border-white/25 bg-white/10 text-white hover:bg-white/15 sm:w-auto"
                >
                  <CalendarDays className="h-4 w-4" strokeWidth={1.9} />
                  Reservar visita
                  <ArrowRight className="h-4 w-4" strokeWidth={1.9} />
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid gap-3 rounded-lg border border-white/14 bg-burgundy-950/72 p-4 backdrop-blur-md sm:grid-cols-3 lg:grid-cols-1">
            {estateFacts.map((fact) => (
              <div key={fact.label} className="border-white/10 py-2 sm:border-l sm:pl-4 lg:border-l-0 lg:border-t lg:pl-0 lg:first:border-t-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gold-300/80">
                  {fact.label}
                </p>
                <p className="mt-2 font-serif text-2xl text-white">{fact.value}</p>
                <p className="mt-1 text-sm leading-6 text-cream-100/76">{fact.description}</p>
              </div>
            ))}
          </div>
        </div>
    </section>
  );
}
