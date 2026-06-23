import hashlib

from django.db import migrations, models


def populate_idempotency_fields(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    PaymentWebhookLog = apps.get_model("payments", "PaymentWebhookLog")
    db_alias = schema_editor.connection.alias

    for payment in Payment.objects.using(db_alias).all():
        payment.idempotency_key = f"mercadopago:preference:{payment.order_id}"
        payment.save(update_fields=["idempotency_key"])

    for webhook in PaymentWebhookLog.objects.using(db_alias).order_by("pk"):
        source = f"{webhook.topic}:{webhook.mp_notification_id}:{webhook.pk}"
        webhook.deduplication_key = hashlib.sha256(source.encode("utf-8")).hexdigest()
        webhook.save(update_fields=["deduplication_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="preference_init_point",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name="payment",
            name="preference_sandbox_init_point",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name="payment",
            name="mp_preference_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="paymentwebhooklog",
            name="deduplication_key",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.RunPython(populate_idempotency_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="payment",
            name="idempotency_key",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="paymentwebhooklog",
            name="deduplication_key",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                condition=~models.Q(mp_preference_id=""),
                fields=("mp_preference_id",),
                name="unique_nonempty_mp_preference_id",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                condition=~models.Q(mp_payment_id=""),
                fields=("mp_payment_id",),
                name="unique_nonempty_mp_payment_id",
            ),
        ),
    ]
