# Generated by Django 4.2.1 on 2024-12-24 19:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0003_remove_userprofile_journaling_journalentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='journalentry',
            name='journal_date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
