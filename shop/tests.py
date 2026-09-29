from decimal import Decimal
from unittest.mock import Mock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .liqpay import encode_data, make_signature
from .models import Brand, Category, Order, Perfume, PerfumeVariant


class PerfumeImportAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_login(self.user)

    def test_csv_import_creates_and_updates_product(self):
        url = reverse('admin:shop_perfume_import')
        csv_data = (
            'name,brand,category,price,slug,volume_ml,is_available\n'
            'Test perfume,Test brand,Test category,199.50,test-perfume,100,false\n'
        )
        response = self.client.post(url, {'csv_file': SimpleUploadedFile('products.csv', csv_data.encode())})
        self.assertRedirects(response, reverse('admin:shop_perfume_changelist'))
        perfume = Perfume.objects.get(slug='test-perfume')
        self.assertEqual(perfume.price, Decimal('199.50'))
        self.assertEqual(perfume.volume_ml, 100)
        self.assertFalse(perfume.is_available)

        updated_csv = csv_data.replace('199.50', '250')
        self.client.post(url, {'csv_file': SimpleUploadedFile('products.csv', updated_csv.encode())})
        self.assertEqual(Perfume.objects.count(), 1)
        self.assertEqual(Perfume.objects.get().price, Decimal('250'))


class CartTests(TestCase):
    def setUp(self):
        brand = Brand.objects.create(name='Test Brand')
        category = Category.objects.create(name='Test Category')
        self.perfume = Perfume.objects.create(
            name='Test Perfume', brand=brand, category=category,
            price=Decimal('125.00'),
        )

    def test_add_product_and_show_total(self):
        response = self.client.post(
            reverse('shop:cart_add', args=[self.perfume.pk]),
            {'next': reverse('shop:catalog')},
        )
        self.assertRedirects(response, reverse('shop:catalog'))
        response = self.client.get(reverse('shop:cart_detail'))
        self.assertContains(response, 'Test Perfume')
        self.assertContains(response, '125,00 грн')
        self.assertEqual(response.context['total'], Decimal('125.00'))

    def test_update_and_remove_product(self):
        session = self.client.session
        session['cart'] = {str(self.perfume.pk): 1}
        session.save()
        self.client.post(reverse('shop:cart_update', args=[self.perfume.pk]), {'quantity': 3})
        response = self.client.get(reverse('shop:cart_detail'))
        self.assertEqual(response.context['total'], Decimal('375.00'))
        self.client.post(reverse('shop:cart_remove', args=[self.perfume.pk]))
        response = self.client.get(reverse('shop:cart_detail'))
        self.assertFalse(response.context['items'])

    def test_ajax_add_returns_updated_cart_quantity(self):
        response = self.client.post(
            reverse('shop:cart_add', args=[self.perfume.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            'ok': True,
            'cart_quantity': 1,
            'message': '«Test Perfume» додано до кошика.',
        })

    def test_cart_uses_selected_volume_variant_price(self):
        variant = PerfumeVariant.objects.create(perfume=self.perfume, volume_ml=100, price=Decimal('210.00'))
        response = self.client.post(reverse('shop:cart_add', args=[self.perfume.pk]), {'variant_id': variant.pk})

        self.assertRedirects(response, reverse('shop:cart_detail'))
        response = self.client.get(reverse('shop:cart_detail'))
        self.assertEqual(response.context['total'], Decimal('210.00'))
        self.assertEqual(response.context['items'][0]['variant'], variant)

    def test_checkout_creates_order_and_clears_cart(self):
        session = self.client.session
        session['cart'] = {str(self.perfume.pk): 2}
        session.save()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('shop:checkout'), {
                'full_name': 'Ірина Тестова',
                'phone': '+380991234567',
                'email': 'iryna@example.com',
                'delivery_method': 'nova_poshta',
                'city': 'Київ',
                'city_ref': 'city-ref-1',
                'delivery_address': 'Відділення №1',
                'warehouse_ref': 'warehouse-ref-1',
                'payment_method': 'cod',
                'comment': 'Зателефонуйте перед відправленням',
            })
        order = Order.objects.get()
        self.assertRedirects(response, reverse('shop:checkout_success', args=[order.pk]))
        self.assertEqual(order.subtotal, Decimal('250.00'))
        self.assertEqual(order.phone, '+380991234567')
        self.assertEqual(order.items.get().quantity, 2)
        self.assertFalse(self.client.session.get('cart'))

    def test_checkout_requires_nova_poshta_selection_refs(self):
        session = self.client.session
        session['cart'] = {str(self.perfume.pk): 1}
        session.save()
        response = self.client.post(reverse('shop:checkout'), {
            'full_name': 'Ірина Тестова',
            'phone': '+380991234567',
            'email': 'iryna@example.com',
            'delivery_method': 'nova_poshta',
            'city': 'Київ',
            'delivery_address': 'Відділення №1',
            'payment_method': 'cod',
            'comment': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'city', 'Оберіть місто зі списку Нової пошти.')
        self.assertFormError(response.context['form'], 'delivery_address', 'Оберіть відділення зі списку Нової пошти.')
        self.assertFalse(Order.objects.exists())

    def test_checkout_accepts_courier_manual_address(self):
        session = self.client.session
        session['cart'] = {str(self.perfume.pk): 1}
        session.save()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('shop:checkout'), {
                'full_name': 'Ірина Тестова',
                'phone': '099 123 45 67',
                'email': 'iryna@example.com',
                'delivery_method': 'courier',
                'city': 'Львів',
                'delivery_address': 'вул. Тестова, 1',
                'payment_method': 'cod',
                'comment': '',
            })
        order = Order.objects.get()
        self.assertRedirects(response, reverse('shop:checkout_success', args=[order.pk]))
        self.assertEqual(order.phone, '+380991234567')

    def test_card_checkout_redirects_to_payment_start(self):
        session = self.client.session
        session['cart'] = {str(self.perfume.pk): 1}
        session.save()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('shop:checkout'), {
                'full_name': 'Ірина Тестова',
                'phone': '+380991234567',
                'email': 'iryna@example.com',
                'delivery_method': 'courier',
                'city': 'Львів',
                'delivery_address': 'вул. Тестова, 1',
                'payment_method': 'card',
                'comment': '',
            })
        order = Order.objects.get()
        self.assertRedirects(response, reverse('shop:payment_start', args=[order.pk]), fetch_redirect_response=False)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

    @override_settings(LIQPAY_PUBLIC_KEY='public-key', LIQPAY_PRIVATE_KEY='private-key')
    def test_payment_start_renders_liqpay_form(self):
        order = Order.objects.create(
            full_name='Ірина Тестова',
            phone='+380991234567',
            email='iryna@example.com',
            delivery_method='courier',
            city='Львів',
            delivery_address='вул. Тестова, 1',
            payment_method='card',
            payment_status=Order.PaymentStatus.PENDING,
            subtotal=Decimal('125.00'),
        )
        response = self.client.get(reverse('shop:payment_start', args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://www.liqpay.ua/api/3/checkout')
        self.assertContains(response, 'name="data"')
        self.assertContains(response, 'name="signature"')

    @override_settings(LIQPAY_PUBLIC_KEY='public-key', LIQPAY_PRIVATE_KEY='private-key')
    def test_liqpay_callback_marks_order_paid(self):
        order = Order.objects.create(
            full_name='Ірина Тестова',
            phone='+380991234567',
            email='iryna@example.com',
            delivery_method='courier',
            city='Львів',
            delivery_address='вул. Тестова, 1',
            payment_method='card',
            payment_status=Order.PaymentStatus.PENDING,
            subtotal=Decimal('125.00'),
        )
        data = encode_data({
            'order_id': f'ta-order-{order.pk}',
            'status': 'success',
            'transaction_id': 'txn-1',
        })
        response = self.client.post(reverse('shop:liqpay_callback'), {
            'data': data,
            'signature': make_signature(data),
        })
        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.payment_transaction_id, 'txn-1')

    @override_settings(LIQPAY_PUBLIC_KEY='public-key', LIQPAY_PRIVATE_KEY='private-key')
    def test_liqpay_callback_rejects_invalid_signature(self):
        data = encode_data({'order_id': 'ta-order-1', 'status': 'success'})
        response = self.client.post(reverse('shop:liqpay_callback'), {
            'data': data,
            'signature': 'bad-signature',
        })
        self.assertEqual(response.status_code, 400)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='shop@example.com',
        ORDER_NOTIFICATION_EMAIL='owner@example.com',
    )
    def test_checkout_sends_owner_and_customer_emails(self):
        session = self.client.session
        session['cart'] = {str(self.perfume.pk): 1}
        session.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('shop:checkout'), {
                'full_name': 'Ірина Тестова', 'phone': '+380991234567',
                'email': 'iryna@example.com', 'delivery_method': 'nova_poshta',
                'city': 'Київ', 'city_ref': 'city-ref-1',
                'delivery_address': 'Відділення №1', 'warehouse_ref': 'warehouse-ref-1',
                'payment_method': 'cod', 'comment': '',
            })
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('owner@example.com', mail.outbox[0].to)
        self.assertIn('iryna@example.com', mail.outbox[1].to)
        self.assertIn('html', mail.outbox[0].alternatives[0][1])
        self.assertIn('html', mail.outbox[1].alternatives[0][1])

    @override_settings(NOVA_POSHTA_API_KEY='test-key')
    @patch('shop.views._send_nova_poshta_request')
    def test_nova_poshta_autofill_city_returns_items(self, mock_request):
        mock_request.return_value = {
            'data': [
                {'Description': 'Київ', 'Ref': 'city-ref-1', 'AreaDescription': 'Київська'},
                {'Description': 'Бровари', 'Ref': 'city-ref-2', 'AreaDescription': 'Київська'},
            ]
        }
        response = self.client.get(reverse('shop:nova_poshta_autofill'), {'type': 'city', 'q': 'Киє'})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            'items': [
                {'name': 'Київ', 'ref': 'city-ref-1', 'area': 'Київська'},
                {'name': 'Бровари', 'ref': 'city-ref-2', 'area': 'Київська'},
            ],
        })

    @override_settings(DEBUG=True, NOVA_POSHTA_API_KEY='')
    def test_nova_poshta_autofill_reports_missing_key_in_debug(self):
        response = self.client.get(reverse('shop:nova_poshta_autofill'), {'type': 'city', 'q': 'Ки'})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            'items': [],
            'error': 'NOVA_POSHTA_API_KEY is not configured',
        })

    @override_settings(NOVA_POSHTA_VERIFY_SSL=False)
    @patch('shop.views.ssl._create_unverified_context')
    def test_nova_poshta_uses_unverified_ssl_context_when_disabled(self, mock_context):
        context = Mock()
        mock_context.return_value = context
        from .views import _get_ssl_context

        self.assertIs(_get_ssl_context(), context)

    def test_perfume_detail_shows_notes_availability_and_recommendations(self):
        brand = Brand.objects.create(name='Recommended Brand')
        category = Category.objects.create(name='Recommended Category')
        related_perfume = Perfume.objects.create(
            name='Recommended Perfume',
            brand=brand,
            category=category,
            price=Decimal('210.00'),
            volume_ml=100,
            notes_top='Гвоздика, бергамот',
            notes_middle='Троянда, пачулі',
            notes_base='Ваніль, мускус',
            description='Літній, м’який і витончений аромат.',
            is_available=True,
            gallery=['/media/gallery-1.jpg', '/media/gallery-2.jpg'],
        )
        primary_perfume = Perfume.objects.create(
            name='Signature Perfume',
            brand=brand,
            category=category,
            price=Decimal('260.00'),
            volume_ml=50,
            notes_top='Апельсин, мигдаль',
            notes_middle='Суцвіття троянди',
            notes_base='Деревні акорди',
            description='Елегантний аромат для вечірніх виходів.',
            is_available=True,
            gallery=['/media/gallery-3.jpg'],
        )

        response = self.client.get(reverse('shop:perfume_detail', args=[primary_perfume.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ноти аромату')
        self.assertContains(response, 'У наявності')
        self.assertContains(response, '100 ml')
        self.assertContains(response, 'Вам також може сподобатись')
        self.assertContains(response, 'Recommended Perfume')

    def test_perfume_detail_shows_discount_for_selected_variant(self):
        brand = Brand.objects.create(name='Discount Brand')
        category = Category.objects.create(name='Discount Category')
        perfume = Perfume.objects.create(
            name='Discount Perfume',
            brand=brand,
            category=category,
            price=Decimal('900.00'),
            is_available=True,
        )
        PerfumeVariant.objects.create(
            perfume=perfume,
            volume_ml=50,
            price=Decimal('900.00'),
        )
        discounted_variant = PerfumeVariant.objects.create(
            perfume=perfume,
            volume_ml=100,
            price=Decimal('900.00'),
            regular_price=Decimal('1200.00'),
        )

        response = self.client.get(reverse('shop:perfume_detail', args=[perfume.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-current-price>900,00 грн</span>')
        self.assertContains(response, 'Знижка <span data-discount-percent>0</span>%')
        self.assertContains(response, 'data-regular-price="1 200,00 грн"')
        self.assertContains(response, f'data-discount-percent="{discounted_variant.discount_percent}"')
        self.assertEqual(discounted_variant.discount_percent, 25)

    def test_catalog_search_filters_results(self):
        brand = Brand.objects.create(name='Search Brand')
        category = Category.objects.create(name='Search Category')
        Perfume.objects.create(
            name='Amber Discovery',
            slug='amber-discovery',
            brand=brand,
            category=category,
            price=Decimal('140.00'),
            is_available=True,
        )
        Perfume.objects.create(
            name='Night Bloom',
            slug='night-bloom',
            brand=brand,
            category=category,
            price=Decimal('160.00'),
            is_available=True,
        )

        response = self.client.get(reverse('shop:catalog'), {'q': 'amber'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amber Discovery')
        self.assertNotContains(response, 'Night Bloom')

    def test_user_can_register(self):
        response = self.client.post(reverse('pages:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())

    @override_settings(NOVA_POSHTA_API_KEY='test-key')
    @patch('shop.views._send_nova_poshta_request')
    def test_nova_poshta_autofill_warehouse_returns_items(self, mock_request):
        mock_request.return_value = {
            'data': [
                {'Description': 'Відділення №1', 'ShortAddress': 'Відділення №1', 'Ref': 'warehouse-ref-1'},
                {'Description': 'Відділення №2', 'ShortAddress': 'Відділення №2', 'Ref': 'warehouse-ref-2'},
            ]
        }
        response = self.client.get(reverse('shop:nova_poshta_autofill'), {
            'type': 'warehouse', 'q': 'Від', 'city_ref': 'city-ref-1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            'items': [
                {'name': 'Відділення №1', 'ref': 'warehouse-ref-1'},
                {'name': 'Відділення №2', 'ref': 'warehouse-ref-2'},
            ],
        })


class CatalogTests(TestCase):
    def setUp(self):
        self.brand_a = Brand.objects.create(name='Brand A')
        self.brand_b = Brand.objects.create(name='Brand B')
        self.category_floral = Category.objects.create(name='Floral')
        self.category_woody = Category.objects.create(name='Woody')
        self.rose = Perfume.objects.create(
            name='Rose Light',
            brand=self.brand_a,
            category=self.category_floral,
            price=Decimal('1200.00'),
        )
        self.oud = Perfume.objects.create(
            name='Oud Night',
            brand=self.brand_b,
            category=self.category_woody,
            price=Decimal('2500.00'),
        )
        self.hidden = Perfume.objects.create(
            name='Hidden Scent',
            brand=self.brand_a,
            category=self.category_woody,
            price=Decimal('900.00'),
            is_available=False,
        )

    def test_catalog_filters_by_brand(self):
        response = self.client.get(reverse('shop:catalog'), {'brand': self.brand_a.slug})
        self.assertContains(response, 'Rose Light')
        self.assertNotContains(response, 'Oud Night')
        self.assertNotContains(response, 'Hidden Scent')

    def test_catalog_filters_by_category(self):
        response = self.client.get(reverse('shop:catalog'), {'category': self.category_woody.slug})
        self.assertContains(response, 'Oud Night')
        self.assertNotContains(response, 'Rose Light')

    def test_catalog_filters_by_price_range(self):
        response = self.client.get(reverse('shop:catalog'), {'price_min': '2000', 'price_max': '3000'})
        self.assertContains(response, 'Oud Night')
        self.assertNotContains(response, 'Rose Light')

    def test_catalog_sorts_by_price_ascending(self):
        response = self.client.get(reverse('shop:catalog'), {'sort': 'price_asc'})
        perfumes = list(response.context['perfumes'])
        self.assertEqual(perfumes, [self.rose, self.oud])

    def test_catalog_prioritizes_sale_new_and_bestseller_products(self):
        self.oud.regular_price = Decimal('3000.00')
        self.oud.save()
        self.rose.is_new = True
        self.rose.save()
        bestseller = Perfume.objects.create(
            name='Bestseller', brand=self.brand_a, category=self.category_floral,
            price=Decimal('1000.00'), is_bestseller=True,
        )

        response = self.client.get(reverse('shop:catalog'))

        self.assertEqual(list(response.context['perfumes']), [self.oud, self.rose, bestseller])
        self.assertContains(response, '-16%')
        self.assertContains(response, 'Новинка')
        self.assertContains(response, 'Хіт продажів')

    def test_catalog_shows_empty_state_for_no_matches(self):
        response = self.client.get(reverse('shop:catalog'), {'price_min': '99999'})
        self.assertContains(response, 'За цими фільтрами ароматів не знайдено.')
