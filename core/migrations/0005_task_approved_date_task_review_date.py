# Generated by Django 5.1.3 on 2024-11-26 06:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_task_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='approved_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='review_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
