# Generated by Django 3.2.13 on 2022-08-08 14:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ojs", "0004_add_editor"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="authors",
            field=models.JSONField(default=list),
        ),
    ]