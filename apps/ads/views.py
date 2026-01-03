from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.users.permissions import IsContractorOrAdmin, IsCustomerOrAdmin, is_admin, is_support
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewSerializer

from .models import Ad, AdRequest
from .permissions import CanViewAd, IsAdOwnerOrAdmin, IsAssignedContractorOrAdmin
from .serializers import (
    AdApplySerializer,
    AdAssignSerializer,
    AdRequestSerializer,
    AdReviewCreateSerializer,
    AdSerializer,
)

User = get_user_model()


class AdViewSet(viewsets.ModelViewSet):
    serializer_class = AdSerializer
    queryset = Ad.objects.all()

    # ---------- visibility rules ----------
    def get_queryset(self):
        u = self.request.user
        qs = Ad.objects.all()

        if is_admin(u) or is_support(u):
            return qs

        own = Q(creator=u)
        open_ads = Q(status="OPEN")
        contractor_assigned_or_done = Q(status__in=["ASSIGNED", "DONE"], assigned_contractor=u)

        # CANCELED only visible to owner/support/admin (NOT contractor) :contentReference[oaicite:3]{index=3}
        return qs.filter(own | open_ads | contractor_assigned_or_done).distinct()

    # ---------- permissions ----------
    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsCustomerOrAdmin()]

        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsAdOwnerOrAdmin()]

        # lifecycle actions
        if self.action in ("cancel", "assign", "confirm_completion", "requests"):
            return [permissions.IsAuthenticated(), IsAdOwnerOrAdmin()]

        if self.action in ("apply", "withdraw"):
            return [permissions.IsAuthenticated(), IsContractorOrAdmin()]

        if self.action == "report_done":
            return [permissions.IsAuthenticated(), IsAssignedContractorOrAdmin()]

        if self.action == "review":
            return [permissions.IsAuthenticated(), IsAdOwnerOrAdmin(), IsCustomerOrAdmin()]

        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    # ---------- lifecycle actions ----------

    @extend_schema(
        request=AdApplySerializer,
        responses={200: AdRequestSerializer, 201: AdRequestSerializer},
        examples=[
            OpenApiExample("Apply request", value={"note": "I can do it today."}, request_only=True),
            OpenApiExample(
                "Apply response",
                value={
                    "id": 77,
                    "ad": 10,
                    "contractor": 5,
                    "status": "APPLIED",
                    "note": "I can do it today.",
                    "created_at": "2026-01-03T10:00:00Z",
                    "updated_at": "2026-01-03T10:00:00Z",
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="apply")
    def apply(self, request, pk=None):
        ad: Ad = self.get_object()

        # Validation rules (PDF) :contentReference[oaicite:4]{index=4}
        if ad.status != "OPEN":
            return Response({"detail": "You can only apply to OPEN ads."}, status=status.HTTP_400_BAD_REQUEST)
        if ad.creator_id == request.user.id:
            return Response({"detail": "You cannot apply to your own ad."}, status=status.HTTP_400_BAD_REQUEST)

        s = AdApplySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        note = s.validated_data.get("note", "")

        obj, created = AdRequest.objects.get_or_create(
            ad=ad,
            contractor=request.user,
            defaults={"status": "APPLIED", "note": note},
        )
        if not created:
            obj.status = "APPLIED"
            obj.note = note
            obj.save(update_fields=["status", "note", "updated_at"])

        return Response(
            AdRequestSerializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        request=None,
        responses={200: AdRequestSerializer},
        examples=[
            OpenApiExample(
                "Withdraw response",
                value={
                    "id": 77,
                    "ad": 10,
                    "contractor": 5,
                    "status": "WITHDRAWN",
                    "note": "I can do it today.",
                    "created_at": "2026-01-03T10:00:00Z",
                    "updated_at": "2026-01-03T11:00:00Z",
                },
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        ad: Ad = self.get_object()

        obj = AdRequest.objects.filter(ad=ad, contractor=request.user).first()
        if not obj:
            return Response({"detail": "You have not applied to this ad."}, status=status.HTTP_400_BAD_REQUEST)

        if obj.status != "WITHDRAWN":
            obj.status = "WITHDRAWN"
            obj.save(update_fields=["status", "updated_at"])

        return Response(AdRequestSerializer(obj).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={200: AdRequestSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Requests list response",
                value=[
                    {
                        "id": 77,
                        "ad": 10,
                        "contractor": 5,
                        "status": "APPLIED",
                        "note": "I can do it today.",
                        "created_at": "2026-01-03T10:00:00Z",
                        "updated_at": "2026-01-03T10:00:00Z",
                    }
                ],
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["get"], url_path="requests")
    def requests(self, request, pk=None):
        """
        Customer selects contractor from this list. :contentReference[oaicite:5]{index=5}
        """
        ad: Ad = self.get_object()
        qs = AdRequest.objects.filter(ad=ad, status="APPLIED").order_by("-created_at")
        return Response(AdRequestSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AdAssignSerializer,
        responses={200: AdSerializer},
        examples=[
            OpenApiExample(
                "Assign request",
                value={"contractor_id": 5, "scheduled_at": "2026-01-05T12:00:00Z", "location": "Tehran - Valiasr"},
                request_only=True,
            ),
            OpenApiExample(
                "Assign response",
                value={
                    "id": 10,
                    "title": "Fix my sink",
                    "description": "Kitchen sink leaking",
                    "category": "plumbing",
                    "status": "ASSIGNED",
                    "creator": 2,
                    "assigned_contractor": 5,
                    "scheduled_at": "2026-01-05T12:00:00Z",
                    "location": "Tehran - Valiasr",
                    "work_reported_done_at": None,
                    "completed_at": None,
                    "canceled_at": None,
                    "created_at": "2026-01-03T09:00:00Z",
                    "updated_at": "2026-01-03T10:05:00Z",
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        ad: Ad = self.get_object()

        if ad.status != "OPEN":
            return Response({"detail": "Only OPEN ads can be assigned."}, status=status.HTTP_400_BAD_REQUEST)

        s = AdAssignSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        contractor_id = s.validated_data["contractor_id"]
        scheduled_at = s.validated_data["scheduled_at"]
        location = s.validated_data["location"]

        contractor = User.objects.filter(id=contractor_id, role="CONTRACTOR").first()
        if not contractor:
            return Response({"detail": "Invalid contractor_id."}, status=status.HTTP_400_BAD_REQUEST)

        # Must be among APPLIED requests (PDF) :contentReference[oaicite:6]{index=6}
        ok = AdRequest.objects.filter(ad=ad, contractor=contractor, status="APPLIED").exists()
        if not ok:
            return Response({"detail": "Contractor has not applied to this ad."}, status=status.HTTP_400_BAD_REQUEST)

        ad.assigned_contractor = contractor
        ad.scheduled_at = scheduled_at
        ad.location = location
        ad.status = "ASSIGNED"
        ad.save(update_fields=["assigned_contractor", "scheduled_at", "location", "status", "updated_at"])

        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={200: AdSerializer},
        examples=[
            OpenApiExample(
                "Report done response",
                value={"id": 10, "status": "ASSIGNED", "work_reported_done_at": "2026-01-06T15:00:00Z"},
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="report-done")
    def report_done(self, request, pk=None):
        ad: Ad = self.get_object()

        if ad.status != "ASSIGNED":
            return Response({"detail": "Only ASSIGNED ads can be reported done."}, status=status.HTTP_400_BAD_REQUEST)

        if not ad.work_reported_done_at:
            ad.work_reported_done_at = timezone.now()
            ad.save(update_fields=["work_reported_done_at", "updated_at"])

        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={200: AdSerializer},
        examples=[
            OpenApiExample(
                "Confirm completion response",
                value={"id": 10, "status": "DONE", "completed_at": "2026-01-06T16:00:00Z"},
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="confirm-completion")
    def confirm_completion(self, request, pk=None):
        ad: Ad = self.get_object()

        if ad.status != "ASSIGNED":
            return Response({"detail": "Ad must be ASSIGNED to confirm completion."}, status=status.HTTP_400_BAD_REQUEST)
        if not ad.work_reported_done_at:
            return Response({"detail": "Contractor has not reported completion yet."}, status=status.HTTP_400_BAD_REQUEST)

        # Customer confirms -> DONE (contractor cannot confirm) :contentReference[oaicite:7]{index=7}
        ad.status = "DONE"
        ad.completed_at = timezone.now()
        ad.save(update_fields=["status", "completed_at", "updated_at"])

        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={200: AdSerializer},
        examples=[
            OpenApiExample(
                "Cancel response",
                value={"id": 10, "status": "CANCELED", "canceled_at": "2026-01-04T10:20:30Z"},
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        ad: Ad = self.get_object()

        # Customer can cancel before final completion (DONE) :contentReference[oaicite:8]{index=8}
        if ad.status == "DONE":
            return Response({"detail": "Cannot cancel a DONE ad."}, status=status.HTTP_400_BAD_REQUEST)

        if ad.status != "CANCELED":
            ad.status = "CANCELED"
            ad.canceled_at = timezone.now()
            ad.save(update_fields=["status", "canceled_at", "updated_at"])

        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AdReviewCreateSerializer,
        responses={201: ReviewSerializer},
        examples=[
            OpenApiExample(
                "Create review request",
                value={"rating": 5, "comment": "Great work, on time."},
                request_only=True,
            ),
            OpenApiExample(
                "Create review response",
                value={"id": 1, "ad": 10, "author": 2, "contractor": 5, "rating": 5, "comment": "Great work, on time.", "created_at": "2026-01-06T17:00:00Z"},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        """
        Customer rates/comments contractor after DONE. :contentReference[oaicite:9]{index=9}
        """
        ad: Ad = self.get_object()

        if ad.status != "DONE":
            return Response({"detail": "You can only review after the ad is DONE."}, status=status.HTTP_400_BAD_REQUEST)
        if not ad.assigned_contractor_id:
            return Response({"detail": "Ad has no assigned contractor."}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(ad, "review"):
            return Response({"detail": "This ad already has a review."}, status=status.HTTP_400_BAD_REQUEST)

        s = AdReviewCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        review = Review.objects.create(
            ad=ad,
            author=request.user,
            contractor=ad.assigned_contractor,
            rating=s.validated_data["rating"],
            comment=s.validated_data.get("comment", ""),
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
