from django.db import migrations


def create_variants(apps, schema_editor):
    Perfume = apps.get_model('shop', 'Perfume')
    PerfumeVariant = apps.get_model('shop', 'PerfumeVariant')
    for perfume in Perfume.objects.all():
        PerfumeVariant.objects.get_or_create(
            perfume_id=perfume.pk,
            volume_ml=perfume.volume_ml,
            defaults={
                'price': perfume.price,
                'regular_price': perfume.regular_price,
                'is_available': perfume.is_available,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('shop', '0008_perfumevariant_orderitem_variant')]

    operations = [migrations.RunPython(create_variants, migrations.RunPython.noop)]
