# Generated by Django 5.1.7 on 2025-03-27 00:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_guess_score'),
    ]

    operations = [
        migrations.RenameField(
            model_name='location',
            old_name='appr_error',
            new_name='avg_error',
        ),
        migrations.RenameField(
            model_name='location',
            old_name='appr_time',
            new_name='avg_time',
        ),
    ]
