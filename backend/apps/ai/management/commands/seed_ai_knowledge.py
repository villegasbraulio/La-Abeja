"""Seed baseline knowledge for the AI support agent."""

# ruff: noqa: E501

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ai.models import KnowledgeDocument, KnowledgeSource
from apps.ai.rag.ingest import KnowledgeIngestionService

SEED_DOCUMENTS = [
    {
        "external_id": "guide-shipping",
        "title": "Guia de compra y envios",
        "channel": KnowledgeDocument.Channel.PUBLIC,
        "content": (
            "Cobertura prioritaria en Cuyo y AMBA.\n"
            "El retiro en bodega se coordina luego de la confirmacion y puede combinarse con una visita.\n"
            "Si la compra es para regalar o requiere volumen, responde una persona del equipo.\n"
            "El despacho usa embalaje protegido y seguimiento."
        ),
    },
    {
        "external_id": "visit-faq",
        "title": "Visitas y hospitalidad",
        "channel": KnowledgeDocument.Channel.PUBLIC,
        "content": (
            "Las visitas guiadas y maridajes se coordinan con anticipacion para garantizar cupos.\n"
            "Se aceptan grupos, empresas y celebraciones privadas bajo propuesta a medida.\n"
            "La experiencia puede continuar con compra asistida o retiro de una seleccion preparada."
        ),
    },
    {
        "external_id": "gifts-corporate",
        "title": "Regalos y programas corporativos",
        "channel": KnowledgeDocument.Channel.PUBLIC,
        "content": (
            "Hay cajas de 2, 3 y 6 vinos con presentacion premium.\n"
            "Los programas corporativos incluyen curaduria por segmento, volumen escalable y entrega coordinada.\n"
            "El canal recomendado para regalos corporativos es el concierge comercial."
        ),
    },
    {
        "external_id": "internal-playbook-support",
        "title": "Playbook interno de soporte",
        "channel": KnowledgeDocument.Channel.INTERNAL,
        "content": (
            "Si una consulta mezcla pedido y pago, el agente debe usar tools antes de responder.\n"
            "Si no hay evidencia suficiente, debe derivar al equipo humano.\n"
            "Las acciones con side effects requieren aprobacion cuando no son de solo lectura."
        ),
    },
]


class Command(BaseCommand):
    """Seed baseline knowledge for the AI feature."""

    help = "Seed baseline AI knowledge for La Abeja."

    def handle(self, *args: object, **options: object) -> None:
        """Insert or refresh the seeded knowledge corpus."""
        del args, options
        source, _ = KnowledgeSource.objects.get_or_create(
            name="La Abeja Seed Knowledge",
            defaults={
                "source_type": KnowledgeSource.SourceType.MANUAL,
                "uri": "seed://la-abeja",
                "is_active": True,
            },
        )
        service = KnowledgeIngestionService()
        for document in SEED_DOCUMENTS:
            service.upsert_document(
                source=source,
                external_id=document["external_id"],
                title=document["title"],
                content=document["content"],
                channel=document["channel"],
            )
        self.stdout.write(self.style.SUCCESS("AI knowledge seeded successfully."))
