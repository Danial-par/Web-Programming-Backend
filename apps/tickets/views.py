from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiResponse,
)

from apps.users.permissions import IsSupportOrAdmin, is_admin, is_support
from .models import Ticket
from .permissions import IsTicketOwnerOrSupportOrAdmin
from .serializers import TicketRespondSerializer, TicketSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Tickets"],
        summary="List tickets",
        description="Users see their own tickets. SUPPORT/ADMIN see all tickets.",
    ),
    create=extend_schema(
        tags=["Tickets"],
        summary="Create ticket",
        description="Any user can create a support ticket with title + message (optional ad link).",
        examples=[
            OpenApiExample(
                "Create ticket request",
                value={"title": "Problem", "message": "Contractor didn't show up.", "ad": 10},
                request_only=True,
            )
        ],
    ),
    partial_update=extend_schema(
        tags=["Tickets"],
        summary="Edit ticket",
        description="Owner can edit their ticket; SUPPORT/ADMIN can edit any ticket.",
    ),
    destroy=extend_schema(
        tags=["Tickets"],
        summary="Delete ticket",
        description="SUPPORT/ADMIN only.",
    ),
)
class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    queryset = Ticket.objects.select_related("created_by", "ad")

    def get_queryset(self):
        u = self.request.user
        if is_admin(u) or is_support(u):
            return self.queryset
        return self.queryset.filter(created_by=u)

    def get_permissions(self):
        if self.action in ("destroy",):
            # only support/admin can delete/manage all tickets :contentReference[oaicite:14]{index=14}
            return [permissions.IsAuthenticated(), IsSupportOrAdmin()]
        if self.action == "respond":
            # only support/admin can answer (customer cannot answer own ticket) :contentReference[oaicite:15]{index=15}
            return [permissions.IsAuthenticated(), IsSupportOrAdmin()]
        # read/update: owner OR support/admin
        return [permissions.IsAuthenticated(), IsTicketOwnerOrSupportOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        tags=["Tickets"],
        summary="Respond to ticket",
        description="SUPPORT/ADMIN responds with a single text response. Ticket owner cannot respond.",
        request=TicketRespondSerializer,
        responses={200: TicketSerializer, 403: OpenApiResponse(description="Forbidden")},
        examples=[
            OpenApiExample(
                "Respond request",
                value={"support_response": "We are investigating.", "status": "IN_PROGRESS"},
                request_only=True,
            ),
            OpenApiExample(
                "Respond response",
                value={"id": 12, "status": "IN_PROGRESS", "support_response": "We are investigating."},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        ticket: Ticket = self.get_object()

        s = TicketRespondSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        ticket.support_response = s.validated_data["support_response"]
        ticket.responded_by = request.user
        ticket.responded_at = timezone.now()

        if "status" in s.validated_data:
            ticket.status = s.validated_data["status"]
        else:
            # default when responding
            ticket.status = "IN_PROGRESS"

        ticket.save(update_fields=["support_response", "responded_by", "responded_at", "status", "updated_at"])
        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)
