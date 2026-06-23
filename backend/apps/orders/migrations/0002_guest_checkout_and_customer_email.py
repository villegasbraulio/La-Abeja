from django.db import migrations, models


def populate_customer_email(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    db_alias = schema_editor.connection.alias
    for order in Order.objects.using(db_alias).select_related("user").all():
        if order.customer_email:
            continue
        user = getattr(order, "user", None)
        if user and user.email:
            order.customer_email = user.email
            order.save(update_fields=["customer_email"])


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0001_initial"),
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="orders",
                to="authentication.customuser",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="customer_email",
            field=models.EmailField(blank=True, default="", max_length=254),
            preserve_default=False,
        ),
        migrations.RunPython(populate_customer_email, migrations.RunPython.noop),
    ]
