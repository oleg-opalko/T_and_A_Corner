from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0006_perfume_gallery_perfume_notes_base_and_more')]

    operations = [
        migrations.AddField(
            model_name='perfume',
            name='regular_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Стара ціна'),
        ),
        migrations.AddField(
            model_name='perfume',
            name='is_new',
            field=models.BooleanField(default=False, verbose_name='Новинка'),
        ),
        migrations.AddField(
            model_name='perfume',
            name='is_bestseller',
            field=models.BooleanField(default=False, verbose_name='Хіт продажів'),
        ),
    ]
