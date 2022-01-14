# Generated by Django 3.1.6 on 2021-03-08 17:43

import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iiif_search', '0007_auto_20210308_1726'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='indexables',
            index=models.Index(fields=['type', 'subtype'], name='iiif_search_inde_type_bdb46f_idx'),
        ),
    ]
