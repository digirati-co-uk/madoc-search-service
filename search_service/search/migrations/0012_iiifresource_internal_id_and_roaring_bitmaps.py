from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0011_add_trigram_similarity_and_unaccent'),
    ]

    operations = [
        migrations.AddField(
            model_name='iiifresource',
            name='internal_id',
            field=models.BigAutoField(db_index=True, unique=True, primary_key=False),
            preserve_default=False,
        ),
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS roaringbitmap;

            CREATE MATERIALIZED VIEW mv_facet_bitmaps AS
            SELECT 
                type, 
                subtype, 
                indexable,
                language_iso639_1,
                language_iso639_2,
                md5(COALESCE(type, '') || '::' || COALESCE(subtype, '') || '::' || COALESCE(indexable, '') || '::' || COALESCE(language_iso639_1, '') || '::' || COALESCE(language_iso639_2, '')) as facet_hash,
                rb_build_agg(iiif.internal_id::int4) AS iiif_bitmap
            FROM search_indexables idx
            JOIN search_iiifresource iiif ON idx.iiif_id = iiif.madoc_id
            GROUP BY type, subtype, indexable, language_iso639_1, language_iso639_2;

            CREATE UNIQUE INDEX mv_facet_bitmaps_hash_idx ON mv_facet_bitmaps(facet_hash);
            CREATE INDEX mv_facet_bitmaps_type_subtype_idx ON mv_facet_bitmaps(type, subtype);
            """,
            reverse_sql="""
            DROP MATERIALIZED VIEW IF EXISTS mv_facet_bitmaps;
            """
        )
    ]
