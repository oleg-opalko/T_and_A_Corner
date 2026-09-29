from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AccountProfile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class AccountForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=32, required=False)
    city = forms.CharField(max_length=120, required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['username'].initial = user.username
        self.fields['email'].initial = user.email
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name

        profile = None
        try:
            profile = user.account_profile
        except AccountProfile.DoesNotExist:
            profile = None
        if profile:
            self.fields['phone'].initial = profile.phone
            self.fields['city'].initial = profile.city

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username and User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Користувач з таким іменем вже існує.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if email and User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Користувач з такою поштою вже існує.')
        return email

    def save(self):
        self.user.username = self.cleaned_data['username'].strip()
        self.user.email = self.cleaned_data['email'].strip()
        self.user.first_name = self.cleaned_data['first_name'].strip()
        self.user.last_name = self.cleaned_data['last_name'].strip()
        self.user.save(update_fields=['username', 'email', 'first_name', 'last_name'])

        profile = None
        try:
            profile = self.user.account_profile
        except AccountProfile.DoesNotExist:
            profile = None
        if profile is None:
            profile = AccountProfile.objects.create(user=self.user)
        profile.phone = self.cleaned_data['phone'].strip()
        profile.city = self.cleaned_data['city'].strip()
        profile.save(update_fields=['phone', 'city'])
        return self.user
