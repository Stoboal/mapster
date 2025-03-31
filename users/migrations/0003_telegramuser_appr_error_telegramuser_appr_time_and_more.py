# Generated by Django 5.1.7 on 2025-03-14 00:28

import django.contrib.auth.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_telegramuser_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramuser',
            name='appr_error',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='telegramuser',
            name='appr_time',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='telegramuser',
            name='games',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='telegramuser',
            name='total_errors',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='telegramuser',
            name='total_time',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='telegramuser',
            name='username',
            field=models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username'),
        ),
    ]
