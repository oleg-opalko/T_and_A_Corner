from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import Brand, Category, Perfume


class Command(BaseCommand):
    help = 'Load demo perfumes matching the design mockup'

    def handle(self, *args, **options):
        category, _ = Category.objects.get_or_create(
            slug='signature',
            defaults={'name': 'Signature Collection'},
        )
        brand, _ = Brand.objects.get_or_create(
            slug='ta-corner',
            defaults={'name': 'T&A Corner'},
        )

        demo_products = [
            {
                'slug': 'noir-eclat',
                'name': 'Noir Éclat',
                'image': 'https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=80',
                'gallery': [
                    'https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1587017539573-35a5ad39b0d8?auto=format&fit=crop&w=900&q=80',
                ],
                'notes_top': 'Чорна троянда, бергамот',
                'notes_middle': 'Ірис, пачулі',
                'notes_base': 'Мускус, ваніль',
                'description': 'Темний, витончений аромат для вечірньої атмосфери.',
            },
            {
                'slug': 'ambre-minuit',
                'name': 'Ambre Minuit',
                'image': 'https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=900&q=80',
                'gallery': [
                    'https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1587017539573-35a5ad39b0d8?auto=format&fit=crop&w=900&q=80',
                ],
                'notes_top': 'Апельсиновий цвіт, сік бузку',
                'notes_middle': 'Троянда, фіалка',
                'notes_base': 'Амбра, сандал',
                'description': 'Теплий амбрейний шлейф з м’якою, луксовою основою.',
            },
            {
                'slug': 'velour-oud',
                'name': 'Velour Oud',
                'image': 'https://images.unsplash.com/photo-1587017539573-35a5ad39b0d8?auto=format&fit=crop&w=900&q=80',
                'gallery': [
                    'https://images.unsplash.com/photo-1587017539573-35a5ad39b0d8?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=80',
                ],
                'notes_top': 'Гвоздика, персиковий цвіт',
                'notes_middle': 'Пачулі, кедр',
                'notes_base': 'Оуд, кістяний мускус',
                'description': 'Глибокий і бархатистий аромат з яскравим деревним акцентом.',
            },
            {
                'slug': 'lunar-shadow',
                'name': 'Lunar Shadow',
                'image': 'https://images.unsplash.com/photo-1611078489935-0cb964de46d6?auto=format&fit=crop&w=900&q=80',
                'gallery': [
                    'https://images.unsplash.com/photo-1611078489935-0cb964de46d6?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1587017539573-35a5ad39b0d8?auto=format&fit=crop&w=900&q=80',
                ],
                'notes_top': 'Лимон, фрезія',
                'notes_middle': 'Ніжна троянда, хміль',
                'notes_base': 'Мускус, білий кедр',
                'description': 'Легкий і модний аромат із м’яким, нічним характером.',
            },
        ]

        for product in demo_products:
            Perfume.objects.update_or_create(
                slug=product['slug'],
                defaults={
                    'name': product['name'],
                    'brand': brand,
                    'category': category,
                    'product_type': 'Extrait de Parfum',
                    'price': Decimal('180.00'),
                    'volume_ml': 50,
                    'notes_top': product['notes_top'],
                    'notes_middle': product['notes_middle'],
                    'notes_base': product['notes_base'],
                    'image': product['image'],
                    'gallery': product['gallery'],
                    'is_available': True,
                    'is_featured': True,
                    'description': product['description'],
                },
            )

        self.stdout.write(self.style.SUCCESS('Demo products loaded.'))
