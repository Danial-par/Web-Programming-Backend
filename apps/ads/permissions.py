from rest_framework.permissions import BasePermission
from apps.users.permissions import is_admin, is_support


class IsAdOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        return is_admin(request.user) or obj.creator_id == request.user.id


class IsAssignedContractorOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        return is_admin(request.user) or obj.assigned_contractor_id == request.user.id


class CanViewAd(BasePermission):
    """
    PDF visibility:
    - CANCELED ads only visible to creator + support + admin
    - ASSIGNED/DONE visible to creator + assigned contractor + support/admin
    - OPEN visible to authenticated users
    :contentReference[oaicite:2]{index=2}
    """
    def has_object_permission(self, request, view, obj) -> bool:
        u = request.user
        if is_admin(u) or is_support(u):
            return True
        if obj.creator_id == u.id:
            return True
        if obj.status == "OPEN":
            return True
        if obj.status == "CANCELED":
            return False
        return obj.assigned_contractor_id == u.id
