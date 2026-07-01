export interface SiteLink {
  label: string;
  href: string;
}

export interface FooterGroup {
  title: string;
  links: SiteLink[];
}

export interface FactItem {
  label: string;
  value: string;
  description: string;
}

export interface ExperienceItem {
  title: string;
  description: string;
  details: string[];
  cta: string;
}

export interface EditorialCard {
  title: string;
  description: string;
  eyebrow: string;
  href: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface ContactChannel {
  label: string;
  value: string;
  note: string;
}

export const siteLinks: SiteLink[] = [
  { label: "Inicio", href: "/" },
  { label: "Vinos", href: "/vinos" },
  { label: "Visitas", href: "/visitas" },
  { label: "Historia", href: "/historia" },
  { label: "Regalos", href: "/regalos" },
  { label: "Compras", href: "/guia-de-compra" },
  { label: "Contacto", href: "/contacto" },
];

export const footerGroups: FooterGroup[] = [
  {
    title: "Explorar",
    links: [
      { label: "Colección de vinos", href: "/vinos" },
      { label: "Planear una visita", href: "/visitas" },
      { label: "Historia de la bodega", href: "/historia" },
      { label: "Regalos y cajas", href: "/regalos" },
    ],
  },
  {
    title: "Asistencia",
    links: [
      { label: "Guía de compra y envíos", href: "/guia-de-compra" },
      { label: "Compra segura", href: "/compra-segura" },
      { label: "Retiro en bodega", href: "/guia-de-compra#retiro" },
      { label: "Cambios y privacidad", href: "/compra-segura" },
      { label: "Contacto y concierge", href: "/contacto" },
    ],
  },
];

export const estateFacts: FactItem[] = [
  {
    label: "Legado",
    value: "1883",
    description: "Una de las bodegas pioneras de San Rafael, con identidad cuyana y vocación anfitriona.",
  },
  {
    label: "Hospitalidad",
    value: "5 experiencias",
    description: "Catas, recorridos, maridajes y formatos privados pensados para turismo premium.",
  },
  {
    label: "Compra directa",
    value: "Tienda + visitas",
    description: "Colección online, reservas y atención personalizada en una misma experiencia.",
  },
];

export const hospitalityPromises: FactItem[] = [
  {
    label: "Retiro",
    value: "Sin costo",
    description: "Retiro coordinado en bodega con ventana de 48 horas y atención personalizada.",
  },
  {
    label: "Despachos",
    value: "Todo Cuyo + AMBA",
    description: "Envíos programados con embalaje protegido, seguimiento y soporte humano.",
  },
  {
    label: "Concierge",
    value: "Lunes a sábado",
    description: "Asistencia para regalos, maridajes, compras corporativas y reservas privadas.",
  },
];

export const featuredExperiences: ExperienceItem[] = [
  {
    title: "Recorrido fundacional y cata clásica",
    description:
      "Un paseo por la historia de la bodega, sala de barricas y degustación guiada de etiquetas emblema.",
    details: ["90 minutos", "3 vinos", "Tabla regional", "Ideal primera visita"],
    cta: "Reservar recorrido",
  },
  {
    title: "Cata premium entre toneles",
    description:
      "Experiencia para quienes buscan profundidad en varietales, guarda y expresión del terroir sanrafaelino.",
    details: ["75 minutos", "5 vinos", "Sommelier anfitrión", "Cupo 10 personas"],
    cta: "Solicitar fecha",
  },
  {
    title: "Mesa larga y maridaje cuyano",
    description:
      "Formato gastronómico para celebraciones, agasajos corporativos y grupos que quieren vivir la finca.",
    details: ["Chef invitado", "Menú por pasos", "Privado", "Disponible a medida"],
    cta: "Consultar evento privado",
  },
];

export const storyMilestones = [
  {
    year: "1883",
    title: "Origen pionero",
    description:
      "La bodega nace en una zona de acequias, frutales y viñas, con una impronta profundamente cuyana.",
  },
  {
    year: "1930",
    title: "Consolidacion en San Rafael",
    description:
      "La finca se afirma como punto de encuentro entre producción, comercio local y cultura del vino.",
  },
  {
    year: "2000+",
    title: "Hospitalidad contemporanea",
    description:
      "La experiencia suma tienda online, reservas y servicio personalizado sin perder su caracter fundacional.",
  },
];

export const editorialCards: EditorialCard[] = [
  {
    eyebrow: "Visitas",
    title: "Como planear un dia completo en San Rafael alrededor del vino",
    description:
      "Horarios sugeridos, experiencias complementarias y tips para disfrutar la bodega con calma.",
    href: "/visitas",
  },
  {
    eyebrow: "Maridajes",
    title: "Tres combinaciones para lucirte con carnes, fuegos lentos y quesos cuyanos",
    description:
      "Ideas de servicio que llevan la experiencia del vino a la mesa con una narrativa más afinada.",
    href: "/guia-de-compra",
  },
  {
    eyebrow: "Regalos",
    title: "Armar una caja memorable para clientes, equipos o celebraciones familiares",
    description:
      "Selecciones pensadas para sorprender con presentacion premium y un mensaje bien curado.",
    href: "/regalos",
  },
];

export const giftingCollections = [
  {
    title: "Cajas para celebraciones",
    description:
      "Selecciones listas para cumpleaños, aniversarios y reuniones donde el gesto importa tanto como la botella.",
    bullets: ["Packaging premium", "Tarjeta personalizada", "Opciones de 2, 3 y 6 vinos"],
  },
  {
    title: "Regalos corporativos",
    description:
      "Programas de obsequios para clientes, equipos y fin de año con asesoramiento de imagen y presupuesto.",
    bullets: ["Curaduria por segmento", "Volumen escalable", "Entrega coordinada"],
  },
  {
    title: "Invitaciones y bodas",
    description:
      "Etiquetas y cajas para eventos que buscan una memoria material elegante y conectada con Mendoza.",
    bullets: ["Selecciones especiales", "Asistencia por evento", "Opciones con retiro en finca"],
  },
];

export const shippingHighlights = [
  {
    title: "Despacho protegido",
    description:
      "Todas las botellas viajan en embalaje reforzado para temperatura y manipuleo de larga distancia.",
  },
  {
    title: "Retiro coordinado",
    description:
      "Si estas en la zona, podes retirar en bodega y sumar una visita o una compra asistida por el equipo.",
  },
  {
    title: "Atencion humana",
    description:
      "Si estas comprando para regalar o queres ayuda con maridajes, te responde una persona, no un formulario perdido.",
  },
];

export const guideFaqs: FaqItem[] = [
  {
    question: "¿A que provincias envian hoy?",
    answer:
      "Hoy coordinamos despachos con cobertura prioritaria en Cuyo y AMBA, y asistencia especial para otras plazas segun volumen, temporada y ventana climatica.",
  },
  {
    question: "¿Puedo retirar mi compra en la bodega?",
    answer:
      "Si. El retiro en bodega se coordina luego de la confirmacion y es ideal para combinar con una visita o regalo de ultimo momento.",
  },
  {
    question: "¿Hay opciones para empresas y eventos?",
    answer:
      "Si. Regalos corporativos, cajas a medida y experiencias privadas se canalizan desde contacto con respuesta personalizada.",
  },
  {
    question: "¿Puedo pagar online desde la tienda?",
    answer:
      "Si. La tienda permite avanzar con el pedido, elegir modalidad de entrega y continuar el pago online con seguimiento posterior desde el historial.",
  },
];

export const visitFaqs: FaqItem[] = [
  {
    question: "¿Necesito reserva previa?",
    answer:
      "Para vivir la experiencia completa, sí. Las visitas guiadas y maridajes se coordinan con antelación para garantizar cupos y anfitrión.",
  },
  {
    question: "¿Aceptan grupos grandes o eventos privados?",
    answer:
      "Si, especialmente para empresas, celebraciones y mesas largas. Se arma una propuesta a medida segun cantidad y formato.",
  },
  {
    question: "¿Hay estacionamiento y acceso sencillo?",
    answer:
      "La propuesta contempla llegada en auto, valet coordinado para eventos y orientacion clara desde el centro de San Rafael.",
  },
];

export const contactChannels: ContactChannel[] = [
  {
    label: "Concierge comercial",
    value: "reservas@bodegalaabeja.com.ar",
    note: "Compras especiales, regalos corporativos y asesoramiento de etiquetas.",
  },
  {
    label: "Telefono y WhatsApp",
    value: "+54 260 443 1122",
    note: "Atención de lunes a sábado de 10 a 18 h.",
  },
  {
    label: "Visitas y hospitalidad",
    value: "Av. Hipolito Yrigoyen 9500, San Rafael, Mendoza",
    note: "A minutos del centro, con retiro en bodega y experiencias privadas coordinables.",
  },
];

export const visitPlanningSteps = [
  "Elegis experiencia, cantidad de invitados y fecha ideal.",
  "El equipo confirma cupos, horario y recomendaciones de llegada.",
  "Recibis asistencia previa por WhatsApp para adaptar dieta, traslados o regalos.",
  "La visita puede continuar con compra asistida o retiro de una selección preparada.",
];

export const aboutPillars = [
  {
    title: "Terroir con identidad",
    description:
      "San Rafael aporta amplitud térmica, suelos aluviales y una expresión de fruta franca que la marca asume como su centro narrativo.",
  },
  {
    title: "Hospitalidad como producto",
    description:
      "La experiencia no termina en la etiqueta: incluye recepcion, recorrido, lenguaje de servicio y postventa con seguimiento real.",
  },
  {
    title: "Atencion conectada",
    description:
      "La tienda, las visitas y el canal de contacto funcionan como una sola conversación para acompañar mejor cada compra.",
  },
];
