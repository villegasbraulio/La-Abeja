import { Link } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";

const policySections = [
  {
    title: "Pagos",
    items: [
      "Los pagos online se procesan con Mercado Pago.",
      "El pedido queda registrado antes de abrir el checkout seguro.",
      "Si el pago falla, podés reintentar desde el detalle del pedido o contactar al equipo.",
    ],
  },
  {
    title: "Envíos y retiro",
    items: [
      "El checkout calcula envío estándar, express o retiro en bodega.",
      "Los despachos viajan con embalaje protegido y seguimiento cuando el operador asigna tracking.",
      "El retiro se coordina en San Rafael, Mendoza, dentro del horario comercial.",
    ],
  },
  {
    title: "Cambios y devoluciones",
    items: [
      "Si el pedido llega dañado, escribinos dentro de las 48 horas de recibido.",
      "Conservá fotos del embalaje y las botellas para acelerar la revisión.",
      "Las cancelaciones se aceptan mientras el pedido no haya sido preparado o despachado.",
    ],
  },
  {
    title: "Privacidad",
    items: [
      "Usamos tus datos para procesar compras, pagos, envíos, visitas y soporte.",
      "No publicamos ni vendemos datos de clientes.",
      "Podés pedir actualización o baja de tus datos desde el canal de contacto.",
    ],
  },
];

export function PoliciesPage() {
  return (
    <div>
      <PageHero
        eyebrow="Compra segura"
        title="Políticas claras para comprar vino online con acompañamiento humano."
        description="Pagos, envíos, retiro, cambios y privacidad en una sola referencia para decidir sin dudas."
        aside={
          <div className="space-y-4">
            <div className="rounded-lg bg-cream-50 p-4 text-burgundy-900">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                Pago
              </p>
              <p className="mt-2 text-lg font-semibold">Mercado Pago</p>
            </div>
            <div className="rounded-lg bg-cream-50 p-4 text-burgundy-900">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                Entrega
              </p>
              <p className="mt-2 text-lg font-semibold">Envío con seguimiento o retiro</p>
            </div>
          </div>
        }
      />

      <section className="mx-auto max-w-7xl px-6 py-10">
        <SectionHeading
          eyebrow="Condiciones"
          title="Lo básico, sin letra chica innecesaria."
          description="Para compras especiales, regalos corporativos o eventos, el equipo confirma condiciones finales por contacto directo."
        />
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {policySections.map((section) => (
            <article
              key={section.title}
              className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet"
            >
              <h2 className="text-xl font-semibold text-burgundy-950">{section.title}</h2>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-burgundy-800">
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/checkout">
            <Button>Ir al checkout</Button>
          </Link>
          <Link to="/contacto">
            <Button variant="ghost">Hablar con el equipo</Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
