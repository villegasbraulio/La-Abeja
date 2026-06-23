from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_guest_checkout_and_customer_email"),
    ]

    operations = [
        migrations.CreateModel(
            name="AndreaniShipment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("idempotency_key", models.CharField(max_length=100, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("processing", "Procesando"),
                            ("created", "Creado"),
                            ("failed", "Fallido"),
                        ],
                        default="processing",
                        max_length=20,
                    ),
                ),
                ("tracking_number", models.CharField(blank=True, max_length=100)),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                (
                    "response_status_code",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("label_source_url", models.URLField(blank=True, max_length=1000)),
                (
                    "label",
                    models.FileField(blank=True, upload_to="andreani/labels/%Y/%m/%d"),
                ),
                ("label_error", models.TextField(blank=True)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="andreani_shipment",
                        to="orders.order",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
