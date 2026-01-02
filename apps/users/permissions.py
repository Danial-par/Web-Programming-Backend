from rest_framework.permissions import BasePermission


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_superuser)


def is_support(user) -> bool:
    return bool(is_admin(user) or (user and user.is_authenticated and getattr(user, "role", None) == "SUPPORT"))


def is_contractor(user) -> bool:
    return bool(is_admin(user) or (user and user.is_authenticated and getattr(user, "role", None) == "CONTRACTOR"))


def is_customer(user) -> bool:
    return bool(is_admin(user) or (user and user.is_authenticated and getattr(user, "role", None) == "CUSTOMER"))


class IsAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_admin(request.user)


class IsSupportOrAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_support(request.user)


class IsContractorOrAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_contractor(request.user)


class IsCustomerOrAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_customer(request.user)
