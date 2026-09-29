import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .formatting import format_uah
from .models import Order

logger = logging.getLogger(__name__)


def send_order_emails(order_id):
    """Send transactional notifications after a successfully saved order."""
    order = Order.objects.prefetch_related('items').get(pk=order_id)
    items = list(order.items.all())
    lines = '\n'.join(
        f'— {item.name} × {item.quantity}: {format_uah(item.subtotal)}'
        for item in items
    )
    common_details = (
        f'Замовлення №{order.pk}\n\n'
        f'Клієнт: {order.full_name}\n'
        f'Телефон: {order.phone}\n'
        f'Email: {order.email}\n'
        f'Доставка: {order.get_delivery_method_display()}\n'
        f'Місто: {order.city}\n'
        f'Адреса / відділення: {order.delivery_address}\n'
        f'Оплата: {order.get_payment_method_display()}\n'
        f'Коментар: {order.comment or "—"}\n\n'
        f'Товари:\n{lines}\n\n'
        f'Сума товарів: {format_uah(order.subtotal)}'
    )
    context = {'order': order, 'items': items}

    try:
        if settings.ORDER_NOTIFICATION_EMAIL:
            send_mail(
                subject=f'Нове замовлення №{order.pk} — T&A Corner',
                message=common_details,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ORDER_NOTIFICATION_EMAIL],
                html_message=render_to_string('emails/order_owner.html', context),
            )

        send_mail(
            subject=f'Ми отримали ваше замовлення №{order.pk} — T&A Corner',
            message=(
                f'Вітаємо, {order.full_name}!\n\n'
                'Дякуємо за замовлення. Ми зв’яжемося з вами найближчим часом, '
                'щоб підтвердити доставку та оплату.\n\n'
                f'{common_details}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            html_message=render_to_string('emails/order_customer.html', context),
        )
    except Exception:
        # An order must remain saved even when an email provider is temporarily unavailable.
        logger.exception('Не вдалося надіслати листи для замовлення №%s', order.pk)
