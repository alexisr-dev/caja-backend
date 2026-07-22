from rest_framework.permissions import BasePermission

class _RolPermission(BasePermission):

    rol_atributo: str = ''

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return bool(getattr(user, self.rol_atributo, False))

class IsAdmin(_RolPermission):
    message = 'Requiere rol ADMIN'
    rol_atributo = 'es_admin'

class IsVendedor(_RolPermission):
    message = 'Requiere rol VENDEDOR'
    rol_atributo = 'es_vendedor'

class IsCliente(_RolPermission):
    message = 'Requiere rol CLIENTE'
    rol_atributo = 'es_cliente'

class IsAdminOrVendedor(BasePermission):
    message = 'Requiere rol ADMIN o VENDEDOR'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.es_admin or user.es_vendedor

class IsClienteOrVendedor(BasePermission):
    message = 'Requiere rol CLIENTE o VENDEDOR'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.es_cliente or user.es_vendedor

class IsOwnerOrAdmin(BasePermission):
    message = 'Solo el dueño o admin puede acceder'

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.es_admin:
            return True
        for attr in ('cliente', 'usuario', 'vendedor'):
            owner = getattr(obj, attr, None)
            if owner == user:
                return True
        return False
