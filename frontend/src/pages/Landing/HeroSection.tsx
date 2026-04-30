import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../../components/ui/Button";
import { estateFacts } from "../../lib/siteContent";

export function HeroSection() {
  return (
    <section className="mx-auto grid max-w-7xl gap-12 px-6 py-16 lg:grid-cols-[1.08fr_0.92fr] lg:items-center lg:py-20">
      <div>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-5 text-sm font-semibold uppercase tracking-[0.35em] text-burgundy-700"
        >
          San Rafael · Mendoza · Desde 1883
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="max-w-3xl font-serif text-5xl leading-tight text-burgundy-950 md:text-7xl"
        >
          Una bodega historica convertida en experiencia premium de compra, visita y marca.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-6 max-w-2xl text-lg leading-8 text-burgundy-800"
        >
          Bodega La Abeja combina hospitalidad cuyana, storytelling enologico y una plataforma
          digital lista para mostrar catalogo, visitas, regalos y automatizaciones de alto nivel.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-10 flex flex-wrap gap-4"
        >
          <Link to="/vinos">
            <Button>Explorar etiquetas</Button>
          </Link>
          <Link to="/visitas">
            <Button variant="ghost">Planear una visita</Button>
          </Link>
          <Link to="/regalos">
            <Button variant="secondary">Ver regalos</Button>
          </Link>
        </motion.div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {estateFacts.map((fact) => (
            <div
              key={fact.label}
              className="rounded-[28px] border border-burgundy-100 bg-white/80 p-5 shadow-velvet"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                {fact.label}
              </p>
              <p className="mt-3 font-serif text-3xl text-burgundy-950">{fact.value}</p>
              <p className="mt-2 text-sm leading-6 text-burgundy-700">{fact.description}</p>
            </div>
          ))}
        </div>
      </div>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative overflow-hidden rounded-[32px] border border-white/60 bg-hero-radial p-6 shadow-velvet"
      >
        <img
          src="https://images.unsplash.com/photo-1569919659476-f0852f6834b7?auto=format&fit=crop&w=1400&q=80"
          alt="Viñedos de Bodega La Abeja"
          className="h-[520px] w-full rounded-[26px] object-cover"
        />
        <div className="absolute bottom-12 left-12 max-w-sm rounded-[24px] bg-burgundy-950/88 p-6 text-cream-50">
          <p className="text-sm uppercase tracking-[0.22em] text-gold-300">Hospitalidad + conversion</p>
          <p className="mt-3 text-lg leading-7">
            Una arquitectura pensada para vender vino, organizar visitas, disparar seguimiento y
            sostener una experiencia coherente antes y despues de cada contacto.
          </p>
        </div>
      </motion.div>
    </section>
  );
}
