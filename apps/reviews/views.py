from rest_framework import permissions, viewsets

from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.users.permissions import IsCustomerOrAdmin
from .models import Review
from .permissions import IsReviewAuthorOrSupportOrAdmin
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related("ad", "author", "contractor")

    def get_permissions(self):
        if self.action == "create":
            # customer writes review after completion :contentReference[oaicite:16]{index=16}
            return [permissions.IsAuthenticated(), IsCustomerOrAdmin()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsReviewAuthorOrSupportOrAdmin()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        examples=[
            OpenApiExample(
                "Create review request",
                value={"ad": 10, "rating": 5, "comment": "Very professional, on time."},
                request_only=True,
            ),
            OpenApiExample(
                "Create review response",
                value={"id": 1, "ad": 10, "author": 2, "contractor": 5, "rating": 5, "comment": "Very professional, on time."},
                response_only=True,
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
