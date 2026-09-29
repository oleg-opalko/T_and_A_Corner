from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField('Назва', max_length=120)
    slug = models.SlugField('Slug', max_length=140, unique=True, blank=True)
    description = models.TextField('Опис', blank=True)

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:category', kwargs={'slug': self.slug})


class Brand(TimeStampedModel):
    name = models.CharField('Назва', max_length=120)
    slug = models.SlugField('Slug', max_length=140, unique=True, blank=True)
    description = models.TextField('Опис', blank=True)
    logo = models.ImageField('Логотип', upload_to='brands/', blank=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренди'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Perfume(TimeStampedModel):
    name = models.CharField('Назва', max_length=200)
    slug = models.SlugField('Slug', max_length=220, unique=True, blank=True)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='perfumes',
        verbose_name='Бренд',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='perfumes',
        verbose_name='Категорія',
    )
    description = models.TextField('Опис', blank=True)
    product_type = models.CharField(
        'Тип продукту',
        max_length=80,
        default='Extrait de Parfum',
    )
    price = models.DecimalField('Ціна', max_digits=10, decimal_places=2)
    regular_price = models.DecimalField('Стара ціна', max_digits=10, decimal_places=2, null=True, blank=True)
    volume_ml = models.PositiveIntegerField('Обʼєм (мл)', default=50)
    notes_top = models.CharField('Топ-ноти', max_length=255, blank=True)
    notes_middle = models.CharField('Середні ноти', max_length=255, blank=True)
    notes_base = models.CharField('Базові ноти', max_length=255, blank=True)
    image = models.ImageField('Зображення', upload_to='perfumes/', blank=True)
    gallery = models.JSONField('Галерея', blank=True, default=list)
    is_available = models.BooleanField('В наявності', default=True)
    is_featured = models.BooleanField('На головній', default=False)
    is_new = models.BooleanField('Новинка', default=False)
    is_bestseller = models.BooleanField('Хіт продажів', default=False)

    class Meta:
        verbose_name = 'Парфум'
        verbose_name_plural = 'Парфуми'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.brand.name} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f'{self.brand.name}-{self.name}', allow_unicode=True)
            self.slug = base_slug
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if not self.image:
            return ''
        image_value = str(self.image)
        if image_value.startswith(('http://', 'https://')):
            return image_value
        return self.image.url

    @property
    def is_on_sale(self):
        return self.regular_price is not None and self.regular_price > self.price

    @property
    def discount_percent(self):
        if not self.is_on_sale:
            return 0
        return int((self.regular_price - self.price) / self.regular_price * 100)

    def get_absolute_url(self):
        return reverse('shop:perfume_detail', kwargs={'slug': self.slug})


class PerfumeVariant(models.Model):
    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE, related_name='variants', verbose_name='Парфум')
    volume_ml = models.PositiveIntegerField('Обʼєм (мл)')
    price = models.DecimalField('Ціна', max_digits=10, decimal_places=2)
    regular_price = models.DecimalField('Стара ціна', max_digits=10, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField('В наявності', default=True)

    class Meta:
        verbose_name = 'Варіант обʼєму'
        verbose_name_plural = 'Варіанти обʼєму'
        ordering = ('volume_ml',)
        constraints = [models.UniqueConstraint(fields=('perfume', 'volume_ml'), name='unique_perfume_volume')]

    def __str__(self):
        return f'{self.perfume} — {self.volume_ml} мл'

    @property
    def is_on_sale(self):
        return self.regular_price is not None and self.regular_price > self.price

    @property
    def discount_percent(self):
        if not self.is_on_sale:
            return 0
        return int((self.regular_price - self.price) / self.regular_price * 100)


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = 'new', 'Нове'
        PAID = 'paid', 'Оплачено'
        PROCESSING = 'processing', 'В обробці'
        SHIPPED = 'shipped', 'Відправлено'
        COMPLETED = 'completed', 'Виконане'
        CANCELLED = 'cancelled', 'Скасоване'

    class DeliveryMethod(models.TextChoices):
        NOVA_POSHTA = 'nova_poshta', 'Нова пошта'
        COURIER = 'courier', 'Кур’єрська доставка'
        PICKUP = 'pickup', 'Самовивіз'

    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Оплата карткою'
        COD = 'cod', 'Післяплата'
        ONLINE = 'online', 'Онлайн-оплата'

    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = 'not_required', 'Не потрібна'
        PENDING = 'pending', 'Очікує оплати'
        PAID = 'paid', 'Оплачено'
        FAILED = 'failed', 'Не вдалося оплатити'
        CANCELLED = 'cancelled', 'Скасовано'

    full_name = models.CharField('ПІБ', max_length=160)
    phone = models.CharField('Телефон', max_length=32)
    email = models.EmailField('Email')
    city = models.CharField('Місто', max_length=120)
    delivery_address = models.CharField('Адреса або відділення', max_length=255)
    delivery_method = models.CharField(
        'Спосіб доставки', max_length=20, choices=DeliveryMethod.choices,
        default=DeliveryMethod.NOVA_POSHTA,
    )
    payment_method = models.CharField(
        'Спосіб оплати', max_length=20, choices=PaymentMethod.choices,
        default=PaymentMethod.CARD,
    )
    comment = models.TextField('Коментар', blank=True)
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.NEW)
    subtotal = models.DecimalField('Сума товарів', max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        'Статус оплати', max_length=20, choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_REQUIRED,
    )
    payment_provider_order_id = models.CharField('ID платежу в провайдері', max_length=255, blank=True)
    payment_transaction_id = models.CharField('ID транзакції', max_length=255, blank=True)
    payment_payload = models.JSONField('Дані платежу', blank=True, default=dict)

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-created_at']

    def __str__(self):
        return f'Замовлення #{self.pk} — {self.full_name}'

    @property
    def requires_online_payment(self):
        return self.payment_method in {self.PaymentMethod.CARD, self.PaymentMethod.ONLINE}


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Замовлення')
    perfume = models.ForeignKey(Perfume, on_delete=models.PROTECT, related_name='order_items', verbose_name='Парфум')
    variant = models.ForeignKey(
        PerfumeVariant, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_items', verbose_name='Варіант обʼєму',
    )
    name = models.CharField('Назва товару', max_length=200)
    price = models.DecimalField('Ціна за одиницю', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Кількість')

    class Meta:
        verbose_name = 'Позиція замовлення'
        verbose_name_plural = 'Позиції замовлення'

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.name} × {self.quantity}'
