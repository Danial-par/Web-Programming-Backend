from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.ads.serializers import AdSummarySerializer
from apps.reviews.serializers import ReviewPublicSerializer

User = get_user_model()


class UserNonSensitiveSerializer(serializers.ModelSerializer):
    """
    Non-sensitive fields only (no email/phone).
    """
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "role")
        read_only_fields = fields


class ContractorListSerializer(UserNonSensitiveSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    completed_ads_count = serializers.IntegerField(read_only=True)

    class Meta(UserNonSensitiveSerializer.Meta):
        fields = UserNonSensitiveSerializer.Meta.fields + (
            "avg_rating",
            "review_count",
            "completed_ads_count",
        )


class ContractorProfileResponseSerializer(serializers.Serializer):
    contractor = UserNonSensitiveSerializer()
    completed_ads_count = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    review_count = serializers.IntegerField()
    completed_ads = AdSummarySerializer(many=True)
    reviews = ReviewPublicSerializer(many=True)


class CustomerProfileResponseSerializer(serializers.Serializer):
    customer = UserNonSensitiveSerializer()
    ads = AdSummarySerializer(many=True)
