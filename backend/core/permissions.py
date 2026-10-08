from rest_framework.permissions import BasePermission

from .models import User

ROLES = frozenset({"secretary", "coordinator", "instructor", "communication"})


def is_internal(user):
    return bool(
        user and user.is_authenticated and user.is_active
        and user.access_status == "approved"
        and isinstance(user.roles, list) and user.roles
        and all(isinstance(role, str) for role in user.roles)
        and set(user.roles).issubset(ROLES)
    )


def is_administrative(user):
    return is_internal(user) and bool(set(user.roles) & {"secretary", "coordinator"})


class IsInternal(BasePermission):
    message = "O acesso interno requer conta aprovada com uma função autorizada."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Session users and force-authenticated users may hold stale attributes.
        current = User.objects.filter(pk=request.user.pk).first()
        if not is_internal(current):
            return False
        request.user = current
        return True


class IsAdministrative(BasePermission):
    message = "Esta operação requer Secretaria ou Coordenação."

    def has_permission(self, request, view):
        return is_administrative(request.user)
