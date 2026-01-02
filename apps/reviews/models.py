from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Review(models.Model):
    """
    Review = (rating 1..5 + text comment) written by customer about contractor,
    tied to a single Ad.
    """

    # Strongly recommended: one review per ad (customer reviews after completion)
    ad = models.OneToOneField(
        "ads.Ad",
        on_delete=models.CASCADE,
        related_name="review",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_written",
        db_index=True,
    )

    contractor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_received",
        limit_choices_to={"role": "CONTRACTOR"},
        db_index=True,
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        db_index=True,
    )

    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(rating__gte=1) & Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]
        indexes = [
            # Fast "contractor profile" listing newest reviews
            models.Index(fields=["contractor", "created_at"]),
            # Optional endpoint: filter reviews by rating
            models.Index(fields=["contractor", "rating"]),
        ]

    def __str__(self) -> str:
        return f"Review#{self.pk} {self.rating}/5 contractor={self.contractor_id} ad={self.ad_id}"
