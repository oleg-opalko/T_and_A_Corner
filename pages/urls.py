from django.urls import path

from . import views

app_name = 'pages'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),
    path('account/', views.account, name='account'),
    path('favorite/<int:perfume_id>/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('fragrance-guide/', views.fragrance_guide, name='fragrance_guide'),
]
