import base64
import hashlib
import json

from django.conf import settings
from django.urls import reverse


SUCCESS_STATUSES = {'success', 'sandbox'}
FAILURE_STATUSES = {'failure', 'error', 'reversed'}
CANCELLED_STATUSES = {'cancelled'}


def is_configured():
    return bool(settings.LIQPAY_PUBLIC_KEY and settings.LIQPAY_PRIVATE_KEY)


def encode_data(payload):
    raw = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


def decode_data(data):
    raw = base64.b64decode(data).decode('utf-8')
    return json.loads(raw)


def make_signature(data):
    sign_string = f'{settings.LIQPAY_PRIVATE_KEY}{data}{settings.LIQPAY_PRIVATE_KEY}'.encode('utf-8')
    digest = hashlib.sha3_256(sign_string).digest()
    return base64.b64encode(digest).decode('ascii')


def verify_signature(data, signature):
    return bool(data and signature and make_signature(data) == signature)


def make_order_id(order):
    return f'ta-order-{order.pk}'


def build_checkout_payload(order, request):
    result_url = request.build_absolute_uri(reverse('shop:payment_return', args=[order.pk]))
    server_url = request.build_absolute_uri(reverse('shop:liqpay_callback'))
    payload = {
        'public_key': settings.LIQPAY_PUBLIC_KEY,
        'version': 7,
        'action': 'pay',
        'amount': str(order.subtotal),
        'currency': settings.LIQPAY_CURRENCY,
        'description': f'T&A Corner — замовлення №{order.pk}',
        'order_id': make_order_id(order),
        'result_url': result_url,
        'server_url': server_url,
        'language': 'uk',
    }
    data = encode_data(payload)
    return {
        'checkout_url': settings.LIQPAY_CHECKOUT_URL,
        'data': data,
        'signature': make_signature(data),
        'payload': payload,
    }
