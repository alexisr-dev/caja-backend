import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import IsAdmin
from .throttles import LoginThrottle, OtpSendThrottle, OtpVerifyThrottle
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .models import CustomUser, CodigoVerificacion2FA, TokenRecuperacionPassword, _hash_codigo
from .serializers import (
    UserSerializer,
    RegistroSerializer,
    LoginSerializer,
    Login2FASerializer,
    PerfilUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    GoogleSignInSerializer,
    UsuarioAdminSerializer,
    CrearUsuarioAdminSerializer,
)

logger = logging.getLogger(__name__)


def _enmascarar_email(email: str) -> str:
    """Devuelve 'al***@gmail.com' para no exponer el email completo en respuestas."""
    local, domain = email.split('@', 1)
    return f'{local[:2]}***@{domain}'


def _emitir_sesion(user: CustomUser, *, extra: dict | None = None) -> dict:
    refresh = RefreshToken.for_user(user)
    payload = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }
    if extra:
        payload.update(extra)
    return payload

@extend_schema(tags=['auth'])
class RegistroView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegistroSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_emitir_sesion(user), status=status.HTTP_201_CREATED)

@extend_schema(
    tags=['auth'],
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description='Tokens JWT (cliente) o {requiere_2fa: true} (admin/vendedor)'),
        401: OpenApiResponse(description='Credenciales inválidas'),
        403: OpenApiResponse(description='Cuenta desactivada'),
    },
)
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            logger.warning(
                'LOGIN_FAILED email=%s ip=%s',
                serializer.validated_data.get('email'),
                request.META.get('REMOTE_ADDR'),
            )
            return Response(
                {'detail': 'Credenciales invalidas', 'codigo': 'credenciales_invalidas'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {'detail': 'Cuenta desactivada', 'codigo': 'cuenta_inactiva'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.es_cliente:
            data = _emitir_sesion(user, extra={'requiere_2fa': False})
            return Response(data)

        return self._iniciar_2fa(user)

    @staticmethod
    def _iniciar_2fa(user: CustomUser) -> Response:
        codigo_obj, codigo_claro = CodigoVerificacion2FA.generar(user)
        try:
            send_mail(
                subject='Tu codigo de verificacion',
                message=(
                    f'Hola {user.first_name or user.email},\n\n'
                    f'Tu codigo de verificacion es: {codigo_claro}\n'
                    f'Expira en {CodigoVerificacion2FA.DURACION_MINUTOS} minutos.\n\n'
                    f'Si no fuiste tu, ignora este mensaje.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.exception('Fallo enviando email 2FA a %s: %s', user.email, exc)
            return Response(
                {'detail': 'No pudimos enviar el codigo. Intenta de nuevo.',
                 'codigo': 'email_falla'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        session_token = signing.dumps(
            {'uid': user.id},
            salt='2fa-login',
        )
        return Response({
            'requiere_2fa': True,
            'session_token': session_token,
            'mensaje': f'Codigo enviado a {_enmascarar_email(user.email)}',
        })

@extend_schema(tags=['auth'], request=Login2FASerializer, responses={200: UserSerializer})
class Login2FAView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OtpVerifyThrottle]

    def post(self, request):
        serializer = Login2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_token = serializer.validated_data['session_token']
        codigo_input = serializer.validated_data['codigo']

        try:
            data = signing.loads(
                session_token,
                salt='2fa-login',
                max_age=CodigoVerificacion2FA.DURACION_MINUTOS * 60,
            )
            user_id = data['uid']
        except (signing.BadSignature, signing.SignatureExpired, KeyError):
            logger.warning('2FA session_token invalido/expirado desde %s', request.META.get('REMOTE_ADDR'))
            return Response(
                {'detail': 'Sesion de verificacion invalida o expirada', 'codigo': 'sesion_invalida'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'Usuario invalido', 'codigo': 'usuario_invalido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {'detail': 'Cuenta desactivada', 'codigo': 'cuenta_inactiva'},
                status=status.HTTP_403_FORBIDDEN,
            )

        codigo_obj = (
            CodigoVerificacion2FA.objects
            .filter(usuario=user, codigo=_hash_codigo(codigo_input))
            .order_by('-creado')
            .first()
        )
        if not codigo_obj or not codigo_obj.es_valido():
            logger.warning('OTP_FAILED user_id=%s ip=%s', user_id, request.META.get('REMOTE_ADDR'))
            return Response(
                {'detail': 'Codigo invalido o expirado', 'codigo': 'codigo_2fa_invalido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        codigo_obj.usado = True
        codigo_obj.save(update_fields=['usado'])

        return Response(_emitir_sesion(user))

@extend_schema(tags=['auth'], responses={205: None})
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass
        return Response(status=status.HTTP_205_RESET_CONTENT)

@extend_schema(tags=['auth'])
@extend_schema_view(
    get=extend_schema(responses={200: UserSerializer}),
    patch=extend_schema(request=PerfilUpdateSerializer, responses={200: UserSerializer}),
)
class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = PerfilUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

@extend_schema(tags=['auth'], request=PasswordResetRequestSerializer, responses={200: OpenApiTypes.OBJECT})
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OtpSendThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = CustomUser.objects.filter(email=email).first()
        if user:
            self._enviar_codigo(user)

        return Response({
            'detail': 'Si el email esta registrado, recibiras un codigo en breve.',
        })

    @staticmethod
    def _enviar_codigo(user: CustomUser) -> None:
        _token_obj, codigo_claro = TokenRecuperacionPassword.generar(user)
        try:
            send_mail(
                subject='Recuperar tu contrasena',
                message=(
                    f'Hola {user.first_name or user.email},\n\n'
                    f'Tu codigo para resetear tu contrasena es: {codigo_claro}\n'
                    f'Expira en {TokenRecuperacionPassword.DURACION_MINUTOS} minutos.\n\n'
                    f'Si no fuiste tu, ignora este mensaje.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.exception('Fallo enviando email reset a %s: %s', user.email, exc)

@extend_schema(tags=['auth'], request=PasswordResetConfirmSerializer, responses={200: OpenApiTypes.OBJECT})
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OtpVerifyThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        codigo = serializer.validated_data['codigo']
        nueva_password = serializer.validated_data['nueva_password']

        token = (
            TokenRecuperacionPassword.objects
            .select_related('usuario')
            .filter(codigo=_hash_codigo(codigo))
            .first()
        )
        if not token or not token.es_valido():
            return Response(
                {'detail': 'Codigo invalido o expirado', 'codigo': 'codigo_invalido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user = token.usuario
            user.set_password(nueva_password)
            user.save(update_fields=['password'])
            token.usado = True
            token.save(update_fields=['usado'])
            for outstanding in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=outstanding)

        return Response({'detail': 'Contrasena actualizada con exito.'})

@extend_schema(tags=['auth'], request=GoogleSignInSerializer, responses={200: UserSerializer})
class GoogleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token

        token = serializer.validated_data['id_token']

        try:
            info = g_id_token.verify_oauth2_token(token, g_requests.Request())
        except ValueError:
            return Response(
                {'detail': 'Token de Google invalido o expirado', 'codigo': 'token_google_invalido'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if info.get('aud') not in settings.GOOGLE_OAUTH_CLIENT_IDS:
            logger.warning('Google audience no autorizado: %s', info.get('aud'))
            return Response(
                {'detail': 'audience no autorizado', 'codigo': 'audience_invalido'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not info.get('email_verified'):
            return Response(
                {'detail': 'Email no verificado por Google', 'codigo': 'email_no_verificado'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = info['email'].lower().strip()
        google_id = info['sub']
        first_name = info.get('given_name', '')
        last_name = info.get('family_name', '')
        picture = info.get('picture', '')

        with transaction.atomic():
            user = CustomUser.objects.filter(email=email).first()
            es_cuenta_nueva = False

            if user is None:
                user = CustomUser.objects.create(
                    email=email,
                    username=email,
                    first_name=first_name,
                    last_name=last_name,
                    rol=CustomUser.Rol.CLIENTE,
                    google_id=google_id,
                    avatar_url=picture,
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])
                es_cuenta_nueva = True
            else:
                if user.rol != CustomUser.Rol.CLIENTE:
                    return Response(
                        {'detail': 'Esta cuenta es administrativa, usa email y contrasena',
                         'codigo': 'cuenta_admin'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                cambios = []
                if not user.google_id:
                    user.google_id = google_id
                    cambios.append('google_id')
                if not user.avatar_url and picture:
                    user.avatar_url = picture
                    cambios.append('avatar_url')
                if cambios:
                    user.save(update_fields=cambios)

        fcm_token = serializer.validated_data.get('fcm_token')
        if fcm_token:
            from notificaciones.models import DispositivoFCM
            DispositivoFCM.objects.update_or_create(
                token_fcm=fcm_token,
                defaults={
                    'usuario': user,
                    'plataforma': serializer.validated_data.get('plataforma', 'ANDROID'),
                    'activo': True,
                },
            )

        data = _emitir_sesion(user, extra={'es_cuenta_nueva': es_cuenta_nueva})
        data['user']['es_cuenta_nueva'] = es_cuenta_nueva
        return Response(data)

@extend_schema(tags=['auth'])
class UsuariosListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from core.pagination import StandardPagination
        qs = CustomUser.objects.all().order_by('rol', 'email')
        rol = request.query_params.get('rol')
        if rol:
            qs = qs.filter(rol=rol)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(email__icontains=search) | qs.filter(first_name__icontains=search)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = UsuarioAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CrearUsuarioAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UsuarioAdminSerializer(user).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['auth'])
class UsuarioDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        serializer = UsuarioAdminSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
