from django.db import migrations
from django.contrib.postgres.operations import (
        TrigramExtension, 
        UnaccentExtension, 
        )

class Migration(migrations.Migration):
    dependencies = [
        ('search', '0010_alter_iiifresource_items_and_more'),
    ]


    operations = [
        TrigramExtension(),
        UnaccentExtension(), 
    ]
