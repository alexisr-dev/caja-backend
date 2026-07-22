from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegistroView,
    LoginView,
    Login2FAView,
    LogoutView,
    PerfilView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    GoogleSignInView,
    UsuariosListView,
    UsuarioDetailView,
)

urlpatterns = [
    path('registro/',               RegistroView.as_view(),               name='auth-registro'),
    path('login/',                  LoginView.as_view(),                   name='auth-login'),
    path('login-2fa/',              Login2FAView.as_view(),                name='auth-login-2fa'),
    path('refresh/',                TokenRefreshView.as_view(),            name='auth-refresh'),
    path('logout/',                 LogoutView.as_view(),                  name='auth-logout'),
    path('perfil/',                 PerfilView.as_view(),                  name='auth-perfil'),
    path('password-reset-request/', PasswordResetRequestView.as_view(),   name='auth-password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(),   name='auth-password-reset-confirm'),
    path('google/',                 GoogleSignInView.as_view(),            name='auth-google'),
    path('usuarios/',               UsuariosListView.as_view(),            name='auth-usuarios-list'),
    path('usuarios/<int:pk>/',      UsuarioDetailView.as_view(),           name='auth-usuarios-detail'),
]
