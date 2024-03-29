# Generated by Django 3.1.1 on 2020-09-25 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("search", "0001_initial")]

    operations = [
        migrations.RemoveIndex(model_name="indexables", name="search_inde_languag_8d9a47_idx"),
        migrations.RenameField(
            model_name="indexables", old_name="language_iso629_1", new_name="language_iso639_1"
        ),
        migrations.RenameField(
            model_name="indexables", old_name="language_iso629_2", new_name="language_iso639_2"
        ),
        migrations.AddField(
            model_name="indexables",
            name="indexable_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="indexables",
            name="indexable_float",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="indexables",
            name="indexable_int",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="indexables",
            name="indexable_json",
            field=models.JSONField(blank=True, null=True),
        ),
        # migrations.AddField(
        #     model_name='indexables',
        #     name='language_iso639_1',
        #     field=models.CharField(blank=True, max_length=2, null=True),
        # ),
        # migrations.AddField(
        #     model_name='indexables',
        #     name='language_iso639_2',
        #     field=models.CharField(blank=True, max_length=3, null=True),
        # ),
        migrations.AddIndex(
            model_name="indexables",
            index=models.Index(
                fields=["language_iso639_2", "language_iso639_1", "language_display"],
                name="search_inde_languag_e4a69b_idx",
            ),
        ),
    ]
