from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from rest_framework import permissions, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.users.permissions import is_admin, is_support
from .models import Ad, AdRequest
from .permissions import (
    CanViewAd,
    IsAdOwnerOrAdmin,
    IsAdRequestOwnerOrAdmin,
    IsAssignedContractorOrAdmin,
)
from .serializers import (
    AdAssignSerializer,
    AdRequestSerializer,
    AdSerializer,
)


User = get_user_model()


class AdViewSet(viewsets.ModelViewSet):
    serializer_class = AdSerializer
    queryset = Ad.objects.all()

    def get_queryset(self):
        u = self.request.user
        qs = Ad.objects.all()

        if is_admin(u) or is_support(u):
            return qs

        own = Q(creator=u)  # creator sees all own ads (including canceled)
        open_ads = Q(status="OPEN")
        assigned_or_done_to_contractor = Q(status__in=["ASSIGNED", "DONE"], assigned_contractor=u)

        # CANCELED not visible to others (not even contractor), per PDF :contentReference[oaicite:10]{index=10}
        return qs.filter(own | open_ads | assigned_or_done_to_contractor).distinct()

    def get_permissions(self):
        if self.action == "create":
            # only CUSTOMER (or admin) creates ads :contentReference[oaicite:11]{index=11}
            return [permissions.IsAuthenticated()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsAdOwnerOrAdmin()]
        if self.action in ("cancel", "assign", "confirm_completion"):
            return [permissions.IsAuthenticated(), IsAdOwnerOrAdmin()]
        if self.action == "report_done":
            return [permissions.IsAuthenticated(), IsAssignedContractorOrAdmin()]
        # retrieve/list visibility handled by queryset + CanViewAd on object
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_superuser or getattr(user, "role", None) == "CUSTOMER"):
            raise permissions.PermissionDenied("Only customers can create ads.")
        serializer.save(creator=user)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        # object-level visibility check (extra safety)
        if not CanViewAd().has_object_permission(request, self, obj):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        request=None,
        responses={200: AdSerializer},
        examples=[
            OpenApiExample(
                "Cancel response",
                value={"id": 10, "status": "CANCELED", "canceled_at": "2026-01-02T10:20:30Z"},
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        ad: Ad = self.get_object()

        if ad.status == "DONE":
            return Response({"detail": "Cannot cancel a DONE ad."}, status=status.HTTP_400_BAD_REQUEST)
        if ad.status == "CANCELED":
            return Response({"detail": "Ad is already canceled."}, status=status.HTTP_400_BAD_REQUEST)

        ad.status = "CANCELED"
        ad.canceled_at = timezone.now()
        ad.save(update_fields=["status", "canceled_at", "updated_at"])
        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)

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
                value={"id": 10, "status": "ASSIGNED", "assigned_contractor": 5, "location": "Tehran - Valiasr"},
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

        # Must be among applicants (requests) :contentReference[oaicite:12]{index=12}
        has_request = AdRequest.objects.filter(ad=ad, contractor=contractor, status="APPLIED").exists()
        if not has_request:
            return Response({"detail": "This contractor has not applied to this ad."}, status=status.HTTP_400_BAD_REQUEST)

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

        # Customer confirms; contractor cannot confirm (permission already enforces owner) :contentReference[oaicite:13]{index=13}
        ad.status = "DONE"
        ad.completed_at = timezone.now()
        ad.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)


class AdRequestViewSet(mixins.CreateModelMixin,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    serializer_class = AdRequestSerializer
    queryset = AdRequest.objects.select_related("ad", "contractor")

    def get_queryset(self):
        u = self.request.user
        qs = self.queryset

        if is_admin(u) or is_support(u):
            return qs
        if getattr(u, "role", None) == "CONTRACTOR":
            return qs.filter(contractor=u)
        # CUSTOMER: requests for own ads
        return qs.filter(ad__creator=u)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action == "withdraw":
            return [permissions.IsAuthenticated(), IsAdRequestOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        request=None,
        responses={200: AdRequestSerializer},
        examples=[
            OpenApiExample(
                "Withdraw response",
                value={"id": 77, "ad": 10, "contractor": 5, "status": "WITHDRAWN", "note": "..." },
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        req: AdRequest = self.get_object()
        if req.status == "WITHDRAWN":
            return Response(AdRequestSerializer(req).data, status=status.HTTP_200_OK)

        req.status = "WITHDRAWN"
        req.save(update_fields=["status", "updated_at"])
        return Response(AdRequestSerializer(req).data, status=status.HTTP_200_OK)
