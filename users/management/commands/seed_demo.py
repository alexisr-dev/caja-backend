"""Crea (o actualiza) las cuentas de demostracion para reclutadores.

Estas cuentas llevan `es_demo=True`, lo que hace que `LoginView` entregue los tokens
directamente sin pedir el codigo 2FA de 6 digitos: el visitante no tiene acceso al buzon
de correo de la cuenta. Cualquier otro usuario ADMIN/VENDEDOR sigue pasando por el 2FA.

Uso:
    python manage.py seed_demo            # crea lo que falte, no toca contrasenas existentes
    python manage.py seed_demo --reset    # ademas reescribe la contrasena y reactiva la cuenta
"""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import CustomUser

CUENTAS_DEMO = [
    {
        'email': 'demo.admin@cajasmart.dev',
        'rol': CustomUser.Rol.ADMIN,
        'first_name': 'Admin',
        'last_name': 'Demo',
        'env_password': 'DEMO_ADMIN_PASSWORD',
        'password_defecto': 'DemoAdmin2025!',
        'panel': '/admin',
    },
    {
        'email': 'demo.vendedor@cajasmart.dev',
        'rol': CustomUser.Rol.VENDEDOR,
        'first_name': 'Vendedor',
        'last_name': 'Demo',
        'env_password': 'DEMO_VENDEDOR_PASSWORD',
        'password_defecto': 'DemoVendedor2025!',
        'panel': '/caja',
    },
]


class Command(BaseCommand):
    help = 'Crea o actualiza las cuentas demo (ADMIN y VENDEDOR) que omiten el 2FA.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Restablece la contrasena y reactiva las cuentas aunque ya existan.',
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        reset = opciones['reset']
        resumen = []

        for cuenta in CUENTAS_DEMO:
            password = os.environ.get(cuenta['env_password'], cuenta['password_defecto'])
            usuario = CustomUser.objects.filter(email=cuenta['email']).first()

            if usuario is None:
                usuario = CustomUser.objects.create_user(
                    email=cuenta['email'],
                    password=password,
                    rol=cuenta['rol'],
                    first_name=cuenta['first_name'],
                    last_name=cuenta['last_name'],
                )
                estado = 'creada'
            else:
                estado = 'actualizada'

            usuario.rol = cuenta['rol']
            usuario.first_name = cuenta['first_name']
            usuario.last_name = cuenta['last_name']
            usuario.es_demo = True
            usuario.is_active = True
            # Sin acceso al admin de Django: ese panel usa sesion y no pasa por 2FA.
            usuario.is_staff = False
            usuario.is_superuser = False

            if reset:
                usuario.set_password(password)
                estado = 'restablecida'

            usuario.save()
            resumen.append((cuenta, password, estado))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Cuentas demo listas (omiten el codigo 2FA):'))
        self.stdout.write('')
        for cuenta, password, estado in resumen:
            self.stdout.write(f"  {cuenta['rol']:<9} -> {cuenta['panel']}  [{estado}]")
            self.stdout.write(f"    email      : {cuenta['email']}")
            self.stdout.write(f"    contrasena : {password}")
            self.stdout.write('')
        self.stdout.write(
            'Estas credenciales tambien se muestran en /login del frontend '
            '(VITE_DEMO_MODE=true). Manten ambos lados sincronizados.'
        )
