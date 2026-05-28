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

    def build_payment_issue_response(self, result: dict[str, object]) -> str:
        """Render a payment diagnostic response."""
        if not result.get("found"):
            return "No encontre un pago asociado con esos datos."
        return (
            f"El pedido {result.get('order_number')} tiene pago {result.get('payment_status')} "
            f"y estado de pedido {result.get('order_status')}. "
            f"Diagnostico: {result.get('diagnosis')}. "
            f"Siguiente paso sugerido: {result.get('recommended_action')}"
        ).strip()

    def build_sales_summary_response(self, result: dict[str, object]) -> str:
        """Render aggregate sales metrics."""
        return (
            f"Resumen de ventas para {result.get('period')}: "
            f"{result.get('order_count')} pedidos, "
            f"ARS {result.get('total_revenue')} facturados, "
            f"{result.get('bottles_sold')} botellas vendidas, "
            f"ticket promedio ARS {result.get('average_order_value')}."
        )

    def build_sales_over_period_response(self, results: list[dict[str, object]], grain: str) -> str:
        """Render grouped sales metrics."""
        if not results:
            return "No hubo ventas cerradas para ese periodo."
        lines = [
            (
                f"- {item['period']}: {item['order_count']} pedidos, "
                f"ARS {item['total_revenue']}, {item['bottles_sold']} botellas"
            )
            for item in results
        ]
        return f"Ventas agrupadas por {grain}:\n" + "\n".join(lines)

    def build_sales_by_varietal_response(self, results: list[dict[str, object]]) -> str:
        """Render varietal sales rankings."""
        if not results:
            return "No encontre ventas por varietal para ese periodo."
        lines = [
            (
                f"- {item['varietal']}: {item['bottles_sold']} botellas, "
                f"ARS {item['revenue']}, {item['order_count']} pedidos"
            )
            for item in results
        ]
        return "Ventas por varietal:\n" + "\n".join(lines)

    def build_sales_by_bottle_response(self, results: list[dict[str, object]]) -> str:
        """Render bottle or SKU sales rankings."""
        if not results:
            return "No encontre ventas por etiqueta para ese periodo."
        lines = [
            (
                f"- {item['wine_name']} ({item['sku']}): {item['bottles_sold']} botellas, "
                f"ARS {item['revenue']}, {item['order_count']} pedidos"
            )
            for item in results
        ]
        return "Ventas por botella o etiqueta:\n" + "\n".join(lines)

    def build_support_task_response(self, result: dict[str, object]) -> str:
        """Render a task creation or update response."""
        if result.get("approval_required"):
            return (
                "Prepare la accion y quedo pendiente de aprobacion humana. "
                f"Approval {result.get('approval_request_id')}."
            )
        if result.get("created"):
            return (
                f"Listo. Cree la tarea {result.get('task_id')} "
                f"con estado {result.get('status')} y prioridad {result.get('priority')}."
            )
        if result.get("updated"):
            return (
                f"Actualice la tarea {result.get('task_id')} "
                f"y quedo en estado {result.get('status')}."
            )
        return "No pude completar la operacion sobre la tarea con los datos recibidos."

    def build_order_status_update_response(self, result: dict[str, object]) -> str:
        """Render a status-change or approval-needed response."""
        if result.get("approval_required"):
            return (
                "Prepare el cambio de estado, pero requiere aprobacion humana antes de ejecutarse. "
                f"Approval {result.get('approval_request_id')}."
            )
        if not result.get("updated"):
            return "No pude actualizar el pedido con los datos recibidos."
        return (
            f"Actualice el pedido {result.get('order_number')} "
            f"de {result.get('previous_status')} a {result.get('status')}."
        )
