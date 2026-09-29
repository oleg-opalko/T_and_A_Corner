import json
import ssl
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, F, IntegerField, Value, When
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from pages.models import UserFavorite

from .cart import get_cart, get_cart_quantity, save_cart
from .emails import send_order_emails
from .forms import CheckoutForm
from .liqpay import (
    CANCELLED_STATUSES,
    FAILURE_STATUSES,
    SUCCESS_STATUSES,
    build_checkout_payload,
    decode_data,
    is_configured as liqpay_is_configured,
    make_order_id,
    verify_signature,
)
from .models import Brand, Category, Order, OrderItem, Perfume, PerfumeVariant


def _get_ssl_context():
    if not settings.NOVA_POSHTA_VERIFY_SSL:
        return ssl._create_unverified_context()

    try:
        import certifi
    except ImportError:
        return None

    return ssl.create_default_context(cafile=certifi.where())


def _send_nova_poshta_request(payload):
    request_data = json.dumps(payload).encode('utf-8')
    request = Request(
        settings.NOVA_POSHTA_API_URL,
        data=request_data,
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=10, context=_get_ssl_context()) as response:
        return json.loads(response.read().decode('utf-8'))


@require_GET
def nova_poshta_autofill(request):
    lookup_type = request.GET.get('type', 'city')
    query = request.GET.get('q', '').strip()
    limit = '20'
    if lookup_type == 'city':
        if len(query) < 2:
            return JsonResponse({'items': []})
    elif lookup_type == 'warehouse':
        city_ref = request.GET.get('city_ref', '').strip()
        if not city_ref:
            return JsonResponse({'items': []})
    else:
        return JsonResponse({'items': []})

    api_key = settings.NOVA_POSHTA_API_KEY
    if not api_key:
        response = {'items': []}
        if settings.DEBUG:
            response['error'] = 'NOVA_POSHTA_API_KEY is not configured'
        return JsonResponse(response)

    try:
        if lookup_type == 'city':
            cache_key = f'np:city:{query.lower()}'
            cached_items = cache.get(cache_key)
            if cached_items is not None:
                return JsonResponse({'items': cached_items})
            payload = {
                'apiKey': api_key,
                'modelName': 'Address',
                'calledMethod': 'getCities',
                'methodProperties': {
                    'FindByString': query,
                    'Limit': limit,
                    'Page': '1',
                    'Language': 'uk',
                },
            }
            response_data = _send_nova_poshta_request(payload)
            if not response_data.get('success', True):
                error = '; '.join(response_data.get('errors') or ['Нова пошта тимчасово не повернула міста.'])
                return JsonResponse({'items': [], 'error': error})
            items = [
                {
                    'name': item.get('Description', ''),
                    'ref': item.get('Ref', ''),
                    'area': item.get('AreaDescription') or item.get('Area', ''),
                }
                for item in response_data.get('data', [])
                if item.get('Description') and item.get('Ref')
            ]
            cache.set(cache_key, items, 60 * 60 * 6)
        else:
            cache_key = f'np:warehouse:{city_ref}:{query.lower()}'
            cached_items = cache.get(cache_key)
            if cached_items is not None:
                return JsonResponse({'items': cached_items})
            method_properties = {
                'CityRef': city_ref,
                'Limit': limit,
                'Page': '1',
                'Language': 'uk',
            }
            if query:
                method_properties['FindByString'] = query
            payload = {
                'apiKey': api_key,
                'modelName': 'AddressGeneral',
                'calledMethod': 'getWarehouses',
                'methodProperties': method_properties,
            }
            response_data = _send_nova_poshta_request(payload)
            if not response_data.get('success', True):
                error = '; '.join(response_data.get('errors') or ['Нова пошта тимчасово не повернула відділення.'])
                return JsonResponse({'items': [], 'error': error})
            items = [
                {
                    'name': item.get('Description') or item.get('ShortAddress') or '',
                    'ref': item.get('Ref', ''),
                }
                for item in response_data.get('data', [])
                if item.get('Description') or item.get('ShortAddress')
            ]
            cache.set(cache_key, items, 60 * 60 * 6)
    except (HTTPError, URLError, ValueError) as error:
        items = []
        if settings.DEBUG:
            return JsonResponse({'items': items, 'error': str(error)})

    return JsonResponse({'items': items})


def catalog(request):
    perfumes = (
        Perfume.objects.filter(is_available=True)
        .select_related('brand', 'category').prefetch_related('variants')
    )
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(UserFavorite.objects.filter(user=request.user).values_list('perfume_id', flat=True))
    categories = Category.objects.all()
    brands = Brand.objects.all()

    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_brand = request.GET.get('brand', '').strip()
    price_min = request.GET.get('price_min', '').strip()
    price_max = request.GET.get('price_max', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    if search_query:
        perfumes = perfumes.filter(
            name__icontains=search_query,
        )

    if selected_category:
        perfumes = perfumes.filter(category__slug=selected_category)
    if selected_brand:
        perfumes = perfumes.filter(brand__slug=selected_brand)
    if price_min:
        try:
            perfumes = perfumes.filter(price__gte=Decimal(price_min))
        except (ArithmeticError, InvalidOperation):
            price_min = ''
    if price_max:
        try:
            perfumes = perfumes.filter(price__lte=Decimal(price_max))
        except (ArithmeticError, InvalidOperation):
            price_max = ''

    sort_options = {
        'newest': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'name': 'name',
    }
    priority = Case(
        When(regular_price__gt=F('price'), then=Value(0)),
        When(is_new=True, then=Value(1)),
        When(is_bestseller=True, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    perfumes = perfumes.annotate(priority=priority).order_by('priority', sort_options.get(sort, '-created_at'))

    return render(request, 'shop/catalog.html', {
        'perfumes': perfumes,
        'categories': categories,
        'brands': brands,
        'favorite_ids': favorite_ids,
        'filters': {
            'q': search_query,
            'category': selected_category,
            'brand': selected_brand,
            'price_min': price_min,
            'price_max': price_max,
            'sort': sort if sort in sort_options else 'newest',
        },
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    perfumes = category.perfumes.filter(is_available=True).select_related('brand').prefetch_related('variants').order_by(
        Case(
            When(regular_price__gt=F('price'), then=Value(0)),
            When(is_new=True, then=Value(1)),
            When(is_bestseller=True, then=Value(2)),
            default=Value(3), output_field=IntegerField(),
        ),
        '-created_at',
    )
    return render(request, 'shop/category.html', {
        'category': category,
        'perfumes': perfumes,
    })


def perfume_detail(request, slug):
    perfume = get_object_or_404(
        Perfume.objects.select_related('brand', 'category').prefetch_related('variants'),
        slug=slug,
        is_available=True,
    )
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(UserFavorite.objects.filter(user=request.user).values_list('perfume_id', flat=True))
    variants = [variant for variant in perfume.variants.all() if variant.is_available]
    related_perfumes = (
        Perfume.objects.filter(is_available=True)
        .select_related('brand', 'category').prefetch_related('variants')
        .exclude(pk=perfume.pk)
        .filter(category=perfume.category)
        [:4]
    )
    return render(request, 'shop/perfume_detail.html', {
        'perfume': perfume,
        'variants': variants,
        'related_perfumes': related_perfumes,
        'favorite_ids': favorite_ids,
    })


@require_POST
def cart_add(request, perfume_id):
    perfume = get_object_or_404(Perfume, pk=perfume_id, is_available=True)
    variant_id = request.POST.get('variant_id')
    variant = None
    if variant_id:
        variant = get_object_or_404(PerfumeVariant, pk=variant_id, perfume=perfume, is_available=True)
    cart = get_cart(request)
    product_id = f'{perfume.pk}:{variant.pk}' if variant else str(perfume.pk)
    cart[product_id] = int(cart.get(product_id, 0)) + 1
    save_cart(request, cart)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'cart_quantity': get_cart_quantity(request),
            'message': f'«{perfume.name}» додано до кошика.',
        })
    messages.success(request, f'«{perfume.name}» додано до кошика.')
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect('shop:cart_detail')


def cart_detail(request):
    items, total = get_cart_items(request)

    return render(request, 'shop/cart.html', {'items': items, 'total': total})


def get_cart_items(request):
    """Build cart rows from products that are still available."""
    cart = get_cart(request)
    product_ids = []
    variant_ids = []
    for key in cart:
        product_id, _, variant_id = key.partition(':')
        if product_id.isdigit():
            product_ids.append(int(product_id))
        if variant_id.isdigit():
            variant_ids.append(int(variant_id))
    perfumes = {
        perfume.pk: perfume
        for perfume in Perfume.objects.filter(pk__in=product_ids, is_available=True).select_related('brand')
    }
    variants = {
        variant.pk: variant
        for variant in PerfumeVariant.objects.filter(pk__in=variant_ids, is_available=True).select_related('perfume')
    }
    items = []
    total = Decimal('0.00')
    valid_ids = set()
    for key, quantity in cart.items():
        product_id, _, variant_id = key.partition(':')
        perfume = perfumes.get(int(product_id)) if product_id.isdigit() else None
        variant = variants.get(int(variant_id)) if variant_id.isdigit() else None
        if not perfume or (variant and variant.perfume_id != perfume.pk):
            continue
        unit_price = variant.price if variant else perfume.price
        quantity = int(quantity)
        subtotal = unit_price * quantity
        items.append({'perfume': perfume, 'variant': variant, 'price': unit_price, 'quantity': quantity, 'subtotal': subtotal, 'cart_key': key})
        total += subtotal
        valid_ids.add(key)

    if set(cart) != valid_ids:
        save_cart(request, {key: cart[key] for key in valid_ids})
    return items, total


@require_POST
def cart_update(request, cart_key):
    cart = get_cart(request)
    if cart_key in cart:
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        if quantity > 0:
            cart[cart_key] = min(quantity, 99)
        else:
            del cart[cart_key]
        save_cart(request, cart)
    return redirect('shop:cart_detail')


@require_POST
def cart_remove(request, cart_key):
    cart = get_cart(request)
    cart.pop(cart_key, None)
    save_cart(request, cart)
    return redirect('shop:cart_detail')


def checkout(request):
    items, total = get_cart_items(request)
    if not items:
        messages.info(request, 'Додайте товар до кошика, щоб оформити замовлення.')
        return redirect('shop:cart_detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.subtotal = total
                if order.requires_online_payment:
                    order.payment_status = Order.PaymentStatus.PENDING
                order.save()
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        perfume=item['perfume'],
                        variant=item['variant'],
                        name=f"{item['perfume'].name} ({item['variant'].volume_ml if item['variant'] else item['perfume'].volume_ml} мл)",
                        price=item['price'],
                        quantity=item['quantity'],
                    )
                    for item in items
                ])
                save_cart(request, {})
                transaction.on_commit(lambda order_id=order.pk: send_order_emails(order_id))
            if order.requires_online_payment:
                return redirect('shop:payment_start', order_id=order.pk)
            return redirect('shop:checkout_success', order_id=order.pk)
    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {'form': form, 'items': items, 'total': total})


def checkout_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'shop/checkout_success.html', {'order': order})


def payment_start(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if not order.requires_online_payment:
        return redirect('shop:checkout_success', order_id=order.pk)
    if order.payment_status == Order.PaymentStatus.PAID:
        return redirect('shop:checkout_success', order_id=order.pk)
    if not liqpay_is_configured():
        messages.error(request, 'Онлайн-оплата тимчасово недоступна. Ми зв’яжемося з вами для уточнення оплати.')
        return redirect('shop:checkout_success', order_id=order.pk)

    payment = build_checkout_payload(order, request)
    return render(request, 'shop/payment_start.html', {'order': order, 'payment': payment})


def payment_return(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'shop/payment_return.html', {'order': order})


@csrf_exempt
@require_POST
def liqpay_callback(request):
    data = request.POST.get('data', '')
    signature = request.POST.get('signature', '')
    if not verify_signature(data, signature):
        return HttpResponseBadRequest('Invalid signature')

    payload = decode_data(data)
    order_id = payload.get('order_id', '')
    if not order_id.startswith('ta-order-'):
        return HttpResponseBadRequest('Invalid order_id')

    order = get_object_or_404(Order, pk=order_id.removeprefix('ta-order-'))
    if order_id != make_order_id(order):
        return HttpResponseBadRequest('Invalid order reference')

    payment_status = payload.get('status', '')
    order.payment_provider_order_id = order_id
    order.payment_transaction_id = str(payload.get('transaction_id') or payload.get('payment_id') or '')
    order.payment_payload = payload

    if payment_status in SUCCESS_STATUSES:
        order.payment_status = Order.PaymentStatus.PAID
        order.status = Order.Status.PAID
    elif payment_status in FAILURE_STATUSES:
        order.payment_status = Order.PaymentStatus.FAILED
    elif payment_status in CANCELLED_STATUSES:
        order.payment_status = Order.PaymentStatus.CANCELLED
    else:
        order.payment_status = Order.PaymentStatus.PENDING

    order.save(update_fields=[
        'payment_status', 'payment_provider_order_id', 'payment_transaction_id',
        'payment_payload', 'status', 'updated_at',
    ])
    return JsonResponse({'ok': True})
