# Generated by Django 5.1.7 on 2025-03-27 00:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_rename_appr_error_telegramuser_avg_error_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='telegramuser',
            name='last_online',
        ),
    ]
