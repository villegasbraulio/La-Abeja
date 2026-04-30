import { Link } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { giftingCollections } from "../../lib/siteContent";

export function GiftsPage() {
  return (
    <div>
      <PageHero
        eyebrow="Regalos y cajas"
        title="Una capa comercial nueva para regalos, agasajos y compras corporativas."
        description="La referencia trabaja muy bien regalos, wine gifting y ocasiones. Aca dejamos un frente propio para vender cajas y consultas especiales con mejor contexto."
        aside={
          <div className="space-y-4 text-burgundy-900">
            <p className="rounded-[22px] bg-cream-50 px-5 py-4">
              Cajas de 2, 3 y 6 vinos con presentacion premium.
            </p>
            <p className="rounded-[22px] bg-cream-50 px-5 py-4">
              Tarjetas personalizadas, coordinacion de entrega y asesoramiento humano.
            </p>
            <p className="rounded-[22px] bg-cream-50 px-5 py-4">
              Programas especiales para empresas, eventos y celebraciones.
            </p>
          </div>
        }
      >
        <Link to="/contacto?tipo=regalos">
          <Button>Solicitar propuesta</Button>
        </Link>
        <Link to="/vinos">
          <Button variant="ghost">Elegir etiquetas</Button>
        </Link>
      </PageHero>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-3">
          {giftingCollections.map((collection) => (
            <article
              key={collection.title}
              className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet"
            >
              <h2 className="font-serif text-3xl text-burgundy-950">{collection.title}</h2>
              <p className="mt-4 leading-7 text-burgundy-800">{collection.description}</p>
              <ul className="mt-5 space-y-2 text-sm text-burgundy-700">
                {collection.bullets.map((bullet) => (
                  <li key={bullet}>• {bullet}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="rounded-[36px] border border-white/70 bg-burgundy-950 px-8 py-10 text-cream-50 shadow-velvet">
          <SectionHeading
            eyebrow="Gift Concierge"
            title="Un area dedicada a regalos mejora conversion y tambien eleva la marca."
            description="En vez de esconder este caso de uso dentro del catalogo, la pagina lo vuelve visible, aspiracional y comercialmente claro."
            tone="light"
          />
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/contacto?tipo=corporativo">
              <Button variant="secondary">Hablar por regalos corporativos</Button>
            </Link>
            <Link to="/guia-de-compra">
              <Button variant="ghost" className="border-white/30 text-cream-50 hover:bg-white/10">
                Ver logistica y envios
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
