from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from shop.models import Perfume

from .forms import AccountForm, RegistrationForm
from .models import AccountProfile, UserFavorite


def _get_user_favorite_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(
        UserFavorite.objects.filter(user=user).values_list('perfume_id', flat=True)
    )


def home(request):
    featured_perfumes = (
        Perfume.objects.filter(is_available=True, is_featured=True)
        .select_related('brand', 'category')[:4]
    )
    if not featured_perfumes:
        featured_perfumes = (
            Perfume.objects.filter(is_available=True)
            .select_related('brand', 'category')[:4]
        )
    favorite_ids = _get_user_favorite_ids(request.user)
    return render(request, 'pages/home.html', {
        'featured_perfumes': featured_perfumes,
        'favorite_ids': favorite_ids,
    })


def about(request):
    return render(request, 'pages/about.html')


def contact(request):
    return render(request, 'pages/contact.html')


def fragrance_guide(request):
    return render(request, 'pages/fragrance_guide.html')


def login_page(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password'),
            )
            if user is not None:
                login(request, user)
                messages.success(request, 'Вхід виконано успішно.')
                return redirect('pages:home')
    else:
        form = AuthenticationForm()
    return render(request, 'pages/login.html', {'form': form})


def logout_page(request):
    logout(request)
    messages.info(request, 'Ви вийшли з облікового запису.')
    return redirect('pages:home')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Реєстрація успішна. Вітаємо в T&A Corner!')
            return redirect('pages:home')
    else:
        form = RegistrationForm()
    return render(request, 'pages/register.html', {'form': form})


@login_required
def account(request):
    profile, _ = AccountProfile.objects.get_or_create(user=request.user)
    favorites = Perfume.objects.filter(
        favorite_records__user=request.user,
    ).select_related('brand', 'category')
    favorite_ids = _get_user_favorite_ids(request.user)

    if request.method == 'POST':
        form = AccountForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваші дані успішно оновлено.')
            return redirect('pages:account')
    else:
        form = AccountForm(request.user)

    return render(request, 'pages/account.html', {
        'form': form,
        'profile': profile,
        'favorites': favorites,
        'favorite_ids': favorite_ids,
    })


@login_required
@require_POST
def toggle_favorite(request, perfume_id):
    perfume = get_object_or_404(Perfume, pk=perfume_id, is_available=True)
    user_favorite, created = UserFavorite.objects.get_or_create(user=request.user, perfume=perfume)
    if not created:
        user_favorite.delete()
        is_favorite = False
        message = 'Товар видалено з улюблених.'
    else:
        is_favorite = True
        message = 'Товар додано до улюблених.'

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'is_favorite': is_favorite,
            'message': message,
        })

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect('pages:account')

