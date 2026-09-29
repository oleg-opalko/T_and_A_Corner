from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from shop.models import Brand, Category, Perfume


class AccountProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alice',
            email='alice@example.com',
            password='StrongPass123!',
        )
        self.brand = Brand.objects.create(name='Account Brand')
        self.category = Category.objects.create(name='Account Category')
        self.perfume = Perfume.objects.create(
            name='Favorite Perfume',
            brand=self.brand,
            category=self.category,
            price=Decimal('199.00'),
            is_available=True,
        )

    def test_account_page_allows_editing_user_data(self):
        self.client.login(username='alice', password='StrongPass123!')

        response = self.client.post(reverse('pages:account'), {
            'username': 'alice-updated',
            'email': 'alice.updated@example.com',
            'first_name': 'Alice',
            'last_name': 'Updated',
            'phone': '+380991234567',
            'city': 'Київ',
        })

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'alice-updated')
        self.assertEqual(self.user.email, 'alice.updated@example.com')
        self.assertEqual(self.user.first_name, 'Alice')
        self.assertEqual(self.user.last_name, 'Updated')

    def test_account_page_lists_user_favorites(self):
        self.client.login(username='alice', password='StrongPass123!')
        response = self.client.post(reverse('pages:toggle_favorite', args=[self.perfume.pk]), {
            'next': reverse('pages:account'),
        })

        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('pages:account'))
        self.assertContains(response, 'Favorite Perfume')

    def test_home_page_marks_favorite_products_for_authenticated_user(self):
        self.perfume.is_featured = True
        self.perfume.save(update_fields=['is_featured'])

        self.client.login(username='alice', password='StrongPass123!')
        response = self.client.post(reverse('pages:toggle_favorite', args=[self.perfume.pk]), {
            'next': reverse('pages:home'),
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('pages:home'))
        self.assertContains(response, '♥')

    def test_toggle_favorite_supports_ajax_json_response(self):
        self.client.login(username='alice', password='StrongPass123!')

        response = self.client.post(
            reverse('pages:toggle_favorite', args=[self.perfume.pk]),
            {'next': reverse('pages:account')},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['is_favorite'])
        self.assertIn('додано', payload['message'])

        response = self.client.post(
            reverse('pages:toggle_favorite', args=[self.perfume.pk]),
            {'next': reverse('pages:account')},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertFalse(payload['is_favorite'])
        self.assertIn('видалено', payload['message'])
