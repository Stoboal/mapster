# Generated by Django 5.1.7 on 2025-03-28 00:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_rename_appr_error_location_avg_error_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='country',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
