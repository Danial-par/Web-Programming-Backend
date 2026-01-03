from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, FloatField, Value
from django.db.models.functions import Coalesce

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from apps.ads.models import Ad
from apps.ads.serializers import AdSummarySerializer
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewPublicSerializer
from apps.users.permissions import is_admin, is_support

from .filters import ContractorFilterSet
from .profile_serializers import (
    ContractorListSerializer,
    ContractorProfileResponseSerializer,
    CustomerProfileResponseSerializer,
    UserNonSensitiveSerializer,
)

User = get_user_model()


def contractors_with_stats_queryset():
    """
    Reusable annotated queryset for contractor list + contractor profile stats.
    """
    return (
        User.objects.filter(role="CONTRACTOR")
        .annotate(
            review_count=Count("reviews_received", distinct=True),
            avg_rating=Coalesce(
                Avg("reviews_received__rating"),
                Value(0.0),
                output_field=FloatField(),
            ),
            completed_ads_count=Count(
                "ads_assigned",
                filter=Q(ads_assigned__status="DONE"),
                distinct=True,
            ),
        )
    )


class ContractorListView(generics.ListAPIView):
    """
    Contractor search/filter/sort:
    - filter by min avg rating and min review count
    - ordering by avg_rating and review_count
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ContractorListSerializer

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ContractorFilterSet
    ordering_fields = ["avg_rating", "review_count"]
    ordering = ["-avg_rating", "-review_count"]

    def get_queryset(self):
        return contractors_with_stats_queryset()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="min_avg_rating",
                type=float,
                required=False,
                description="Minimum average rating (e.g. 4.0).",
            ),
            OpenApiParameter(
                name="min_review_count",
                type=int,
                required=False,
                description="Minimum number of reviews (e.g. 10).",
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                required=False,
                description="Comma-separated ordering fields: avg_rating, review_count. Prefix with '-' for desc. Example: -avg_rating,-review_count",
            ),
        ],
        responses={200: ContractorListSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Example response",
                value=[
                    {
                        "id": 5,
                        "username": "reza",
                        "first_name": "",
                        "last_name": "",
                        "role": "CONTRACTOR",
                        "avg_rating": 4.7,
                        "review_count": 12,
                        "completed_ads_count": 20,
                    }
                ],
                response_only=True,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ContractorProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: ContractorProfileResponseSerializer},
        examples=[
            OpenApiExample(
                "Contractor profile response",
                value={
                    "contractor": {"id": 5, "username": "reza", "first_name": "", "last_name": "", "role": "CONTRACTOR"},
                    "completed_ads_count": 3,
                    "avg_rating": 4.5,
                    "review_count": 2,
                    "completed_ads": [
                        {
                            "id": 10,
                            "title": "Fix my sink",
                            "category": "plumbing",
                            "status": "DONE",
                            "created_at": "2026-01-03T09:00:00Z",
                            "scheduled_at": "2026-01-05T12:00:00Z",
                            "location": "Tehran - Valiasr",
                            "assigned_contractor": 5,
                            "completed_at": "2026-01-06T16:00:00Z",
                        }
                    ],
                    "reviews": [
                        {
                            "id": 1,
                            "ad": 10,
                            "author": 2,
                            "author_username": "danial",
                            "rating": 5,
                            "comment": "Great work.",
                            "created_at": "2026-01-06T17:00:00Z",
                        }
                    ],
                },
                response_only=True,
            )
        ],
    )
    def get(self, request, pk: int):
        contractor = contractors_with_stats_queryset().filter(pk=pk).first()
        if not contractor:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ads completed by contractor (DONE)
        completed_ads_qs = (
            Ad.objects.filter(assigned_contractor=contractor, status="DONE")
            .order_by("-completed_at", "-id")
        )

        # Reviews/comments ordered by time (newest first) :contentReference[oaicite:6]{index=6}
        reviews_qs = (
            Review.objects.filter(contractor=contractor)
            .select_related("author")
            .order_by("-created_at")
        )

        payload = {
            "contractor": UserNonSensitiveSerializer(contractor).data,
            "completed_ads_count": contractor.completed_ads_count,
            "avg_rating": contractor.avg_rating,
            "review_count": contractor.review_count,
            "completed_ads": AdSummarySerializer(completed_ads_qs, many=True).data,
            "reviews": ReviewPublicSerializer(reviews_qs, many=True).data,
        }
        return Response(payload, status=status.HTTP_200_OK)


class CustomerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: CustomerProfileResponseSerializer},
        examples=[
            OpenApiExample(
                "Customer profile response",
                value={
                    "customer": {"id": 2, "username": "danial", "first_name": "", "last_name": "", "role": "CUSTOMER"},
                    "ads": [
                        {
                            "id": 10,
                            "title": "Fix my sink",
                            "category": "plumbing",
                            "status": "OPEN",
                            "created_at": "2026-01-03T09:00:00Z",
                            "scheduled_at": None,
                            "location": None,
                            "assigned_contractor": None,
                            "completed_at": None,
                        }
                    ],
                },
                response_only=True,
            )
        ],
    )
    def get(self, request, pk: int):
        customer = User.objects.filter(pk=pk, role="CUSTOMER").first()
        if not customer:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ads_qs = Ad.objects.filter(creator=customer).order_by("-created_at")

        # CANCELED ads not visible to others except owner/support/admin :contentReference[oaicite:7]{index=7}
        if not (is_admin(request.user) or is_support(request.user) or request.user.id == customer.id):
            ads_qs = ads_qs.exclude(status="CANCELED")

        payload = {
            "customer": UserNonSensitiveSerializer(customer).data,
            "ads": AdSummarySerializer(ads_qs, many=True).data,
        }
        return Response(payload, status=status.HTTP_200_OK)
