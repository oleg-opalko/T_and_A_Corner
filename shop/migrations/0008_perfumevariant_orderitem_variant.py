from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('shop', '0007_perfume_regular_price_and_labels')]

    operations = [
        migrations.CreateModel(
            name='PerfumeVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('volume_ml', models.PositiveIntegerField(verbose_name='Обʼєм (мл)')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Ціна')),
                ('regular_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Стара ціна')),
                ('is_available', models.BooleanField(default=True, verbose_name='В наявності')),
                ('perfume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='shop.perfume', verbose_name='Парфум')),
            ],
            options={'verbose_name': 'Варіант обʼєму', 'verbose_name_plural': 'Варіанти обʼєму', 'ordering': ('volume_ml',)},
        ),
        migrations.AddConstraint(model_name='perfumevariant', constraint=models.UniqueConstraint(fields=('perfume', 'volume_ml'), name='unique_perfume_volume')),
        migrations.AddField(model_name='orderitem', name='variant', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='shop.perfumevariant', verbose_name='Варіант обʼєму')),
    ]
