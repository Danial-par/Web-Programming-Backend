from rest_framework.permissions import BasePermission
from apps.users.permissions import is_admin, is_support


class IsReviewAuthorOrSupportOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        return is_admin(request.user) or is_support(request.user) or obj.author_id == request.user.id
