# Generated by Django 4.2.1 on 2024-12-09 05:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='issue',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
