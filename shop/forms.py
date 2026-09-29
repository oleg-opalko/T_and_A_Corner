import re

from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    city_ref = forms.CharField(required=False, widget=forms.HiddenInput())
    warehouse_ref = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Order
        fields = (
            'full_name', 'phone', 'email', 'delivery_method', 'city',
            'delivery_address', 'payment_method', 'comment',
        )
        widgets = {
            'full_name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'phone': forms.TextInput(attrs={'autocomplete': 'tel', 'inputmode': 'tel'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'city': forms.TextInput(attrs={
                'autocomplete': 'off',
                'data-np-city': 'true',
            }),
            'delivery_address': forms.TextInput(attrs={
                'autocomplete': 'off',
                'data-np-warehouse': 'true',
            }),
            'delivery_method': forms.Select(),
            'payment_method': forms.Select(),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].choices = [
            (Order.PaymentMethod.CARD, 'Оплата карткою онлайн'),
            (Order.PaymentMethod.COD, 'Післяплата'),
        ]

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = re.sub(r'\D', '', phone)

        if digits.startswith('380') and len(digits) == 12:
            normalized = f'+{digits}'
        elif digits.startswith('0') and len(digits) == 10:
            normalized = f'+38{digits}'
        elif digits.startswith('80') and len(digits) == 11:
            normalized = f'+3{digits}'
        else:
            raise forms.ValidationError('Вкажіть український номер телефону у форматі +380XXXXXXXXX.')

        return normalized

    def clean(self):
        cleaned_data = super().clean()
        delivery_method = cleaned_data.get('delivery_method')
        city = (cleaned_data.get('city') or '').strip()
        delivery_address = (cleaned_data.get('delivery_address') or '').strip()
        city_ref = (cleaned_data.get('city_ref') or '').strip()
        warehouse_ref = (cleaned_data.get('warehouse_ref') or '').strip()

        if delivery_method == Order.DeliveryMethod.NOVA_POSHTA:
            if not city_ref:
                self.add_error('city', 'Оберіть місто зі списку Нової пошти.')
            if not warehouse_ref:
                self.add_error('delivery_address', 'Оберіть відділення зі списку Нової пошти.')
        elif delivery_method == Order.DeliveryMethod.PICKUP:
            cleaned_data['city'] = city or 'Самовивіз'
            cleaned_data['delivery_address'] = delivery_address or 'Самовивіз'
        else:
            if not city:
                self.add_error('city', 'Вкажіть місто для кур’єрської доставки.')
            if not delivery_address:
                self.add_error('delivery_address', 'Вкажіть адресу доставки.')

        return cleaned_data
