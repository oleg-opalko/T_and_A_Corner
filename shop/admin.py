import csv
from decimal import Decimal, InvalidOperation

from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.db import transaction
from django.utils.text import slugify

from .formatting import format_uah
from .models import Brand, Category, Order, OrderItem, Perfume, PerfumeVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class PerfumeVariantInline(admin.TabularInline):
    model = PerfumeVariant
    extra = 1

@admin.register(Perfume)
class PerfumeAdmin(admin.ModelAdmin):
    change_list_template = 'admin/shop/perfume/change_list.html'
    list_display = (
        'name', 'brand', 'category', 'price', 'regular_price', 'product_type',
        'is_new', 'is_bestseller', 'is_featured', 'is_available',
    )
    list_editable = ('regular_price', 'is_new', 'is_bestseller', 'is_featured', 'is_available')
    list_filter = ('is_available', 'is_new', 'is_bestseller', 'is_featured', 'brand', 'category')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'brand__name', 'category__name')
    inlines = (PerfumeVariantInline,)

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                'import/', self.admin_site.admin_view(self.import_csv),
                name='shop_perfume_import',
            ),
        ] + urls

    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                self.message_user(request, 'Оберіть CSV-файл.', level='ERROR')
            else:
                try:
                    rows = list(csv.DictReader(csv_file.read().decode('utf-8-sig').splitlines()))
                    products = [self._csv_product(row, index) for index, row in enumerate(rows, start=2)]
                    if not products:
                        raise ValueError('Файл не містить товарів.')
                    with transaction.atomic():
                        for product in products:
                            variants = product.pop('variants')
                            brand, _ = Brand.objects.get_or_create(name=product.pop('brand'))
                            category, _ = Category.objects.get_or_create(name=product.pop('category'))
                            slug = product['slug'] or slugify(f'{brand.name}-{product["name"]}', allow_unicode=True)
                            product['slug'] = slug
                            perfume, _ = Perfume.objects.update_or_create(slug=slug, defaults={
                                **product, 'brand': brand, 'category': category,
                            })
                            if not variants:
                                variants = [{
                                    'volume_ml': perfume.volume_ml,
                                    'price': perfume.price,
                                    'regular_price': perfume.regular_price,
                                    'is_available': perfume.is_available,
                                }]
                            for variant in variants:
                                PerfumeVariant.objects.update_or_create(
                                    perfume=perfume, volume_ml=variant['volume_ml'], defaults=variant,
                                )
                except (UnicodeDecodeError, ValueError, csv.Error) as error:
                    self.message_user(request, f'Імпорт не виконано: {error}', level='ERROR')
                else:
                    self.message_user(request, f'Імпортовано товарів: {len(products)}.')
                    return redirect('admin:shop_perfume_changelist')

        return render(request, 'admin/shop/perfume/import_csv.html', {
            **self.admin_site.each_context(request),
            'title': 'Імпорт товарів із CSV',
        })

    @staticmethod
    def _csv_product(row, number):
        def value(column, default=''):
            return (row.get(column) or default).strip()

        required = ('name', 'brand', 'category', 'price')
        missing = [column for column in required if not value(column)]
        if missing:
            raise ValueError(f'Рядок {number}: заповніть {", ".join(missing)}.')

        try:
            price = Decimal(value('price').replace(',', '.'))
            volume_ml = int(value('volume_ml', '50'))
        except (InvalidOperation, ValueError):
            raise ValueError(f'Рядок {number}: ціна та об’єм мають бути числами.')
        if price < 0 or volume_ml < 1:
            raise ValueError(f'Рядок {number}: ціна не може бути від’ємною, об’єм — від 1 мл.')

        def boolean(column, default):
            raw = value(column, str(default)).lower()
            if raw in ('1', 'true', 'так', 'yes'):
                return True
            if raw in ('0', 'false', 'ні', 'no'):
                return False
            raise ValueError(f'Рядок {number}: {column} має бути true або false.')

        return {
            'name': value('name'), 'slug': value('slug'),
            'brand': value('brand'), 'category': value('category'),
            'price': price, 'regular_price': PerfumeAdmin._csv_price(value('regular_price'), number), 'volume_ml': volume_ml,
            'product_type': value('product_type', 'Extrait de Parfum'),
            'description': value('description'),
            'notes_top': value('notes_top'), 'notes_middle': value('notes_middle'),
            'notes_base': value('notes_base'), 'image': value('image'),
            'variants': PerfumeAdmin._csv_variants(value('variants'), number),
            'is_available': boolean('is_available', True),
            'is_new': boolean('is_new', False),
            'is_bestseller': boolean('is_bestseller', False),
            'is_featured': boolean('is_featured', False),
        }

    @staticmethod
    def _csv_variants(raw, number):
        variants = []
        for value in filter(None, raw.split('|')):
            try:
                volume_ml, price = value.split(':')
                variants.append({'volume_ml': int(volume_ml), 'price': Decimal(price.replace(',', '.')), 'is_available': True})
            except (ValueError, InvalidOperation):
                raise ValueError(f'Рядок {number}: варіанти вкажіть як 30:500|50:700|100:1200.')
        return variants

    @staticmethod
    def _csv_price(raw, number):
        if not raw:
            return None
        try:
            return Decimal(raw.replace(',', '.'))
        except InvalidOperation:
            raise ValueError(f'Рядок {number}: стара ціна має бути числом.')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('perfume', 'variant', 'name', 'price', 'quantity', 'subtotal_display')
    fields = ('perfume', 'variant', 'name', 'price', 'quantity', 'subtotal_display')
    can_delete = False

    @admin.display(description='Сума')
    def subtotal_display(self, obj):
        return format_uah(obj.subtotal) if obj.pk else '—'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'full_name', 'phone', 'email', 'delivery_method', 'payment_method',
        'payment_status', 'subtotal_display', 'status', 'created_at',
    )
    list_editable = ('status',)
    list_filter = ('status', 'payment_status', 'delivery_method', 'payment_method', 'created_at')
    search_fields = ('id', 'full_name', 'phone', 'email', 'city', 'delivery_address')
    readonly_fields = (
        'subtotal', 'payment_status', 'payment_provider_order_id',
        'payment_transaction_id', 'payment_payload', 'created_at', 'updated_at',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    actions = (
        'mark_processing', 'mark_shipped', 'mark_completed', 'mark_cancelled',
        'export_orders_csv',
    )
    inlines = (OrderItemInline,)
    fieldsets = (
        ('Статус', {
            'fields': ('status', 'subtotal'),
        }),
        ('Клієнт', {
            'fields': ('full_name', 'phone', 'email'),
        }),
        ('Доставка та оплата', {
            'fields': ('delivery_method', 'city', 'delivery_address', 'payment_method'),
        }),
        ('Онлайн-оплата', {
            'fields': ('payment_status', 'payment_provider_order_id', 'payment_transaction_id', 'payment_payload'),
            'classes': ('collapse',),
        }),
        ('Коментар', {
            'fields': ('comment',),
        }),
        ('Службова інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items')

    @admin.display(description='Сума товарів', ordering='subtotal')
    def subtotal_display(self, obj):
        return format_uah(obj.subtotal)

    def _mark_status(self, request, queryset, status):
        updated = queryset.update(status=status)
        self.message_user(request, f'Оновлено замовлень: {updated}.')

    @admin.action(description='Позначити як "В обробці"')
    def mark_processing(self, request, queryset):
        self._mark_status(request, queryset, Order.Status.PROCESSING)

    @admin.action(description='Позначити як "Відправлено"')
    def mark_shipped(self, request, queryset):
        self._mark_status(request, queryset, Order.Status.SHIPPED)

    @admin.action(description='Позначити як "Виконане"')
    def mark_completed(self, request, queryset):
        self._mark_status(request, queryset, Order.Status.COMPLETED)

    @admin.action(description='Позначити як "Скасоване"')
    def mark_cancelled(self, request, queryset):
        self._mark_status(request, queryset, Order.Status.CANCELLED)

    @admin.action(description='Експортувати вибрані замовлення в CSV')
    def export_orders_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Статус', 'ПІБ', 'Телефон', 'Email', 'Доставка', 'Місто',
            'Адреса / відділення', 'Оплата', 'Сума товарів', 'Коментар', 'Створено',
        ])
        for order in queryset:
            writer.writerow([
                order.pk,
                order.get_status_display(),
                order.full_name,
                order.phone,
                order.email,
                order.get_delivery_method_display(),
                order.city,
                order.delivery_address,
                order.get_payment_method_display(),
                order.subtotal,
                order.comment,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response
    #TODO test build 13