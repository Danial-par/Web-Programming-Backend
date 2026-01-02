from django.conf import settings
from django.db import models
from django.db.models import Q


class Ticket(models.Model):
    """
    Ticket created by any user; only support/admin answers (single text response).
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        CLOSED = "CLOSED", "Closed"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_created",
        db_index=True,
    )

    # Tickets may be related to an ad (optional)
    ad = models.ForeignKey(
        "ads.Ad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
        db_index=True,
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    # Single support response (per PDF)
    support_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_responded",
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Keep responded_by/responded_at consistent (both null or both set)
            models.CheckConstraint(
                check=(
                    (Q(responded_by__isnull=True) & Q(responded_at__isnull=True))
                    | (Q(responded_by__isnull=False) & Q(responded_at__isnull=False))
                ),
                name="ticket_response_fields_all_or_none",
            ),
        ]
        indexes = [
            models.Index(fields=["created_by", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Ticket#{self.pk} {self.title} ({self.status})"
