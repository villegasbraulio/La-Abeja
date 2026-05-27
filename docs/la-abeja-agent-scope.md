# La Abeja - Scope inicial para chat/agente

Este documento define una primera version del alcance usando lo que hoy muestra el repo. Donde no hay evidencia directa, lo marco como inferencia o validacion pendiente.

## 1. Que tipo de negocio es exactamente

- Negocio inferido: bodega con tres frentes comerciales.
- Ecommerce DTC de vinos.
- Visitas y experiencias en bodega.
- Regalos, cajas y programas corporativos.

### Como venden hoy

- DTC: si.
- Tienda propia: si. Hay storefront propio en React y backend Django.
- Checkout: si. El flujo actual usa Mercado Pago Checkout Pro.
- WhatsApp: si, como canal comercial y de soporte visible.
- Shopify: no hay evidencia en el repo.
- MercadoLibre: no hay evidencia en el repo.

### Hipotesis operativa razonable

- La venta transaccional de vinos va por tienda propia.
- Las ventas mas asistidas o consultivas van por contacto humano: WhatsApp, email o formulario.
- Los casos mas consultivos parecen ser visitas, eventos privados, regalos y compras corporativas.

## 2. Que problemas operativos tienen

Esta parte no esta declarada de forma explicita, pero el producto y el backoffice dejan ver los problemas mas probables.

### Problemas operativos mas probables

- Gestion manual de catalogo: precios, stock, destacados, imagenes y contenido del producto.
- Seguimiento manual de pedidos: revision de cola, estado comercial, direccion de entrega y lineas del pedido.
- Seguimiento manual de pagos: conciliacion entre orden, intento de pago y estado final.
- Consultas repetitivas de clientes: envios, retiro en bodega, tiempos de entrega, stock, estado del pedido, regalos, visitas y eventos.
- Coordinacion manual de experiencias y reservas.
- Captura desordenada de leads de alto valor: regalos corporativos, eventos privados, grupos y compras por volumen.
- Necesidad de detectar stock bajo antes de perder ventas.
- Necesidad de recuperar carritos abandonados y empujar recompra.

### Donde parece consumirse mas tiempo

- Responder consultas previas a la compra.
- Revisar pedidos y su estado real.
- Confirmar si hay stock suficiente.
- Coordinar casos no estandar: regalos, retiro, eventos, grupos o visitas.
- Mantener la informacion comercial del catalogo actualizada.

## 3. Que datos/documentos existen

### Datos estructurados que si existen en el producto

- Catalogo de vinos con SKU, precio, costo, stock y umbral de stock bajo.
- Metadatos de producto: categoria, varietal, anada, notas de cata, maridajes, premios, metadata SEO e imagenes.
- Ordenes con numero de pedido, cliente, items, direccion, envio, notas y estado.
- Pagos con preferencia de Mercado Pago, estado, metodo, tipo e installments.
- Clientes con nombre, email, telefono, fecha de nacimiento, preferencias y newsletter.
- Carritos y promo codes.
- Modelos de experiencias, slots y bookings para reservas.

### Contenido reutilizable para RAG

- FAQs de compra, envios y retiro.
- FAQs de visitas y hospitalidad.
- Informacion comercial de regalos, cajas y programas corporativos.
- Canales de contacto, horarios y promesas de servicio.

### Integraciones o piezas conectables

- Wrapper de email.
- Wrapper de WhatsApp.
- Wrapper de SMS.
- Automatizaciones de carrito abandonado.
- Automatizaciones de descuentos de cumpleanos.

### Datos o sistemas que no aparecen conectados hoy

- CRM real.
- Notion.
- Google Docs.
- Tickets o help desk.
- Historial real de conversaciones de WhatsApp.
- PDFs operativos o comerciales.
- MercadoLibre.
- Shopify.

### Observaciones importantes

- El formulario de contacto existe en frontend, pero hoy parece demo. No se ve conectado todavia a CRM, email operativo ni WhatsApp real.
- Sin esas conexiones externas, un RAG puede responder y asistir, pero no cerrar todo el circuito operativo.
- Hay una inconsistencia a validar: el README describe checkout real con Mercado Pago y ordenes, pero parte del contenido comercial del frontend todavia habla del sitio como showcase/demo.

## 4. Que acciones reales podria ejecutar un agente

### Acciones que el stack actual ya permitiria o dejaria muy cerca

- Buscar un pedido por numero o cliente.
- Ver detalle del pedido, direccion, items y estado de pago.
- Consultar stock de una etiqueta.
- Detectar productos sin stock o con stock bajo.
- Responder preguntas frecuentes de envios, retiro y visitas.
- Recomendar vinos segun varietal, notas de cata, maridaje o ocasion.
- Generar una respuesta inicial para regalos corporativos o eventos.
- Resumir una consulta y derivarla a una persona.

### Acciones que convierten el chat en agente de verdad con 1 o 2 integraciones mas

- Crear un lead o tarea desde una consulta de contacto.
- Clasificar mensajes entrantes por tipo: visita, regalo, evento, envio, postventa.
- Redactar y enviar respuesta sugerida por WhatsApp o email.
- Confirmar disponibilidad de visita o experiencia contra slots reales.
- Armar una propuesta de regalos a medida segun presupuesto y cantidad.
- Disparar seguimiento post compra o recuperacion de carrito.
- Recomendar productos alternativos cuando no hay stock.

## MVP recomendado

- Un agente comercial-operativo para pre y post venta.
- Fuentes: catalogo + FAQs + pedidos + stock + contenido de visitas/regalos.
- Acciones MVP: buscar pedido, consultar stock, responder FAQ, sugerir productos, resumir lead y derivar.

## Lo que conviene validar con el equipo

- Cuanto de la venta real pasa por tienda propia vs WhatsApp.
- Si venden tambien por otros canales fuera del repo.
- Como gestionan hoy reservas y eventos.
- Donde viven hoy los leads y seguimientos.
- Que consultas reciben mas seguido.
- Que tareas hacen manualmente todos los dias.
- Que datos externos existen aunque no esten integrados todavia.

## Fuentes del repo usadas para esta definicion

- README del proyecto.
- `frontend/src/lib/siteContent.ts`.
- Modelos de `catalog`, `orders`, `payments`, `reservations` y `authentication`.
- Vistas del backoffice y paginas de contacto, visitas, regalos y guia de compra.
