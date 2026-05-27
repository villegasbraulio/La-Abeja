"""Deterministic response building helpers."""

from __future__ import annotations


class ResponseBuilder:
    """Turn tool and retrieval results into human-readable answers."""

    def build_order_status_response(self, result: dict[str, object]) -> str:
        """Render an order status answer."""
        if not result.get("found"):
            return "No encontre un pedido con ese numero. Si queres, revisamos juntos el numero o lo derivamos al equipo."
        status_label = result.get("status_label") or "sin estado"
        payment_status = result.get("payment_status") or "sin intento de pago"
        shipping_label = result.get("shipping_method_label") or "sin metodo de entrega"
        estimated_delivery = result.get("estimated_delivery")
        tracking_number = result.get("tracking_number")
        trailing = []
        if estimated_delivery:
            trailing.append(f"Entrega estimada: {estimated_delivery}.")
        if tracking_number:
            trailing.append(f"Tracking: {tracking_number}.")
        return (
            f"El pedido {result.get('order_number')} figura en estado {status_label}. "
            f"Pago: {payment_status}. Metodo de entrega: {shipping_label}. "
            + " ".join(trailing)
        ).strip()

    def build_low_stock_response(self, results: list[dict[str, object]]) -> str:
        """Render a low-stock ops response."""
        if not results:
            return "Hoy no encontre productos con stock bajo."
        lines = [
            f"- {item['name']} ({item['sku']}): stock {item['stock']} / umbral {item['low_stock_threshold']}"
            for item in results
        ]
        return "Estos son los vinos con stock bajo ahora mismo:\n" + "\n".join(lines)

    def build_pending_orders_response(self, results: list[dict[str, object]]) -> str:
        """Render a pending-orders ops response."""
        if not results:
            return "No hay pedidos pendientes en este momento."
        lines = [
            f"- {item['order_number']} · {item['customer_name']} · {item['status_label']} · ARS {item['total']}"
            for item in results
        ]
        return "Estos son los pedidos operativos pendientes mas recientes:\n" + "\n".join(lines)

    def build_catalog_response(self, results: list[dict[str, object]]) -> str:
        """Render a catalog search response."""
        if not results:
            return "No encontre etiquetas que coincidan con esa busqueda en el catalogo activo."
        lines = [
            (
                f"- {item['name']} · {item['varietal']} · ARS {item['price']} · "
                f"{'con stock' if item['in_stock'] else 'sin stock'}"
            )
            for item in results
        ]
        return "Encontre estas opciones en el catalogo:\n" + "\n".join(lines)

    def build_knowledge_response(self, results: list[dict[str, object]]) -> str:
        """Render a knowledge-based response fallback."""
        if not results:
            return (
                "No tengo suficiente informacion confiable para responder eso con precision todavia. "
                "Si queres, lo derivamos al equipo o cargamos esa informacion en la base de conocimiento."
            )
        top = results[0]
        return str(top.get("content") or "").strip()
