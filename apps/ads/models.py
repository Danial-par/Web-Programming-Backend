from django.conf import settings
from django.db import models
from django.db.models import Q


class Ad(models.Model):
    """
    Ad workflow statuses (per PDF):
    OPEN -> ASSIGNED -> DONE
    Can be CANCELED before completion.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ASSIGNED = "ASSIGNED", "Assigned"
        DONE = "DONE", "Done"
        CANCELED = "CANCELED", "Canceled"

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ads_created",
        db_index=True,
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    # Eventually one assigned contractor
    assigned_contractor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ads_assigned",
        limit_choices_to={"role": "CONTRACTOR"},
        db_index=True,
    )

    # After assignment, ad has time + location (enforce at API/serializer level).
    scheduled_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)

    # Step 2.10: contractor reports done (visible update)
    work_reported_done_at = models.DateTimeField(null=True, blank=True)

    # Step 2.11: customer confirms done -> status becomes DONE
    completed_at = models.DateTimeField(null=True, blank=True)

    # Step 2.12: customer can cancel before completion
    canceled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # If status is ASSIGNED or DONE => must have assigned_contractor
            models.CheckConstraint(
                check=Q(status__in=["OPEN", "CANCELED"]) | Q(assigned_contractor__isnull=False),
                name="ad_assignee_required_when_assigned_or_done",
            ),
            # If DONE => must have both timestamps (contractor report + customer confirm)
            models.CheckConstraint(
                check=Q(status__in=["OPEN", "ASSIGNED", "CANCELED"]) | Q(work_reported_done_at__isnull=False),
                name="ad_done_requires_work_reported_done_at",
            ),
            models.CheckConstraint(
                check=Q(status__in=["OPEN", "ASSIGNED", "CANCELED"]) | Q(completed_at__isnull=False),
                name="ad_done_requires_completed_at",
            ),
        ]
        indexes = [
            # Fast feeds / lists
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["creator", "created_at"]),
            # Contractor dashboard: assigned/done ads for a contractor
            models.Index(fields=["assigned_contractor", "status"]),
        ]

    def __str__(self) -> str:
        return f"Ad#{self.pk} {self.title} ({self.status})"


class AdRequest(models.Model):
    """
    Contractor request to take an OPEN ad.
    Contractors can withdraw their request (keep row, flip status).
    """

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        related_name="requests",
        db_index=True,
    )

    contractor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ad_requests",
        limit_choices_to={"role": "CONTRACTOR"},
        db_index=True,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.APPLIED,
        db_index=True,
    )

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # One request per (ad, contractor). Withdraw = status change, not extra row.
            models.UniqueConstraint(fields=["ad", "contractor"], name="uniq_ad_request_per_contractor"),
        ]
        indexes = [
            models.Index(fields=["ad", "status"]),
            models.Index(fields=["contractor", "status"]),
        ]

    def __str__(self) -> str:
        return f"AdRequest#{self.pk} ad={self.ad_id} contractor={self.contractor_id} ({self.status})"
