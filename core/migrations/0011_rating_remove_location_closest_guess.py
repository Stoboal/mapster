# Generated by Django 5.1.7 on 2025-03-22 22:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_guess_options_alter_location_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('data', models.JSONField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='location',
            name='closest_guess',
        ),
    ]
